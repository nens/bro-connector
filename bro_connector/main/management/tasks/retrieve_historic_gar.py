from ..tasks.bro_handlers import GARHandler
from ..tasks.kvk_handler import DataRetrieverKVK
from ..tasks.progressor import Progress


# BBOX VALUES ZEELAND
XMIN = 10000
XMAX = 80000
YMIN = 355000
YMAX = 420000


def within_bbox(coordinates) -> bool:
    print(f"x: {coordinates.x}, y: {coordinates.y}")
    if (
        coordinates.x > XMIN
        and coordinates.x < XMAX
        and coordinates.y > YMIN
        and coordinates.y < YMAX
    ):
        return True
    return False


def run(kvk_number: str = None, csv_file: str = None, bro_type: str = "gld"):
    progressor = Progress()
    gar = GARHandler()

    if kvk_number != None:
        DR = DataRetrieverKVK(kvk_number)
        DR.request_bro_ids(bro_type)
        DR.get_ids_kvk()
        ids = DR.gld_ids
        ids_ini_count = len(ids)

    print(f"{ids_ini_count} bro ids found for organisation.")

    for gar in garmodel.objects.all():
        if gar.gld_bro_id in ids:
            ids.remove(gar.gld_bro_id)

    ids_count = len(ids)
    print(f"{ids_count} not in database.")

    progressor.calibrate(ids, 25)

    # Import the well data
    for id in range(ids_count):
        print(id)
