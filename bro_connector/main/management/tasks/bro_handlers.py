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

    def get_data(self, id: str, full_history: bool):
        basis_url = "https://publiek.broservices.nl/gm/gmw/v1/objects/"

        if full_history:
            fh = "ja"
        else:
            fh = "nee"

        gmw_verzoek = requests.get("{}{}?fullHistory={}".format(basis_url, id, fh))
        print(gmw_verzoek.content)
        print(id)
        self.root = ET.fromstring(gmw_verzoek.content)

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

            if split[1] == "intermediateEvent":
                number_of_events = number_of_events + 1
                number_of_event_tubes = 0
                prefix = f"event_{str(number_of_events)}_"

            if split[1] == "tubeData":
                number_of_event_tubes = number_of_event_tubes + 1
                prefix = f"event_{str(number_of_events)}_{str(number_of_event_tubes)}_"

            if split[1] == "wellRemovalDate":
                prefix = "removal_"

            if split[1] == "monitoringTube":
                self.number_of_tubes = self.number_of_tubes + 1
                prefix = f"tube_{str(self.number_of_tubes)}_"

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
        self.count_dictionary = {}
        self.dict = {}

        # Initializing list to use in the dictionary making process.
        self.point_value = []
        self.time = []
        self.qualifier = []
        self.bro_ids = []
        self.units = []
        self.censoring_limit_value = []
        self.censoring_limit_reason = []
        self.censoring_limit_unit = []

    def get_data(self, id: str, filtered: bool):
        basis_url = "https://publiek.broservices.nl/gm/gld/v1/objects/"

        if filtered:
            f = "JA"
        else:
            f = "NEE"

        gmw_verzoek = requests.get(f"{basis_url}{id}?fullHistory={f}")
        print(gmw_verzoek)
        self.root = ET.fromstring(gmw_verzoek.content)

    def append_censoring(self) -> None:
        self.censoring_limit_value.append("None")
        self.censoring_limit_reason.append("None")
        self.censoring_limit_unit.append("None")
        self.dict.update(
            {
                f"{self.number_of_observations}_point_censoring_censoredReason": self.censoring_limit_reason,
                f"{self.number_of_observations}_point_censoring_uom": self.censoring_limit_unit,
                f"{self.number_of_observations}_point_censoring_value": self.censoring_limit_value,
            }
        )

    def root_data_to_dictionary(self):
        prefix = f"{self.number_of_observations}_"

        for element in self.root.iter():
            tag = element.tag
            split = tag.split("}")

            if split[1] == f"observation":
                if self.number_of_observations != 0:
                    if self.number_of_observations == 1:
                        self.count_dictionary[
                            self.number_of_observations
                        ] = self.number_of_points

                    else:
                        self.count_dictionary[self.number_of_observations] = (
                            self.number_of_points
                            - self.count_dictionary[self.number_of_observations - 1]
                        )

                self.number_of_observations = self.number_of_observations + 1
                prefix = f"{self.number_of_observations}_"

            if split[1] == f"broId":
                self.bro_ids.append(element.text)

            # If point, add prefix
            if split[1] == f"point":
                self.number_of_points = self.number_of_points + 1
                prefix = f"{self.number_of_observations}_point_"
                self.append_censoring()

            if split[1] == f"NamedValue":
                prefix = f"{self.number_of_observations}_nv_"

            # If qualifier values add different prefix
            if split[1] == "qualifier":
                prefix = f"{self.number_of_observations}_point_qualifier_"

            if split[1] == "Quantity":
                prefix = f"{self.number_of_observations}_point_censoring_"

            tag = str(prefix) + split[1]

            # Once the last property of qualifier has been itererated (value), reset prefix.
            if tag == f"{self.number_of_observations}_point_qualifier_value":
                prefix = f"{self.number_of_observations}_"

            # Once the last property of qualifier has been itererated (value), reset prefix.
            if tag == f"{self.number_of_observations}_nv_value":
                # Take the codespace, split it at every : and use the last section.
                # E.g. = {codeSpace: 'urn:bro:gld:ObservationType'}
                tag = f"{self.number_of_observations}_{element.attrib['codeSpace'].split(sep=':')[-1]}"
                prefix = f"{self.number_of_observations}_"

            values_value = element.text

            if tag == f"{self.number_of_observations}_processReference":
                values_value = element.attrib[
                    "{http://www.w3.org/1999/xlink}href"
                ].split(sep=":")[-1]

            if tag == f"{self.number_of_observations}_status":
                values_value = element.attrib[
                    "{http://www.w3.org/1999/xlink}href"
                ].split(sep=":")[-1]

            if tag == f"{self.number_of_observations}_broId":
                values_value = self.bro_ids

            if tag.startswith(f"{self.number_of_observations}_point_"):
                if tag == f"{self.number_of_observations}_point_time":
                    self.time.append(element.text)
                    values_value = self.time

                if tag == f"{self.number_of_observations}_point_value":
                    self.point_value.append(element.text)
                    values_value = self.point_value

                    # Add the unit
                    if element.text is None:
                        self.units.append("-")
                        self.dict.update(
                            {f"{self.number_of_observations}_unit": self.units}
                        )

                    else:
                        self.units.append(element.attrib["uom"])
                        self.dict.update(
                            {f"{self.number_of_observations}_unit": self.units}
                        )

                if tag == f"{self.number_of_observations}_point_qualifier_value":
                    self.qualifier.append(element.text)
                    values_value = self.qualifier

                if tag == f"{self.number_of_observations}_point_censoring_value":
                    self.censoring_limit_value[self.number_of_points - 1] = element.text
                    values_value = self.censoring_limit_value

                if tag == f"{self.number_of_observations}_point_censoring_uom":
                    censor_unit = element.attrib["code"]
                    self.censoring_limit_unit[self.number_of_points - 1] = censor_unit
                    values_value = self.censoring_limit_unit

                if (
                    tag
                    == f"{self.number_of_observations}_point_censoring_censoredReason"
                ):
                    censor_reason = element.attrib[
                        "{http://www.w3.org/1999/xlink}href"
                    ].split("/")[-1]
                    self.censoring_limit_reason[
                        self.number_of_points - 1
                    ] = censor_reason
                    values_value = self.censoring_limit_reason

            self.dict.update({tag: values_value})

    def reset_values(self):
        self.number_of_points = 0
        self.number_of_observations = 0
        self.count_dictionary = {}
        self.point_value = []
        self.time = []
        self.qualifier = []
        self.bro_ids = []
        self.units = []
        self.censoring_limit_value = []
        self.censoring_limit_reason = []
        self.censoring_limit_unit = []


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
