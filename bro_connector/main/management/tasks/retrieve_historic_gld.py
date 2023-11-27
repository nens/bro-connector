from ..tasks.bro_handlers import GLDHandler
from ..tasks.kvk_handler import DataRetrieverKVK
from ..tasks.progressor import Progress


from gld.models import (
    GroundwaterLevelDossier
)

# BBOX VALUES ZEELAND
XMIN=10000
XMAX=80000
YMIN=355000
YMAX=420000

def within_bbox(coordinates) -> bool:
    print(f"x: {coordinates.x}, y: {coordinates.y}")
    if (
        coordinates.x > XMIN and
        coordinates.x < XMAX and
        coordinates.y > YMIN and
        coordinates.y < YMAX
    ):
        return True
    return False

def run(kvk_number:str=None, csv_file:str=None, bro_type:str = 'gld'):
    progressor = Progress()
    gld        = GLDHandler()

    if kvk_number != None:
        DR = DataRetrieverKVK(kvk_number)
        DR.request_bro_ids(bro_type)
        DR.get_ids_kvk()
        ids = DR.gld_ids
        ids_ini_count = len(ids)

    print(f"{ids_ini_count} bro ids found for organisation.")

    for gld in GroundwaterLevelDossier.objects.all():
        if gld.gld_bro_id in ids:
            ids.remove(gld.gld_bro_id)

    ids_count = len(ids)
    print(f"{ids_count} not in database.")

    progressor.calibrate(ids, 25)

    # Import the well data
    for id in range(ids_count):
        print(ids[id])
        gld.get_data(ids[id], True)
        gld.root_data_to_dictionary()
        gmw_dict = gld.dict
        print(gmw_dict)



class InitializeData:
    def __init__(self, gmw_dict: dict) -> None:
        self.gmw_dict = gmw_dict

    def groundwater_level_dossier(self) -> None:
        self.dossier = GroundwaterLevelDossier.objects.create(
            gmw_bro_id = self.gmw_dict["broId"][1],
            gld_bro_id = self.gmw_dict["broId"][0],
            research_start_date = self.gmw_dict.get("researchFirstDate"),
            research_last_date = self.gmw_dict.get("researchLastDate"),
            research_last_correction = self.gmw_dict.get("latestCorrectionTime"),
        )