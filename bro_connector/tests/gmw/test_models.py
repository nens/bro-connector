import pytest
from django.contrib.gis.geos import Point

from bro.models import Organisation
from gmw.models import GroundwaterMonitoringWellStatic
from main.settings.base import KVK_USER


@pytest.fixture
@pytest.mark.django_db
def default_organisation():
    return Organisation.objects.create(
        name="Test Organisation",
        kvk_number=int(KVK_USER),
    )


@pytest.mark.django_db
def test_deliver_to_bro_default_function(default_organisation):
    gmw = GroundwaterMonitoringWellStatic.objects.create(
        delivery_accountable_party=default_organisation,
        coordinates=Point(0, 0),  # adjust field name to match your model
    )

    tube = gmw.tube.first()

    assert tube.deliver_gld_to_bro == True