from django.urls import path
from qc_tool.views import render_qc_tool
import qc_tool.app

urlpatterns = [
    path("qc_tool/", render_qc_tool, name="qc_tool"),
]