import datetime
import xml.etree.ElementTree as ET

import requests
from django.core.management.base import BaseCommand
from gld.models import GroundwaterLevelDossier


class Command(BaseCommand):
    def handle(self, *args, **options):
        glds = GroundwaterLevelDossier.objects.all()
        print("Number of GLDs to loop through: ", len(glds))

        if glds:
            for i, gld in enumerate(glds, 1):
                quality_regime = extract_quality_regime(gld, False)
                if quality_regime != gld.quality_regime:
                    print(
                        "Updating quality regime of GLD: ",
                        gld.groundwater_level_dossier_id,
                    )
                    gld.quality_regime = quality_regime
                    gld.save()

                if i % 50 == 0:
                    print(f"{len(glds) - i} GLDs to go")

        glds = GroundwaterLevelDossier.objects.filter(quality_regime__isnull=True).all()
        print("Number of GLDs without a quality regime: ", len(glds))


def extract_quality_regime(gld: GroundwaterLevelDossier, filtered):
    basis_url = "https://publiek.broservices.nl/gm/gld/v1/objects/"
    now = datetime.datetime.now().date()

    if filtered:
        f = "JA"
    else:
        f = "NEE"

    bro_id = gld.gld_bro_id
    start_date = gld.research_start_date

    if bro_id:
        results = requests.get(
            f"{basis_url}{bro_id}?requestReference=BRO-Import-script-{now}&observationPeriodBeginDate=1900-01-01&observationPeriodEndDate={now}&filtered={f}"
        )
        root = ET.fromstring(results.content)
        namespaces = {"brocom": "http://www.broservices.nl/xsd/brocommon/3.0"}
        quality_regime_xml = root.find(".//brocom:qualityRegime", namespaces)

        if quality_regime_xml is None:
            quality_regime = "IMBRO/A"
            print("No quality regime in xml for id: ", bro_id)
        else:
            quality_regime = quality_regime_xml.text

    else:
        if start_date < datetime.date(2021, 1, 1):
            quality_regime = "IMBRO/A"
        else:
            quality_regime = "IMBRO"

    return quality_regime
