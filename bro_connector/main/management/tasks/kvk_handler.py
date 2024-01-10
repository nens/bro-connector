import requests
import json


class DataRetrieverKVK:
    def __init__(self, kvk_nummer):
        self.kvk_nummer = kvk_nummer
        self.bro_ids = []

    def request_bro_ids(self, type):
        options = ["gmw", "frd", "gar", "gmn", "gld"]
        if type.lower() not in options:
            raise Exception(f"Unknown type: {type}. Use a correct option: {options}.")

        basis_url = "https://publiek.broservices.nl"
        kvk_verzoek = requests.get(
            f"{basis_url}/gm/{type}/v1/bro-ids?bronhouder={str(self.kvk_nummer)}"
        )
        self.bro_ids = json.loads(kvk_verzoek.text)["broIds"]

    def get_ids_kvk(self):
        self.gmw_ids = []
        self.gld_ids = []
        self.frd_ids = []
        self.gar_ids = []
        self.gmn_ids = []
        self.other_ids = []

        for id in self.bro_ids:
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
