from django.core.management.base import BaseCommand
from gld.models import GroundwaterLevelDossier
import requests
import xml.etree.ElementTree as ET
import datetime

class Command(BaseCommand):
    def handle(self, *args, **options):
        glds = GroundwaterLevelDossier.objects.filter(
            quality_regime__isnull=True
        ).all()
        print("Number of GLDs without a quality regime before: ",len(glds))

        if glds:
            for i,gld in enumerate(glds,1):
                bro_id = gld.gld_bro_id
                quality_regime = extract_quality_regime(bro_id,False)
                gld.quality_regime = quality_regime
                gld.save() 

                if i % 50 == 0:
                    print(f"{i} GLDs saved")

        glds = GroundwaterLevelDossier.objects.filter(
            quality_regime__isnull=True
        ).all()
        print("Number of GLDs without a quality regime before: ",len(glds))          

def extract_quality_regime(id,filtered):
    basis_url = "https://publiek.broservices.nl/gm/gld/v1/objects/"
    now = datetime.datetime.now().date()

    if filtered:
        f = "JA"
    else:
        f = "NEE"

    results = requests.get(
        f"{basis_url}{id}?requestReference=BRO-Import-script-{now}&observationPeriodBeginDate=1900-01-01&observationPeriodEndDate={now}&filtered={f}"
    )
    root = ET.fromstring(results.content)
    namespaces = {
        "brocom": "http://www.broservices.nl/xsd/brocommon/3.0"
    }
    quality_regime = root.find(".//brocom:qualityRegime", namespaces).text

    if not quality_regime:
        quality_regime = "IMBRO/A"
        print("No quality regime in xml for id: ",id)

    return quality_regime