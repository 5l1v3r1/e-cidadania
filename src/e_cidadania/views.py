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

from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic.create_update import update_object
from django.views.generic.create_update import delete_object
from django.views.generic.list_detail import object_detail

from e_cidadania.apps.news.models import Post
from e_cidadania.apps.news.forms import NewsForm
from e_cidadania.apps.spaces.models import Space

def index_view(request):

    """
    Main view for the index page. It's separated from the urls.py file
    because using directo_to_template in urls.py doesn't refresh the content
    (it's loaded only once).
    """
    pub = Post.objects.filter(post_pub_index=True).order_by('-post_pubdate')
    space_list = Space.objects.all()

    extra_context = {
        'publication': pub,
        'spaces': space_list,
    }

    return render_to_response('site_index.html',
                              extra_context,
                              context_instance=RequestContext(request))

###############
# BIG WARNING #
###############

# The following code violates the DRY principle. Repeating exactly the same
# code as in apps/news/views.py

@permission_required('Post.add_post')
def add_news(request):

    """
    This is a DRY violation. This is a reimplementation of the news view
    located at apps.news.views
    """
    form = NewsForm(request.POST or None)

    if request.POST:
        form_uncommited = form.save(commit=False)
        form_uncommited.post_author = request.user
        form_uncommited.post_pub_index = True

        if form.is_valid():
            form_uncommited.save()
            return redirect('/')

    return render_to_response('news/post_add.html',
                              {'form': form},
                              context_instance=RequestContext(request))

@permission_required('Post.delete_post')
def delete_post(request, post_id):

    """
    Delete an existent post. Post deletion is only reserved to spaces
    administrators or site admins.
    """
    return delete_object(request,
                         model = Post,
                         object_id = post_id,
                         login_required=True,
                         template_name = 'news/post_delete.html',
                         post_delete_redirect = '/')

@permission_required('Post.edit_post')
def edit_post(request, post_id):

    """
    Edit an existent post.
    """

    return update_object(request,
                         model = Post,
                         object_id = post_id,
                         login_required = True,
                         post_save_redirect = '/',
                         template_name = 'news/post_edit.html')

def view_post(request, post_id):

    """
    View a post with comments.
    """

    return object_detail(request,
                         queryset = Post.objects.all(),
                         object_id = post_id,
                         template_name = 'news/post_detail.html',
                         template_object_name = 'news')

