# -*- coding: utf-8 -*-
import floppyforms
from django import forms
from treenode.utils import split_pks
from .models import MarketerNode




class MarketerNodeForm(forms.ModelForm):
    split_cut = forms.DecimalField(min_value=0, max_value=100)
    class Meta:
        model = MarketerNode
        exclude = []

        # def __init__(self, *args, **kwargs):
        #     super(MarketerNodeForm, self).__init__(*args, **kwargs)
        # if 'tn_parent' not in self.fields:
        #     return
        # exclude_pks = []
        # obj = self.instance
        # if obj.pk:
        #     exclude_pks += [obj.pk]
        #     exclude_pks += split_pks(obj.tn_descendants_pks)
        # manager = obj.__class__.objects
        # self.fields['tn_parent'].queryset = manager.exclude(pk__in=exclude_pks)
