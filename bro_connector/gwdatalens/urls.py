from django.urls import path

from gwdatalens.views import render_gwdatalens_tool

urlpatterns = [
    path("gwdatalens/", render_gwdatalens_tool, name="gwdatalens"),
]
