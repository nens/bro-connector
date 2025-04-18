import requests
import requests.auth
from abc import ABC, abstractmethod
import xml.etree.ElementTree as ET


DB_NAME = "grondwatermeetnet"
DB_USER = "postgres"
DB_PASS = "!StNS!2023"
DB_HOST = "localhost"
DB_PORT = "5432"


class BROHandler(ABC):
    @abstractmethod
    def get_data(self, id: str, full_history: bool) -> None:
        pass

    @abstractmethod
    def root_data_to_dictionary(self):
        pass

    @abstractmethod
    def reset_values(self):
        pass


class GMWHandler(BROHandler):
    def __init__(self):
        self.number_of_events = 0
        self.number_of_tubes = 0
        self.number_of_geo_ohm_cables = 0
        self.number_of_electrodes = 0
        self.positions = 0
        self.dict = {}

    def get_data(self, file: str) -> None:
        with open(file, "r") as xml_file:
            data = xml_file.read()
            self.root = ET.fromstring(data)

    def root_data_to_dictionary(self):
        tags = []
        values = []
        prefix = ""
        number_of_events = self.number_of_events

        for element in self.root.iter():
            tag = element.tag
            split = tag.split("}")

            if split[1] == "wellConstructionDate":
                prefix = "construction_"

            if split[1] == "deliveredLocation":
                prefix = ""

            if split[1] == "intermediateEvent":
                number_of_events = number_of_events + 1
                prefix = "event_" + str(number_of_events) + "_"

            if split[1] == "wellRemovalDate":
                prefix = "removal_"

            if split[1] == "monitoringTube":
                self.number_of_tubes = self.number_of_tubes + 1
                prefix = "tube_" + str(self.number_of_tubes) + "_"

            if split[1] == "geoOhmCable":
                self.number_of_geo_ohm_cables = self.number_of_geo_ohm_cables + 1
                prefix = f"tube_{self.number_of_tubes}_geo_ohm_{str(self.number_of_geo_ohm_cables)}_"

            if split[1] == "electrode":
                self.number_of_electrodes = self.number_of_electrodes + 1
                prefix = f"tube_{self.number_of_tubes}_geo_ohm_{str(self.number_of_geo_ohm_cables)}_electrode_{str(self.number_of_electrodes)}_"

            tag = str(prefix) + split[1]

            if split[1] == "pos":
                self.positions = self.positions + 1
                postfix = f"_{self.positions}"
                tag = split[1] + postfix
                tags.append(tag)
                values.append(element.text)
            else:
                tags.append(tag)
                values.append("".join(element.text.split()))

        self.number_of_events = number_of_events

        self.dict = dict(zip(tags, values))

    def reset_values(self):
        self.number_of_events = 0
        self.number_of_tubes = 0
        self.number_of_geo_ohm_cables = 0
        self.number_of_electrodes = 0
        self.positions = 0


class GLDHandler(BROHandler):
    def __init__(self):
        self.number_of_points = 0
        self.number_of_observations = 0
        self.dict = {}

    def get_data(self, id: str, filtered: bool):
        basis_url = "https://publiek.broservices.nl/gm/gld/v1/objects/"

        if filtered:
            f = "JA"
        else:
            f = "NEE"

        gmw_verzoek = requests.get(f"{basis_url}{id}?fullHistory={f}")

        self.root = ET.fromstring(gmw_verzoek.content)

    def root_data_to_dictionary(self):
        tags = []
        values = []
        point_value = []
        time = []
        qualifier = []
        bro_ids = []
        units = []
        number_of_observations = self.number_of_observations
        prefix = f"{number_of_observations}_"

        number_of_points = self.number_of_points
        number_of_observations = self.number_of_observations

        for element in self.root.iter():
            tag = element.tag
            split = tag.split("}")

            if split[1] == "observation":
                number_of_observations = number_of_observations + 1
                prefix = f"{number_of_observations}_"

            if split[1] == "broId":
                bro_ids.append(element.text)

            # If point, add prefix
            if split[1] == "point":
                number_of_points = number_of_points + 1
                prefix = f"{number_of_observations}_point_"

            if split[1] == "NamedValue":
                prefix = f"{number_of_observations}_nv_"

            # If qualifier values add different prefix
            if split[1] == "qualifier":
                prefix = f"{number_of_observations}_point_qualifier_"

            tag = str(prefix) + split[1]

            # Once the last property of qualifier has been itererated (value), reset prefix.
            if tag == f"{number_of_observations}_point_qualifier_value":
                prefix = f"{number_of_observations}_"

            # Once the last property of qualifier has been itererated (value), reset prefix.
            if tag == f"{number_of_observations}_nv_value":
                # Take the codespace, split it at every : and use the last section.
                # E.g. = {codeSpace: 'urn:bro:gld:ObservationType'}
                tag = f"{number_of_observations}_{element.attrib['codeSpace'].split(sep=':')[-1]}"
                prefix = f"{number_of_observations}_"

            values_value = element.text

            if tag == f"{number_of_observations}_processReference":
                values_value = element.attrib[
                    "{http://www.w3.org/1999/xlink}href"
                ].split(sep=":")[-1]

            if tag == f"{number_of_observations}_status":
                values_value = element.attrib[
                    "{http://www.w3.org/1999/xlink}href"
                ].split(sep=":")[-1]

            if tag == f"{number_of_observations}_broId":
                values_value = bro_ids

            if tag.startswith(f"{number_of_observations}_point_"):
                if tag == f"{number_of_observations}_point_time":
                    time.append(element.text)
                    values_value = time

                if tag == f"{number_of_observations}_point_value":
                    point_value.append(element.text)
                    values_value = point_value

                    # Add the unit
                    tags.append(f"{number_of_observations}_unit")
                    try:
                        units.append(element.attrib["uom"])
                        values.append(units)
                    except AttributeError as e:
                        print(e)
                        print(element.attrib, element.text)

                if tag == f"{number_of_observations}_point_qualifier_value":
                    qualifier.append(element.text)
                    values_value = qualifier

            tags.append(tag)
            values.append(values_value)

        self.dict = dict(zip(tags, values))
        self.number_of_observations = number_of_observations
        self.number_of_points = number_of_points

    def reset_values(self):
        self.number_of_points = 0
        self.number_of_observations = 0


class GMNHandler(BROHandler):
    def __init__(self):
        self.dict = {}

    def get_data(self, id: str, full_history: bool):
        basis_url = "https://publiek.broservices.nl/gm/gmn/v1/objects/"

        if full_history:
            fh = "ja"
        else:
            fh = "nee"

        gmw_verzoek = requests.get("{}{}?fullHistory={}".format(basis_url, id, fh))

        self.root = ET.fromstring(gmw_verzoek.content)

    def root_data_to_dictionary(self):
        tags = []
        values = []
        prefix = ""

        for element in self.root.iter():
            tag = element.tag
            split = tag.split("}")

            tag = str(prefix) + split[1]

            tags.append(tag)
            values.append(element.text)

        self.dict = dict(zip(tags, values))

    def reset_values(self):
        pass


class GARHandler(BROHandler):
    def __init__(self):
        self.dict = {}

    def get_data(self, id: str, full_history: bool):
        basis_url = "https://publiek.broservices.nl/gm/gar/v1/objects/"

        if full_history:
            fh = "ja"
        else:
            fh = "nee"

        gmw_verzoek = requests.get("{}{}?fullHistory={}".format(basis_url, id, fh))

        self.root = ET.fromstring(gmw_verzoek.content)

    def root_data_to_dictionary(self):
        tags = []
        values = []
        prefix = ""

        for element in self.root.iter():
            tag = element.tag
            split = tag.split("}")

            tag = str(prefix) + split[1]

            tags.append(tag)
            values.append(element.text)

        self.dict = dict(zip(tags, values))

    def reset_values(self):
        pass


class FRDHandler(BROHandler):
    def __init__(self):
        self.dict = {}

    def get_data(self, id: str, full_history: bool):
        basis_url = "https://publiek.broservices.nl/gm/frd/v1/objects/"

        if full_history:
            fh = "ja"
        else:
            fh = "nee"

        gmw_verzoek = requests.get("{}{}?fullHistory={}".format(basis_url, id, fh))

        self.root = ET.fromstring(gmw_verzoek.content)

    def root_data_to_dictionary(self):
        tags = []
        values = []
        prefix = ""

        for element in self.root.iter():
            tag = element.tag
            split = tag.split("}")

            tag = str(prefix) + split[1]

            tags.append(tag)
            values.append(element.text)

        self.dict = dict(zip(tags, values))

    def reset_values(self):
        pass
