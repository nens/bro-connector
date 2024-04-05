from django.urls import path, include
from qc_tool.views import render_qc_tool
import qc_tool.app.app
# import qc_tool.test_app

urlpatterns = [
    path("qc_tool/", render_qc_tool, name="SimpleExample"),
]
