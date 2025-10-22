"""main URL Configuration

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

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, reverse_lazy
from django.views.generic.base import RedirectView
from gwdatalens.app import app as gwdatalens_app
from gwdatalens.views import render_gwdatalens_tool
from main.dash import visualisatie_meetopstelling

admin.autodiscover()
gwdatalens_app  # noqa
visualisatie_meetopstelling  # noqa

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url=reverse_lazy("admin:index"))),
    path("", include(("gmw.urls", "gmw"), namespace="gmw")),
    path("django_plotly_dash/", include("django_plotly_dash.urls")),
    path("gwdatalens/", render_gwdatalens_tool, name="gwdatalens"),
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
