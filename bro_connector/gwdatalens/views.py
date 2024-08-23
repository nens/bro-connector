# Create your views here.
from django.shortcuts import render


def render_gwdatalens_tool(request):
    return render(request, "dash.html")
