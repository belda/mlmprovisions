from django.conf.urls import url, include
from mlmtools.views import list_codes, code_detail, node_detail

urlpatterns = [
    url("^list_codes/", list_codes, name="list_codes"),
    url("^code_detail/(?P<code>[A-Za-z0-9]{4,15})/", code_detail, name="code_detail"),
    url("^node_detail/(?P<pk>[0-9]+)/", node_detail, name="node_detail"),
]