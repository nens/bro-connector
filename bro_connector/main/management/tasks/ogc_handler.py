import requests
import json


class DataRetrieverOGC:
    def __init__(self, bbox_settings):
        self.bbox = f"bbox={bbox_settings["xmin"]}%2C{bbox_settings["ymin"]}%2C{bbox_settings["xmax"]}%2C{bbox_settings["ymax"]}"
        self.bro_ids = []

    def request_bro_ids(self, type):
        options = ["gmw", "frd", "gar", "gmn", "gld"]
        if type.lower() not in options:
            raise Exception(f"Unknown type: {type}. Use a correct option: {options}.")

        basis_url = "https://api.pdok.nl/"
        ogc_verzoek = requests.get(
            f"{basis_url}/bzk/bro-gminsamenhang-karakteristieken/ogc/v1/collections/gm_{type}/items?{self.bbox}f=json"
        )
        features: list = json.loads(ogc_verzoek.text)["features"]
        self.bro_ids = []
        self.kvk_ids = []
        if features:
            for feature in features:
                self.bro_ids.append(feature["properties"]["bro_id"])
                self.kvk_ids.append(feature["properties"]["delivery_accountable_party"])

    def filter_ids_kvk(self, kvk_number):
        for bro_id, kvk_id in zip(self.bro_ids, self.kvk_ids):
            if kvk_number != kvk_id:
                self.bro_ids.remove(bro_id)

    def get_ids_ogc(self):
        self.gmw_ids = []
        self.gld_ids = []
        self.frd_ids = []
        self.gar_ids = []
        self.gmn_ids = []
        self.other_ids = []

        for id in self.bro_ids:
            print(id)
            if id.startswith("GMW"):
                self.gmw_ids.append(id)

            elif id.startswith("GLD"):
                self.gld_ids.append(id)

            elif id.startswith("FRD"):
                self.frd_ids.append(id)

            elif id.startswith("GAR"):
                self.gar_ids.append(id)

            elif id.startswith("GMN"):
                self.gmn_ids.append(id)

            else:
                self.other_ids.append(id)
