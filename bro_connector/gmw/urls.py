"""gmw URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from gmw.views import gmw_map_context
from main.dash import visualisatie_meetopstelling
from django.contrib import admin

# Some initialisation/discovery stuff
admin.autodiscover()
visualisatie_meetopstelling # noqa

urlpatterns = [
    path("map/", gmw_map_context, name="gmw_map"),
]
