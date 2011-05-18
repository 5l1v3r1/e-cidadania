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

from django.conf.urls.defaults import *
from e_cidadania.apps.spaces.views import GoToSpace, ViewSpaceIndex


urlpatterns = patterns('e_cidadania.apps.spaces.views',

    # News
    (r'^(?P<space_name>\w+)/news/', include('e_cidadania.apps.news.urls')),

    # Proposals
    (r'^(?P<space_name>\w+)/proposal/', include('e_cidadania.apps.proposals.urls')),

    # Documents
    # Please note: Documents are integrated in spaces, they share views.
    (r'^(?P<space_name>\w+)/docs/add', 'add_doc'),

    (r'^(?P<space_name>\w+)/docs/(?P<doc_id>\d+)/edit/', 'edit_doc'),

    (r'^(?P<space_name>\w+)/docs/(?P<doc_id>\d+)/delete/', 'delete_doc'),

    (r'^(?P<space_name>\w+)/docs/', 'list_all_docs'),

    # Spaces
    (r'^(?P<space_name>\w+)/edit/', 'edit_space'),

    (r'^(?P<space_name>\w+)/delete/', 'delete_space'),

    (r'^add/', 'create_space'),

    (r'^go/', GoToSpace.as_view()),

#    (r'^go/', 'go_to_space'),

    (r'^(?P<space_name>\w+)/', ViewSpaceIndex.as_view()),

#    (r'^(?P<space_name>\w+)/', 'view_space_index'),

    # Debates
    #(r'^debate/', include('e_cidadania.apps.debates.urls')),

)

