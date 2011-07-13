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
This file contains all the forms for the debate modules.
"""

from django.forms import ModelForm
from django.forms.models import modelformset_factory

from e_cidadania.apps.debate.models import Debate, Phase, Note

class DebateForm(ModelForm):

    """
    Returns a form created from the Debate data model.
    
    :rtype: HTML Form
    
    .. versionadded:: 0.1b
    """
    class Meta:
        model = Debate

# Create a FormSet with the Phase model
PhaseFormSet = modelformset_factory(Phase, extra=1)

class NoteForm(ModelForm):

    """
    Returns an HTML Form to create or edit a new 'note' or 'proposal' like it's
    called on the sociologists argot.
    
    :rtype: HTML Form
    
    .. versionadded:: 0.1b
    """
    class Meta:
        model = Note
