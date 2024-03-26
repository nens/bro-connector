# Create your views here.
from django.shortcuts import render
import qc_tool.app

def render_qc_tool(request):
    return render(request, "dash.html")