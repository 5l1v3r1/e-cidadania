# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Cidadanía Coop.
# Written by: Oscar Carballal Prego <info@oscarcp.com>
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
    Spaces views
    ===========
    
    These are the views that control the spaces, meetings and documents.
"""

import datetime

# Generic class-based views
from django.views.generic.base import TemplateView, RedirectView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView

# Decorators. the first is a wrapper to convert function-based decorators
# to method decorators that can be put in subclass methods.
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required

# Response types
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404, redirect

# Some extras
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.template import RequestContext

# Function-based views
from django.views.generic.list_detail import object_list, object_detail
from django.views.generic.create_update import create_object, update_object
from django.views.generic.create_update import delete_object

# e-cidadania data models
from e_cidadania.apps.spaces.models import Space, Entity, Document, Meeting
from e_cidadania.apps.news.models import Post
from e_cidadania.apps.spaces.forms import SpaceForm, DocForm, MeetingForm, \
    EntityForm, EntityFormSet
from e_cidadania.apps.proposals.models import Proposal

#
# SPACE VIEWS
#

class GoToSpace(RedirectView):

    """
    *Inherits from* RedirectView
    
    Sends the user to the selected space. This class only accepts GET petitions.  
    """
    def get_redirect_url(self, **kwargs):
        self.place = get_object_or_404(Space, name = self.request.GET['spaces'])
        return '/spaces/{0}'.format(self.place.url)


class ListSpaces(ListView):

    """
    *Inherits from* ListView
    
    Return a spaces list in the system (except private ones) using a generic view.
    The users associated to a private spaces will see it, but not the other private
    spaces.
    """
    model = Space
    

class ViewSpaceIndex(DetailView):

    """
    Returns the index page for a space. This function has multiple extra
    contexts to get all the hardcoded modules information (meetings and documents).
        
    The access to spaces is restricted and filtered in the get_object method. 
    """
    context_object_name = 'get_place'
    template_name = 'spaces/space_index.html'
    
    def get_object(self):
        space_name = self.kwargs['space_name']
        space_object = get_object_or_404(Space, url = space_name)

        if space_object.public == True or self.request.user.is_staff:
            return space_object

        if self.request.user.is_anonymous():
            self.template_name = 'not_allowed.html'
            return space_object

        for i in self.request.user.profile.spaces.all():
            if i.url == space_name:
                return space_object

        self.template_name = 'not_allowed.html'
        return space_object.none()

    # Get extra context data
    def get_context_data(self, **kwargs):
        context = super(ViewSpaceIndex, self).get_context_data(**kwargs)
        place = get_object_or_404(Space, url=self.kwargs['space_name'])
        context['entities'] = Entity.objects.filter(space=place.id)
        context['documents'] = Document.objects.filter(space=place.id)
        context['proposals'] = Proposal.objects.filter(space=place.id).order_by('-pub_date')
        context['publication'] = Post.objects.filter(post_space=place.id).order_by('-post_pubdate')
        return context


#class EditSpace(UpdateView):

#    """
#    Class-based edit space view
#    """
#    form_class = SpaceForm
#    context_object_name = 'form'
#    template_name = 'spaces/space_edit.html'
#    

#    
#    def get_success_url(self):
#        return '/spaces/' + self.kwargs['space_name']
#    
#    def form_valid(self, form):
#        form_uncommited = form.save(commit = False)
#        form_uncommited.author = request.user
#        form_uncommited.save()
#        space = form_uncommited.url
    
#    def form_invalid(self):
#        self.template_name = 'space
    
@permission_required('spaces.edit_space')
def edit_space(request, space_name):

    """
    Returns a forms filled with the current space data to edit it. Access to
    this view is restricted only to site and space administrators.
    
    The filter for space administrators is given by the edit_space permission
    and their belonging to that space.
    
    Parameters
    ----------
    
        - space_name: The url name of the space.
        
    Variables
    ---------
        
        - place: get the space object through the space_name (which is unique)
        - form: SpaceForm instance containing the data related to the current space.
        - form_uncommited: The form instance before saving, so we caqn modify its
                           contents.
    """
    place = get_object_or_404(Space, url=space_name)

    form = SpaceForm(request.POST or None, request.FILES or None, instance=place)

    if request.method == 'POST':
        form_uncommited = form.save(commit=False)
        form_uncommited.author = request.user
        if form.is_valid():
            form_uncommited.save()
            space = form_uncommited.url
            return redirect('/spaces/' + space)

    for i in request.user.profile.spaces.all():
        if i.url == space_name or request.user.is_staff:
            return render_to_response('spaces/space_edit.html',
                              {'form': form, 'get_place': place},
                              context_instance=RequestContext(request))
            
    return render_to_response('not_allowed.html', context_instance=RequestContext(request))

class DeleteSpace(DeleteView):

    """
    Returns a confirmation page before deleting the space object completely.
    This delete function does not delete the space related content. Only the
    site administrators can delete a space.
    """
    context_object_name = 'get_place'
    success_url = '/'

    @method_decorator(permission_required('spaces.delete_space'))
    def dispatch(self, *args, **kwargs):
        return super(DeleteSpace, self).dispatch(*args, **kwargs)

    def get_object(self):
        return get_object_or_404(Space, url = self.kwargs['space_name'])


@permission_required('spaces.add_space')
def create_space(request):

    """
        Returns a SpaceForm form to fill with data to create a new space. There
        is an attached EntityFormset to save the entities related to the space.
    """
    space_form = SpaceForm(request.POST or None, request.FILES or None)
    entity_forms = EntityFormSet(request.POST or None, request.FILES or None,
                                 queryset=Entity.objects.none())
    
    if request.user.is_staff:    
        if request.method == 'POST':
            space_form_uncommited = space_form.save(commit=False)
            space_form_uncommited.author = request.user
    
            if space_form.is_valid() and entity_forms.is_valid():
                new_space = space_form_uncommited.save()
                space = get_object_or_404(Space, name=space_form_uncommited.name)
    
                ef_uncommited = entity_forms.save(commit=False)
                for ef in ef_uncommited:
                    ef.space = space
                    ef.save()
                # We add the created spaces to the user allowed spaces
    
                request.user.profile.spaces.add(space)
                return redirect('/spaces/' + space.url)
    
        return render_to_response('spaces/space_add.html',
                              {'form': space_form,
                               'entityformset': entity_forms},
                              context_instance=RequestContext(request))
    else:
        return render_to_response('not_allowed.html',
                                  context_instance=RequestContext(request))

#
# DOCUMENTS VIEWS
#

class ListDocs(ListView):

    """
    ListDocs(ListView)
        Returns a list with all the documents related to that space.
    """
    paginate_by = 25
    context_object_name = 'document_list'

    def get_queryset(self):
        place = get_object_or_404(Space, url=self.kwargs['space_name'])
        objects = Document.objects.all().filter(space=place.id).order_by('pub_date')
        
        if self.request.user.is_staff:
            return objects
        
        if self.request.user.is_anonymous():
            self.template_name = 'not_allowed.html'
            return objects
        
        for i in self.request.user.profile.spaces.all():
            if i.url == place:
                return objects
        
        self.template_name = 'not_allowed.html'
        return objects

    def get_context_data(self, **kwargs):
        context = super(ListDocs, self).get_context_data(**kwargs)
        context['get_place'] = get_object_or_404(Space, url=self.kwargs['space_name'])
        return context


@permission_required('spaces.add_document')
def add_doc(request, space_name):

    """
    Upload a new document whithin a space. This view is exactly as the create
    space view.
    """

    doc = Document()
    form = DocForm(request.POST or None, request.FILES or None, instance=doc)
    place = get_object_or_404(Space, url=space_name)
    
    for i in request.user.profile.spaces.all():
        if i.url == space_name or request.user.is_staff:
    
            if request.method == 'POST':
                form_uncommited = form.save(commit=False)
                form_uncommited.space = place
                form_uncommited.author = request.user
                if form.is_valid():
                    form_uncommited.save()
                    return redirect('/spaces/' + space_name)
        
            return render_to_response('spaces/document_add.html',
                                      {'form': form, 'get_place': place},
                                      context_instance=RequestContext(request))
    return render_to_response('not_allowed.html',
                              context_instance=RequestContext(request))

@permission_required('spaces.edit_document')
def edit_doc(request, space_name, doc_id):

    """
    Edit uploaded documents :)
    """
    place = get_object_or_404(Space, url=space_name)

    return update_object(request,
                         model = Document,
                         object_id = doc_id,
                         login_required = True,
                         template_name = 'spaces/document_edit.html',
                         template_object_name = 'doc',
                         post_save_redirect = '/',
                         extra_context = {'get_place': place,
                                          'doc': get_object_or_404(Document, pk=doc_id)}
                        )

class DeleteDocument(DeleteView):

    """
    Delete an uploaded document.
    """
        
    def get_object(self):
        return get_object_or_404(Document, pk = self.kwargs['doc_id'])
    
    def get_success_url(self):
        current_space = self.kwargs['space_name']
        return '/spaces/{0}'.format(current_space)
        
    def get_context_data(self, **kwargs):
        context = super(DeleteDocument, self).get_context_data(**kwargs)
        context['get_place'] = get_object_or_404(Space, url=self.kwargs['space_name'])
        return context

#
# MEETING VIEWS
#

class ListMeetings(ListView):

    """
    List all the meetings filtered by the current space
    """
    paginate_by = 25
    context_object_name = 'meeting_list'

    def get_queryset(self):
        place = get_object_or_404(Space, url=self.kwargs['space_name'])
        objects = Meeting.objects.all().filter(space=place.id).order_by\
            ('meeting_date')
        return objects

    def get_context_data(self, **kwargs):
        context = super(ListMeetings, self).get_context_data(**kwargs)
        context['get_place'] = get_object_or_404(Space, url=self.kwargs['space_name'])
        return context


class ViewMeeting(DetailView):
    
    """
    View the meeting description.
    """
    context_object_name = 'meeting'
    template_name = 'spaces/meeting_detail.html'

    def get_object(self):
        space_name = self.kwargs['space_name']

        if self.request.user.is_anonymous():
            self.template_name = 'not_allowed.html'
            return get_object_or_404(Space, url = space_name)

        return get_object_or_404(Meeting, pk = self.kwargs['meeting_id'])

    def get_context_data(self, **kwargs):
        context = super(ViewMeeting, self).get_context_data(**kwargs)
        context['get_place'] = get_object_or_404(Space, url=self.kwargs['space_name'])
        return context
        
def add_meeting(request, space_name):
    
    """
    Create a new meeting. Space and author fields are autmatically filled with
    the request data.
    """
    form = MeetingForm(request.POST or None)
    place = get_object_or_404(Space, url=space_name)
    
    if request.method == 'POST':
        form_uncommited = form.save(commit=False)
        form_uncommited.meeting_author = request.user
        form_uncommited.space = place
        if form.is_valid():
            form_uncommited.save()
            return redirect('/spaces/' + space_name)
    
    return render_to_response('spaces/meeting_add.html',
                              {'form': form, 'get_place': place},
                              context_instance=RequestContext(request))

def edit_meeting(request, space_name, meeting_id):

    """
    """
    place = get_object_or_404(Space, url=space_name)

    return update_object(request,
                         model = Meeting,
                         object_id = meeting_id,
                         login_required = True,
                         template_name = 'spaces/meeting_edit.html',
                         template_object_name = 'meeting',
                         post_save_redirect = '/',
                         extra_context = {'get_place': place})


class DeleteMeeting(DeleteView):

    """
    Delete an uploaded document.
    """

    def get_object(self):
        return get_object_or_404(Meeting, pk = self.kwargs['meeting_id'])

    def get_success_url(self):
        current_space = self.kwargs['space_name']
        return '/spaces/{0}'.format(current_space)
   
    def get_context_data(self, **kwargs):
        context = super(DeleteMeeting, self).get_context_data(**kwargs)
        context['get_place'] = get_object_or_404(Space, url=self.kwargs['space_name'])
        return context
        
class ListPosts(ListView):

    """
    Lists all the news posts within a space. This function can be global for
    the news module because we can't know in which space we are to filter it.
    """
    paginate_by = 25
    context_object_name = 'post_list'
    template_name = 'spaces/news_list.html'
    
    def get_queryset(self):
        place = get_object_or_404(Space, url=self.kwargs['space_name'])
        return Post.objects.all().filter(post_space=place)
    
    
