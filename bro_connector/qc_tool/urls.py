from django.urls import path
from qc_tool.views import render_qc_tool
from qc_tool import test_app

test_app

urlpatterns = [
    path("qc_tool/", render_qc_tool, name="tool"),
]