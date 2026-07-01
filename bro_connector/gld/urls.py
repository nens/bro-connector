from django.urls import path

from gld.api_views import ObservationMeasurementsUpdateView

urlpatterns = [
    path(
        "observation/measurements/",
        ObservationMeasurementsUpdateView.as_view(),
        name="observation-measurements-update",
    ),
]
