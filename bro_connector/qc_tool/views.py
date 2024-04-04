# Create your views here.
from django.shortcuts import render
from qc_tool import test_app
from django.contrib import admin

# Some initialisation/discovery stuff
admin.autodiscover()
test_app

def render_qc_tool(request):
    return render(request, "dash.html")