from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from datetime import datetime
from django.views import View
from mlmtools.models import TrackCode, MarketerNode

def get_granted_node_ids(request):
    ''' Returns list of ids the current user is allowed to see '''
    if request.user.is_superuser:
        return [ x["pk"] for x in MarketerNode.objects.all().values('pk') ]
    node_ids = []
    for node in MarketerNode.objects.filter(owner=request.user):
        node_ids += [node.pk] + [nn.pk for nn in node.descendants]
    return node_ids

@staff_member_required
def list_codes(request):
    node_ids = get_granted_node_ids(request)
    c = {"code_list" : TrackCode.objects.filter(node_id__in=node_ids),
         "granted_node_ids" : node_ids}
    return render(request, "mlmtools/list_codes.html", c)

@staff_member_required
def code_detail(request, code):
    c = { "code" : TrackCode.objects.get(code=code)}
    c["granted_node_ids"] = get_granted_node_ids(request)
    if c["code"].node.pk not in c["granted_node_ids"]:
        raise PermissionDenied("not allowed to view this node")
    if request.GET.get("since"):
        request.session["since"] = request.GET.get("since")
    if request.GET.get("until"):
        request.session["until"] = request.GET.get("until")
    c["since"] = request.session.get("since", (datetime.now().date() - timedelta(days=30)).isoformat())
    c["until"] = request.session.get("until", (datetime.now().date() + timedelta(days=3)).isoformat())
    c["usages"] = c["code"].codeuse_set.filter(used_at__gte=c["since"], used_at__lt=c["until"]).order_by("-used_at")
    return render(request, "mlmtools/code_detail.html", c)

@staff_member_required
def node_detail(request, pk):
    c = {"node" : MarketerNode.objects.get(id=pk)}
    c["granted_node_ids"] = get_granted_node_ids(request)
    if c["node"].pk not in c["granted_node_ids"]:
        raise PermissionDenied("not allowed to view this node")
    if request.GET.get("since"):
        request.session["since"] = request.GET.get("since")
    if request.GET.get("until"):
        request.session["until"] = request.GET.get("until")
    c["since"] = request.session.get("since", (datetime.now().date() - timedelta(days=30)).isoformat())
    c["until"] = request.session.get("until", (datetime.now().date() + timedelta(days=3)).isoformat())
    c["provisions"] = c["node"].get_provisions_for_period(c["since"], c["until"])
    c["provisions_tree"] = c["node"].get_provisions_tree_for_period(c["since"], c["until"])
    c["total_provisions"] = c["node"].get_sum_provisions_for_period(c["since"], c["until"])
    return render(request, "mlmtools/node_detail.html", c)
