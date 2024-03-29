# Create your views here.
from django.shortcuts import render
import qc_tool.app.app
# import qc_tool.test_app

def render_qc_tool(request):
    return render(request, "dash.html")