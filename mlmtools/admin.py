from django.contrib import admin
from django.db.models import Q
from django.utils.safestring import mark_safe
from treenode.admin import TreeNodeModelAdmin
from treenode.utils import split_pks
from mlmtools.forms import MarketerNodeForm
from mlmtools.models import MarketerNode, TrackCode
from django.utils.translation import ugettext as _



class TrackCodeInline(admin.TabularInline):
    model = TrackCode
    extra = 0
    #TODO prevent deletion or discount change after CodeUse exists


@admin.register(MarketerNode)
class MarketerNodeAdmin(TreeNodeModelAdmin):
    list_display = ('name','owner','level','format_split_type','format_split','format_provision','format_my_cut')
    form = MarketerNodeForm
    inlines = [TrackCodeInline]
    MAX_SUB = 4

    def format_my_cut(self, obj):
        return "%.2f%%" % obj.my_cut(100)
    format_my_cut.short_description = _("my cut")

    def format_provision(self, obj):
        return mark_safe("%.2f%% - %.2f%%" % (obj.provision_min(100), obj.max_available(100) ))
    format_provision.short_description = _("provision")

    def format_split(self, obj):
        f = "%.0f/%.0f" % (obj.node_cut, obj.sub_cut)
        if obj.split_type=="treesplit" and obj.parent.split_type=="treesplit":
            return mark_safe("<span style='color: #999;'>"+f+"</span>")
        else:
            return f
    format_split.short_description = _("split")

    def format_split_type(self, obj):
        if obj.split_type=="treesplit" and obj.parent.split_type=="treesplit":
            return mark_safe("<span style='color: #999;'>"+obj.split_type+"</span>")
        else:
            return obj.split_type
    format_split_type.short_description = _("split type")

    def _get_treenode_display_mode(self, request, obj):
        if request.user.is_superuser:
            self.treenode_display_mode = TreeNodeModelAdmin.TREENODE_DISPLAY_MODE_ACCORDION
        else:
            self.treenode_display_mode = TreeNodeModelAdmin.TREENODE_DISPLAY_MODE_INDENTATION
        return self.treenode_display_mode


    def get_queryset(self, request):
        qs = super(MarketerNodeAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        else:
            q = Q(owner_id=request.user.id)
            for i in range(1, self.MAX_SUB):
                q = q | Q( **{"tn_parent__"*i+"owner_id" : request.user.id} )
            return qs.filter(q)


    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "tn_parent":
                exclude_pks = []
                if self.instance:
                    obj = self.instance
                    if obj.pk:
                        exclude_pks += [obj.pk]
                        exclude_pks += split_pks(obj.tn_descendants_pks)
                kwargs["queryset"] = self.get_queryset(request).exclude(pk__in=exclude_pks)
                return db_field.formfield(**kwargs)

        return super(MarketerNodeAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


    def get_form(self, request, obj=None, **kwargs):
        self.instance = obj
        return super(MarketerNodeAdmin, self).get_form(request, obj, **kwargs)


