# -*- coding: utf-8 -*-
#
# Copyright (c) 2010-2012 Cidadania S. Coop. Galega
#
# This file is part of e-cidadania.
#
# e-cidadania is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# e-cidadania is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with e-cidadania. If not, see <http://www.gnu.org/licenses/>.

"""
Proposal module views.
"""
import hashlib
import datetime

# Generic class-based views
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic import FormView
from django.views.generic.create_update import update_object

# Decorators 
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

# Response types
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.http import HttpResponse

# Some extras
from django.contrib import messages
from django.template import RequestContext
from django.db.models import Count
from django.db.models import F

# Application models 
from apps.ecidadania.proposals.models import Proposal, ProposalSet, \
        ProposalField, ConfirmVote
from apps.ecidadania.proposals.forms import ProposalForm, VoteProposal, \
        ProposalSetForm, ProposalFieldForm, ProposalSetSelectForm, \
        ProposalMergeForm, ProposalFieldDeleteForm
from core.spaces.models import Space

from django.core.mail import send_mail
from django.utils.translation import ugettext_lazy as _


class AddProposal(FormView):

    """
    Create a new proposal.
    
    :parameters: space_url
    :rtype: HTML Form
    :context: form, get_place
    """
    form_class = ProposalForm
    template_name = 'proposals/proposal_form.html'
    
    def get_success_url(self):
        return '/spaces/' + self.kwargs['space_url']
        
    def form_valid(self, form):
        self.space = get_object_or_404(Space, url=self.kwargs['space_url'])
        form_uncommited = form.save(commit=False)
        if int(self.kwargs['p_set']) != 0:
            form_uncommited.proposalset = get_object_or_404(ProposalSet, pk=self.kwargs['p_set'])
        form_uncommited.space = self.space
        form_uncommited.author = self.request.user
        form_uncommited.save()
        return super(AddProposal, self).form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super(AddProposal, self).get_context_data(**kwargs)
        self.space = get_object_or_404(Space, url=self.kwargs['space_url'])
        self.field = ProposalField.objects.filter(proposalset=self.kwargs['p_set'])
        context['get_place'] = self.space
        context['form_field'] = [f_name.field_name for f_name in self.field]
        return context
        
    def dispatch(self, *args, **kwargs):
        return super(AddProposal, self).dispatch(*args, **kwargs)


class ViewProposal(DetailView):

    """
    Detail view of a proposal. Inherits from django :class:`DetailView` generic
    view.

    :rtype: object
    :context: proposal
    """
    context_object_name = 'proposal'
    template_name = 'proposals/proposal_detail.html'

    def get_object(self):
        prop_id = self.kwargs['prop_id']
        return get_object_or_404(Proposal, pk = prop_id)

    def get_context_data(self, **kwargs):
        context = super(ViewProposal, self).get_context_data(**kwargs)
        current_space = get_object_or_404(Space, url=self.kwargs['space_url'])
        support_votes_count = Proposal.objects.filter(space=current_space)\
                             .annotate(Count('support_votes'))
        # We are going to get the proposal position in the list
        self.get_position = 0
        proposal = get_object_or_404(Proposal, pk=self.kwargs['prop_id'])
        if proposal.merged == True:
            context['merged_proposal'] = proposal.merged_proposals.all()
        for i,x in enumerate(support_votes_count):
            if x.id == int(self.kwargs['prop_id']):
                self.get_position = i
        context['get_place'] = current_space
        context['support_votes_count'] = support_votes_count[int(self.get_position)].support_votes__count
        context['location'] = Proposal.objects.get(pk=self.kwargs['prop_id'])
        return context


class EditProposal(UpdateView):

    """
    The proposal can be edited by space and global admins, but also by their
    creator.

    :rtype: HTML Form
    :context: get_place
    :parameters: space_url, prop_id
    """
    model = Proposal
    template_name = 'proposals/proposal_form.html'
    
    def get_success_url(self):
        return '/spaces/{0}/proposal/{1}/'.format(self.kwargs['space_url'], self.kwargs['prop_id'])
        
    def get_object(self):
        prop_id = self.kwargs['prop_id']
        return get_object_or_404(Proposal, pk = prop_id)
        
    def get_context_data(self, **kwargs):
        context = super(EditProposal, self).get_context_data(**kwargs)
        self.p_set = Proposal.objects.get(pk = self.kwargs['prop_id'])
        self.field = ProposalField.objects.filter(proposalset = self.p_set.proposalset)
        context['form_field'] = [f_name.field_name for f_name in self.field]
        context['get_place'] = get_object_or_404(Space, url=self.kwargs['space_url'])
        return context
        
    @method_decorator(permission_required('proposals.edit_proposal'))
    def dispatch(self, *args, **kwargs):
        return super(EditProposal, self).dispatch(*args, **kwargs)
                             
            
class DeleteProposal(DeleteView):

    """
    Delete a proposal.

    :rtype: Confirmation
    :context: get_place
    """
    def get_object(self):
        return get_object_or_404(Proposal, pk = self.kwargs['prop_id'])

    def get_success_url(self):
        current_space = self.kwargs['space_url']
        return '/spaces/{0}'.format(current_space)

    def get_context_data(self, **kwargs):
        context = super(DeleteProposal, self).get_context_data(**kwargs)
        context['get_place'] = get_object_or_404(Space, url=self.kwargs['space_url'])
        return context                 
                  
           
@require_POST
def vote_proposal(request, space_url):

    """
    Send email to user to validate vote before is calculated.
    :attributes: - prop: current proposal
    :rtype: multiple entity objects.
    """
    prop = get_object_or_404(Proposal, pk=request.POST['propid'])
    try:
         intent = ConfirmVote.objects.get(user=request.user, proposal=prop)
    except ConfirmVote.DoesNotExist:
        token = hashlib.md5("%s%s%s" % (request.user, prop,
                            datetime.datetime.now())).hexdigest()
        intent = ConfirmVote(user=request.user, proposal=prop, token=token)
        intent.save()
        subject = _("New vote validation request")
        body = _("Hello {0}, \n \
                 You are getting this email because you wanted to support proposal {1}.\n\
                 Please click on the link below to vefiry your vote.\n {2} \n \
                 Thank you for your vote."
                 .format(request.user.username, prop.title,
                 intent.get_approve_url()))
        send_mail(subject=subject, message=body,
                   from_email="noreply@ecidadania.org",
                   recipient_list=[request.user.email])

class ValidateVote(DetailView):

    """
    Validates the vote. It adds the user to the list of users who voted it everything checks ok.
    """
    status = _("The requested vote validation does not exist!")

    def get_object(self):
        try:
            intent = ConfirmVote.objects.get(token=self.kwargs['token'])
            intent.proposal.support_votes.add(intent.user)
            self.status = _("The vote has been authorised for proposal \
            in space \"%s\"." % intent.proposal.title)
            messages.success(self.request, _("Authorization successful"))

        except ConfirmVote.DoesNotExist:
            self.status  = _("The requested intent does not exist!")

        return intent.proposal

    def get_context_data(self, **kwargs):
        context = super(ValidateVote, self).get_context_data(**kwargs)
        context['status'] = self.status
        context['request_user'] = ConfirmVote.objects.get(
            token=self.kwargs['token']).user
        return context

class ListProposals(ListView):

    """
    List all proposals stored whithin a space. Inherits from django :class:`ListView`
    generic view.

    :rtype: Object list
    :context: proposal
    """
    paginate_by = 50
    context_object_name = 'proposal'

    def get_queryset(self):
        place = get_object_or_404(Space, url=self.kwargs['space_url'])
        objects = Proposal.objects.annotate(Count('support_votes')).filter(space=place.id).order_by('pub_date')
        return objects

    def get_context_data(self, **kwargs):
        context = super(ListProposals, self).get_context_data(**kwargs)
        context['get_place'] = get_object_or_404(Space, url=self.kwargs['space_url'])   
        return context




def add_proposal_fields(request, space_url):
    
    """
    Adds a new form field to the proposal form. The admin can customize the proposal form for a 
    particular proposal set. The optional fields will be already defined, this function will allow 
    the admin to add those field to the proposal form.

    .. versionadded:: 0.1.5
    
    :arguments: space_url
    :context:form, get_place, prop_fields, form_data, prop_fields

    """
    
    
    form = ProposalFieldForm(request.POST or None)
    get_place = get_object_or_404(Space, url=space_url)
    if request.method == 'POST':
        if form.is_valid():
            form_data = form.save()
            proposal_fields = ProposalField.objects.filter(proposalset=form_data.proposalset)
            return render_to_response("proposals/proposal_add_fields.html", {'form_data':form_data,\
                                        'get_place':get_place, 'prop_fields':proposal_fields,'form':form},\
                                        context_instance = RequestContext(request))
    return render_to_response("proposals/proposal_add_fields.html", {'form':form, 'get_place':get_place\
                                },context_instance = RequestContext(request))



def remove_proposal_field(request, space_url):
    
    """
    Removes a form field from proposal form. Only for proposals which are in proposal set.

    ..versionadded:: 0.1.5

    :arguments: space_url
    :context: d_form, get_place, delete_field

    """
    
    d_form = ProposalFieldDeleteForm(request.POST or None)
    get_place = get_object_or_404(Space, url=space_url)
    if request.method == 'POST':
        if d_form.is_valid():
            form_data = d_form.save(commit=False)
            delete_field = ProposalField.objects.filter(proposalset=form_data.proposalset, field_name=form_data.field_name)
            delete_field.delete()
            return render_to_response("proposals/proposalform_remove_field.html", {'form':d_form, 'get_place':get_place,\
                                        'deleted_field':form_data}, context_instance = RequestContext(request))

    return render_to_response("proposals/proposalform_remove_field.html", {'form':d_form, 'get_place':get_place}, \
                                context_instance = RequestContext(request))


def proposal_to_set(request, space_url):
    
    """
    Allows to select a proposal set to which a proposal need to be added.

    .. versionadded:: 0.1.5

    :arguments: space_url 
    :context: form, get_place

    """


    sel_form = ProposalSetSelectForm(request.POST or None)
    get_place = get_object_or_404(Space, url=space_url)

    if request.method == 'POST':
        if sel_form.is_valid():
            return redirect('/spaces/'+ space_url +'/proposal/add/'+request.POST['proposalset']+'/')

    return render_to_response("proposals/proposalset_select_form.html", {'form':sel_form, 'get_place':get_place},\
                                context_instance = RequestContext(request))

       
 

def mergedproposal_to_set(request, space_url):

    """
    Allows to select a proposal set to which a merged proposal need to be added

    :arguments: space_url 
    :context:form, get_place

    """

    sel_form = ProposalSetSelectForm(request.POST or None)
    get_place = get_object_or_404(Space, url=space_url)

    if request.method == 'POST':
        if sel_form.is_valid():
            return redirect('/spaces/'+ space_url +'/proposal/merged/'+ request.POST['proposalset'] +'/')

    return render_to_response("proposals/mergedproposal_in_set.html",{'form':sel_form, 'get_place':get_place}, \
                                context_instance = RequestContext(request))


   
def merged_proposal(request, space_url, p_set):
    
    """
    Create a new merged proposal. This proposal can be linked to many other proposals which are in the
    same proposal set. Only admin and moderator can create merged proposals.

    .. versionadded:: 0.1.5

    :arguments: space_url, p_set
    :context:form, get_place, form_field

    """


    get_place = get_object_or_404(Space, url=space_url)
    field = ProposalField.objects.filter(proposalset=p_set)
    form_field = [f_name.field_name for f_name in field]
    if request.method == 'POST':
        merged_form = ProposalForm(request.POST)
        if merged_form.is_valid():
            form_data = merged_form.save(commit=False)
            form_data.proposalset = get_object_or_404(ProposalSet, pk=p_set)
            form_data.space = get_object_or_404(Space, url=space_url)
            form_data.author = request.user
            form_data.merged = True
            field = ProposalField.objects.filter(proposalset=p_set)
            form_field = [f_name.field_name for f_name in field]
            form_data.save()
            merged_form.save_m2m()
            return redirect('/spaces/'+ space_url +'/')
    else: 
        merged_form = ProposalMergeForm(initial={'p_set':p_set})

    return render_to_response("proposals/proposal_merged.html",{'form':merged_form, 'get_place':get_place, \
                                'form_field':form_field},context_instance = RequestContext(request))
#
# Proposal Sets
#

class ListProposalSet(ListView):

    """
    List all the proposal set in a space.
    
    .. versionadded: 0.1.5
    
    :rtype: Object list
    :context: setlist
    """
    paginate_by = 20
    context_object_name = 'setlist'
    
    def get_queryset(self):
        place = get_object_or_404(Space, url=self.kwargs['space_url'])
        objects = ProposalSet.objects.all()
        return objects
    
    def get_context_data(self, **kwargs):
        context = super(ListProposalSet, self).get_context_data(**kwargs)
        context['get_place'] = get_object_or_404(Space, url=self.kwargs['space_url'])
        return context
    
class ViewProposalSet(ListView):

    """
    List all the proposals inside a proposals set.
    
    .. versionadded 0.1.5
    
    :rtype: Object list
    :context: proposalset
    """
    paginate_by = 50
    context_object_name = 'proposalset'
    template_name = 'proposals/proposalset_detail.html'
    
    def get_queryset(self):
        place = get_object_or_404(Space, url=self.kwargs['space_url'])
        objects = Proposal.objects.all().filter(proposalset=self.kwargs['set_id']).order_by('pub_date')
        return objects
    
    def get_context_data(self, **kwargs):
        context = super(ViewProposalSet, self).get_context_data(**kwargs)
        context['get_place'] = get_object_or_404(Space, url=self.kwargs['space_url'])
        return context

class AddProposalSet(FormView):

    """
    Create a new prpoposal set, it can be related to a debate or be in free mode,
    which is not linked to anything. If it's linked to a debate, people can
    make their proposals related to the debate notes.
    
    .. versionadded: 0.1.5
    
    :rtype: Form object
    :context: form, get_place
    """
    form_class = ProposalSetForm
    template_name = 'proposals/proposalset_form.html'
    
    def get_success_url(self):
        return '/spaces/' + self.kwargs['space_url']
    
    def form_valid(self, form):
        self.space = get_object_or_404(Space, url=self.kwargs['space_url'])
        form_uncommited = form.save(commit=False)
        form_uncommited.space = self.space
        form_uncommited.author = self.request.user
        form_uncommited.save()
        return super(AddProposalSet, self).form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super(AddProposalSet, self).get_context_data(**kwargs)
        self.space = get_object_or_404(Space, url=self.kwargs['space_url'])
        context['get_place'] = self.space
        return context
        
    @method_decorator(permission_required('proposals.add_proposalset'))
    def dispatch(self, *args, **kwargs):
        return super(AddProposalSet, self).dispatch(*args, **kwargs)
        
class EditProposalSet(UpdateView):

    """
    Modify an already created proposal set.
    
    .. versionadded: 0.1.5
    
    :rtype: Form object
    :context: form, get_place
    """
    model = ProposalSet
    template_name = 'proposals/proposalset_form.html'
    
    def get_success_url(self):
        return '/spaces/{0}/proposal/psets/{1}/'.format(self.kwargs['space_url'], self.kwargs['set_id'])
        
    def get_object(self):
        propset_id = self.kwargs['set_id']
        return get_object_or_404(ProposalSet, pk = propset_id)
        
    def get_context_data(self, **kwargs):
        context = super(EditProposalSet, self).get_context_data(**kwargs)
        context['get_place'] = get_object_or_404(Space, url=self.kwargs['space_url'])
        return context
        
    @method_decorator(permission_required('proposals.edit_proposalset'))
    def dispatch(self, *args, **kwargs):
        return super(EditProposalSet, self).dispatch(*args, **kwargs)

class DeleteProposalSet(DeleteView):

    """
    Delete a proposal set.
    
    .. versionadded: 0.1.5
    
    :rtype: Confirmation
    :context: get_place
    """
    def get_object(self):
        return get_object_or_404(ProposalSet, pk = self.kwargs['set_id'])

    def get_success_url(self):
        current_space = self.kwargs['space_url']
        return '/spaces/{0}'.format(current_space)

    def get_context_data(self, **kwargs):
        context = super(DeleteProposalSet, self).get_context_data(**kwargs)
        context['get_place'] = get_object_or_404(Space, url=self.kwargs['space_url'])
        return context                 
