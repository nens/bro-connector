import os
import time
from typing import Type
from django.db.models.query import QuerySet
from abc import ABC, abstractmethod
from collections import defaultdict
from django.core.management.base import BaseCommand
import bro_exchange as brx

from frd.models import (
    FormationResistanceDossier,
    FrdSyncLog,
    MeasurementConfiguration,
    GeoOhmMeasurementMethod,
    GeoOhmMeasurementValue,
    ElectrodePair,
    GMWElectrodeReference,
    CalculatedFormationresistanceMethod,
    FormationresistanceSeries,
    FormationresistanceRecord,
    InstrumentConfiguration,
    ElectromagneticMeasurementMethod,
    ElectromagneticRecord,
    ElectromagneticSeries,
    InstrumentConfiguration,
)
from datetime import datetime, date
from main.settings.base import FRD_SETTINGS


def get_xml_payload(xml_filepath):
    """
    Creates a payload of the xml file, based on the filepath
    """
    filepath = xml_filepath
    with open(filepath) as file:
        xml_payload = file.read()

    return xml_payload


def get_unsynced_dossiers(frd_queryset):
    if frd_queryset:
        return frd_queryset.filter(
            frd_bro_id=None, closed_in_bro=False
        )
    else:
        return FormationResistanceDossier.objects.filter(
            frd_bro_id=None, closed_in_bro=False
        )


def get_unsynced_configurations(frd_queryset):
    if frd_queryset:
        return MeasurementConfiguration.objects.filter(bro_id=None, formation_resistance_dossier__in=frd_queryset)
    else:
        return MeasurementConfiguration.objects.filter(bro_id=None)


def get_closed_dossiers(frd_queryset):
    if frd_queryset:
        return frd_queryset.filter(
        closure_date__isnull=False, frd_bro_id__isnull=False, closed_in_bro=False
    )
    else:
        return FormationResistanceDossier.objects.filter(
        closure_date__isnull=False, frd_bro_id__isnull=False, closed_in_bro=False
    )


def get_unsynced_gem_measurement_methods(frd_queryset):
    if frd_queryset:
        return GeoOhmMeasurementMethod.objects.filter(bro_id=None, formation_resistance_dossier__in=frd_queryset)
    else:
        return GeoOhmMeasurementMethod.objects.filter(bro_id=None)


def get_unsynced_emm_methods(frd_queryset):
    if frd_queryset:
        return ElectromagneticMeasurementMethod.objects.filter(bro_id=None, formation_resistance_dossier__in=frd_queryset)
    else:
        return ElectromagneticMeasurementMethod.objects.filter(bro_id=None)


def get_unsynced_emm_configurations(frd_queryset):
    if frd_queryset:
        return InstrumentConfiguration.objects.filter(bro_id=None, formation_resistance_dossier__in=frd_queryset)
    else:
        return InstrumentConfiguration.objects.filter(bro_id=None)


class Command(BaseCommand):
    """
    Handles the sync between the bro-connector and the BRO.
    Runs daily as cronjob.
    """

    help = "Syncs the FRD data to the BRO"

    def handle(self, *args, **kwargs):
        FRDSync.handle()

class FRDSync:
    def handle(self, frd_queryset=None, check_only=False):
        self.handle_frd_registrations(frd_queryset, check_only)
        self.handle_gem_configurations_registration(frd_queryset, check_only)
        self.handle_frd_closures(frd_queryset, check_only)
        self.handle_gem_measurement_registrations(frd_queryset, check_only)
        self.handle_emm_configurations(frd_queryset, check_only)
        self.handle_emm_measurements(frd_queryset, check_only)


    def handle_frd_registrations(self, frd_queryset, check_only):
        """
        Handles the startregistrations for all FRD's without bro_id.
        For each unsynced FRD, the FrdStartregistration class is used to handle the registration
        """
        unsynced_startregistration_dossiers = get_unsynced_dossiers(frd_queryset)

        for dossier in unsynced_startregistration_dossiers:
            startregistration = FrdStartRegistration(dossier)
            startregistration.sync(check_only)

    def handle_gem_configurations_registration(self, frd_queryset, check_only):
        """
        Handles the measurement configurations for all configurations without bro_id.
        """
        unsynced_configurations = get_unsynced_configurations(frd_queryset)
        per_dossier = defaultdict(list[dict])
        for measurement_configuration in unsynced_configurations:
            per_dossier[
                str(measurement_configuration.formation_resistance_dossier_id)
            ].append(measurement_configuration)

        for key, values in per_dossier.items():
            configuration_registration = GEMConfigurationRegistration(values)
            configuration_registration.sync(check_only)

    def handle_emm_configurations(self, frd_queryset,check_only):
        """
        Handles the emm instrument configurations
        """
        unsynced_configurations = get_unsynced_emm_configurations(frd_queryset)

        for configuration in unsynced_configurations:
            emm_configuration_registration = EMMConfigurationRegistration(configuration)
            emm_configuration_registration.sync(check_only)

    def handle_frd_closures(self,frd_queryset, check_only):
        """
        Closes all FRDs with a closure date.
        Checks if any FRD have a closure date.
        If so, and no allready existing log on a closure is found, a Closure request is done.
        """
        closed_startregistration_dossiers = get_closed_dossiers(frd_queryset)
        for dossier in closed_startregistration_dossiers:
            closure = ClosureRegistration(dossier)
            closure.sync(check_only)

    def handle_gem_measurement_registrations(self, frd_queryset, check_only):
        """
        Handles measurements, this is based on the measurement method, without a bro_id.
        """
        unsynced_measurements_methods = get_unsynced_gem_measurement_methods(frd_queryset)

        for method in unsynced_measurements_methods:
            measurement_registration = GEMMeasurementRegistration(method)
            measurement_registration.sync(check_only)

    def handle_emm_measurements(self, frd_queryset, check_only):
        """
        Handles measurements, this is based on the measurement method, without a bro_id.
        """
        unsynced_emm_methods = get_unsynced_emm_methods(frd_queryset)

        for method in unsynced_emm_methods:
            emm_measurement_registration = EMMMeasurementRegistration(method)
            emm_measurement_registration.sync(check_only)

class Registration(ABC):
    log = FrdSyncLog

    def __init__(self):
        self.output_dir = "frd/xml_files/"
        self.xml_file = None
        self.api_version = FRD_SETTINGS["api_version"]
        self.demo = FRD_SETTINGS["demo"]

        if self.demo:
            self.bro_info = FRD_SETTINGS["bro_info_demo"]
        else:
            self.bro_info = FRD_SETTINGS["bro_info_bro_connector"]

    def check_status(self):
        print(self.log)
        if self.log:
            self.check_delivery()

    def sync(self, check_only):
        """
        Checks if a log on the Dossier already exists.
        If not, creates one and handles the complete startregistrations.
        If so, checks the status, and picks up the startregistration process where it was left.
        """
        if check_only:
            self.check_status()

        else:
            status_function_mapping = {
                None: self.generate_xml_file,
                "failed_to_generate_registration_xml": self.generate_xml_file,
                "failed_to_validate_sourcedocument": self.validate_xml_file,
                "succesfully_generated_registration_xml": self.validate_xml_file,
                "failed_to_deliver_sourcedocuments": self.deliver_xml_file,
                "source_document_validation_succesful": self.deliver_xml_file,
                "succesfully_delivered_sourcedocuments": self.check_delivery,
                "delivery_approved": self.check_delivery,
            }

            current_status = self.log.process_status
            method_to_call = status_function_mapping.get(current_status)
            method_to_call()

    def generate_xml_file(self):
        """
        Handles the generation of the registration xml file.
        If it is succesfull, it calls the validate_registration_xml to continue the registration process.
        """
        try:
            print("Generating XML file")
            self.construct_xml_tree()
            self.save_xml_file()

        except Exception as e:
            self.log.process_status = "failed_to_generate_registration_xml"
            self.log.comment = (f"Error message: {e}",)
            self.log.save()

        else:
            self.log.process_status = "succesfully_generated_registration_xml"
            self.log.comment = "Succesfully generated registration request"
            self.log.xml_filepath = self.filepath
            self.log.save()

            self.validate_xml_file()

    @abstractmethod
    def construct_xml_tree(self):
        """
        Setup the data for the registration xml file.
        Then creates the file and saves the xml tree to self.
        """
        pass

    def save_xml_file(self):
        """
        Saves the xmltree as xml file in the filepath as defined in self.
        """
        self.filepath = os.path.join(self.output_dir, self.filename)
        self.xml_file.write(self.filepath, pretty_print=True)

    def validate_xml_file(self):
        """
        Validates the xml file, using the BRO validations service.
        If the xml file is VALIDE, the deliver_xml_file method is called
        """
        print("Validating XML file")

        if "NIET_VALIDE" in self.log.comment:
            self.generate_xml_file()

        xml_payload = get_xml_payload(self.log.xml_filepath)

        try:
            validation_info = brx.validate_sourcedoc(
                payload=xml_payload,
                bro_info=self.bro_info,
                demo=self.demo,
                api=self.api_version,
            )

        except Exception as e:
            self.log.process_status = "failed_to_validate_sourcedocument"
            self.log.comment = f"Error message: {e}"
            self.log.save()

        # Is this else statement needed?
        else:
            validation_status = validation_info["status"]
            validation_errors = validation_info["errors"]

            if validation_status == "VALIDE":
                self.log.process_status = "source_document_validation_succesful"
                self.log.comment = "Succesfully validated sourcedocument"
                self.log.save()

                self.deliver_xml_file()

            # Could we not return and once again remove the else statement?
            else:
                self.log.process_status = "failed_to_validate_sourcedocument"
                self.log.comment = f"Validation Status: {validation_status}, errors: {validation_errors}"
                self.log.save()

    def deliver_xml_file(self):
        """
        Delivers the xml file after it has succesfully been validated.
        If the delivery status is OK, the check_delivery method is called to check for further details.
        """
        print("Delivering XML File")

        delivery_status = self.log.delivery_status

        if delivery_status == 3:
            self.log.process_status = "The delivery of the xml file has failed 3 times. Please check manually what's going on, and reset the delivery status on 'Nog niet aangeleverd"
            self.log.save()
            return

        xml_payload = get_xml_payload(self.log.xml_filepath)
        xml_filename = self.log.xml_filepath.rsplit("/", 1)[-1]
        request_dict = {xml_filename: xml_payload}

        try:
            upload_info = brx.upload_sourcedocs_from_dict(
                reqs=request_dict,
                token=self.bro_info["token"],
                demo=self.demo,
                project_id=self.bro_info["projectnummer"],
                api=self.api_version,
            )

        except Exception as e:
            delivery_status += 1
            self.log.process_status = "failed_to_deliver_sourcedocuments"
            self.log.comment = f"Error message: {e}"
            self.log.delivery_status = delivery_status
            self.log.save()

        else:
            if upload_info == "Error":
                delivery_status += 1
                self.log.process_status = "failed_to_deliver_sourcedocuments"
                self.log.comment = f"Error message: {upload_info}"
                self.log.delivery_status = delivery_status
                self.log.save()

            else:
                self.log.process_status = "succesfully_delivered_sourcedocuments"
                self.log.comment = "Succesfully delivered registration xml file"
                self.log.delivery_status = 4
                self.log.delivery_status_info = upload_info.json()["status"]
                self.log.delivery_id = upload_info.json()["identifier"]
                self.log.save()

                time.sleep(10)

                self.check_delivery()

    def check_delivery(self):
        """
        Checks the delivery status based on the delivery id.
        Updates the log of the frd, based on the return of the BRO webservice.
        If the delivery is fully succesfull, the finish_registration method is called.
        """
        print("Checking delivery")

        try:
            delivery_status_info = brx.check_delivery_status(
                identifier=self.log.delivery_id,
                token=self.bro_info["token"],
                demo=self.demo,
                api=self.api_version,
                project_id=self.bro_info["projectnummer"],
            )
        except Exception as e:
            self.log.comment = f"Error occured during status check of delivery: {e}"
            self.log.save()
        else:
            delivery_status = delivery_status_info.json()["status"]
            delivery_brondocument_status = delivery_status_info.json()["brondocuments"][
                0
            ]["status"]
            delivery_errors = delivery_status_info.json()["brondocuments"][0]["errors"]

            if (
                delivery_status == "DOORGELEVERD"
                and delivery_brondocument_status == "OPGENOMEN_LVBRO"
            ):
                self.finish_registration(delivery_status_info)
                pass
            elif delivery_errors:
                self.log.comment = (
                    f"Found errors during the delivery check: {delivery_errors}"
                )
                self.log.save()

            else:
                self.log.delivery_status_info = delivery_status_info.json()[
                    "brondocuments"
                ][0]["status"]
                self.log.comment = "Startregistration request not yet approved"
                self.log.save()

    def finish_registration(self, delivery_status_info):
        """
        Updates the log, saves the bro_id to the frd, and removes the xml file.
        """
        self.log.delivery_status_info = delivery_status_info.json()["brondocuments"][0][
            "status"
        ]
        self.log.comment = "Delivery approved"
        self.log.process_status = "delivery_approved"
        self.log.bro_id = delivery_status_info.json()["brondocuments"][0]["broId"]
        self.log.synced = True
        self.log.save()

        self.save_bro_id(delivery_status_info)
        self.remove_xml_file()

    @abstractmethod
    def save_bro_id(self, delivery_status_info):
        """
        Save the Bro_Id to the FRD object
        """
        pass

    def remove_xml_file(self):
        """
        Removes the succesfully delivered xml file.
        """
        os.remove(self.log.xml_filepath)
        return


class FrdStartRegistration(Registration):
    """Creates and delivers 10_FRD_StartRegistration.xml files."""

    def __init__(self, frd_obj: FormationResistanceDossier):
        super().__init__()
        self.frd_obj = frd_obj
        self.log = FrdSyncLog.objects.update_or_create(
            event_type="FRD_StartRegistration",
            frd=self.frd_obj,
            delivery_type="register",
        )[0]
        self.filename = f"frd_startregistration_{self.frd_obj.object_id_accountable_party}_{date.today()}.xml"

    def construct_xml_tree(self):
        quality_regime = self.frd_obj.quality_regime or "IMBRO/A"
        gmn_bro_id = getattr(
            self.frd_obj.groundwater_monitoring_net, "gmn_bro_id", None
        )
        gmw_bro_id = getattr(
            getattr(
                self.frd_obj.groundwater_monitoring_tube,
                "groundwater_monitoring_well_static",
                None,
            ),
            "bro_id",
            None,
        )
        gmw_tube_number = str(
            getattr(self.frd_obj.groundwater_monitoring_tube, "tube_number", None)
        )

        metadata = {
            "request_reference": self.filename,
            "delivery_accountable_party": self.frd_obj.delivery_accountable_party,
            "quality_regime": quality_regime,
        }
        srcdocdata = {
            "object_id_accountable_party": self.frd_obj.object_id_accountable_party,
            "gmn_bro_id": [gmn_bro_id],
            "gmw_bro_id": gmw_bro_id,
            "gmw_tube_number": gmw_tube_number,
        }
        startregistration_tool = brx.FRDStartRegistrationTool(
            metadata, srcdocdata, "registration"
        )
        self.xml_file = startregistration_tool.generate_xml_file()

    def save_bro_id(self, delivery_status_info):
        self.frd_obj.frd_bro_id = delivery_status_info.json()["brondocuments"][0][
            "broId"
        ]
        self.frd_obj.save()


class GEMConfigurationRegistration(Registration):
    """Creates and delivers 11_FRD_GEM_MeasurementConfiguration.xml files."""

    def __init__(self, measurement_configurations: dict):
        super().__init__()
        self.measurement_configurations = measurement_configurations
        self.formation_resistance_dossier = measurement_configurations[
            0
        ].formation_resistance_dossier
        self.log = FrdSyncLog.objects.update_or_create(
            event_type="FRD_GEM_MeasurementConfiguration",
            frd=self.formation_resistance_dossier,
            delivery_type="register",
        )[0]

        # Create filename
        if self.measurement_configurations[0].formation_resistance_dossier.frd_bro_id:
            naming = self.measurement_configurations[
                0
            ].formation_resistance_dossier.frd_bro_id
        else:
            naming = self.measurement_configurations[
                0
            ].formation_resistance_dossier.name

        self.filename = f"configuration_registration_{naming}_{date.today()}.xml"

    def format_request_reference(self):
        return f"registration_mc_{self.formation_resistance_dossier.frd_bro_id}_{datetime.now().date()}"

    def format_electrode_reference(self, electrode: GMWElectrodeReference):
        return {
            "cable_number": electrode.cable_number,
            "electrode_number": electrode.electrode_number,
        }

    def format_electrode_pair(self, pair: ElectrodePair):
        return {
            "elektrode1": self.format_electrode_reference(pair.elektrode1),
            "elektrode2": self.format_electrode_reference(pair.elektrode2),
        }

    def configuration_to_list_of_dict(self) -> list:
        configurations_list = []
        for config in self.measurement_configurations:
            config_dict = {
                "name": config.configuration_name,
                "measurement_pair": self.format_electrode_pair(config.measurement_pair),
                "flowcurrent_pair": self.format_electrode_pair(config.flowcurrent_pair),
            }
            configurations_list.append(config_dict)
        return configurations_list

    def construct_xml_tree(self):
        quality_regime = self.formation_resistance_dossier.quality_regime or "IMBRO/A"

        metadata = {
            "request_reference": self.filename,
            "delivery_accountable_party": self.formation_resistance_dossier.delivery_accountable_party,
            "bro_id": self.formation_resistance_dossier.frd_bro_id,
            "quality_regime": quality_regime,
        }

        srcdocdata = {
            "object_id_accountable_party": self.formation_resistance_dossier.object_id_accountable_party,
            "request_reference": self.format_request_reference(),
            "measurement_configurations": self.configuration_to_list_of_dict(),
        }

        configuration_registration_tool = brx.GEMConfigurationTool(
            metadata, srcdocdata, "registration"
        )
        self.xml_file = configuration_registration_tool.generate_xml_file()

    def save_bro_id(self, delivery_status_info):
        for configuration in self.measurement_configurations:
            configuration.bro_id = delivery_status_info.json()["brondocuments"][0][
                "broId"
            ]
            configuration.save()


class ClosureRegistration(Registration):
    """Creates and delivers 15_FRD_Closure.xml files."""

    def __init__(self, dossier):
        super().__init__()
        self.frd_obj = dossier
        self.log = FrdSyncLog.objects.update_or_create(
            event_type="FRD_Closure", frd=self.frd_obj, delivery_type="register"
        )[0]
        self.filename = (
            f"closure_registration_{self.frd_obj.frd_bro_id}_{date.today()}.xml"
        )

    def construct_xml_tree(self):
        quality_regime = self.frd_obj.quality_regime or "IMBRO/A"

        metadata = {
            "request_reference": self.filename,
            "delivery_accountable_party": self.frd_obj.delivery_accountable_party,
            "bro_id": self.frd_obj.frd_bro_id,
            "quality_regime": quality_regime,
        }

        closure_registration_tool = brx.FRDClosureTool(
            metadata=metadata, request_type="registration"
        )
        self.xml_file = closure_registration_tool.generate_xml_file()

    def save_bro_id(self, delivery_status_info):
        self.frd_obj.closed_in_bro = True
        self.frd_obj.save()


class GEMMeasurementRegistration(Registration):
    """Creates and delivers 12_FRD_GEM_Measurement.xml files."""

    def __init__(self, method):
        super().__init__()
        self.method_obj = method
        self.frd_obj = self.method_obj.formation_resistance_dossier
        self.log = FrdSyncLog.objects.update_or_create(
            event_type="FRD_GEM_Measurement",
            frd=self.frd_obj,
            delivery_type="register",
            geo_ohm_measuring_method=self.method_obj,
        )[0]
        self.filename = (
            f"measurement_registration_{self.frd_obj.frd_bro_id}_{date.today()}.xml"
        )

    def construct_xml_tree(self):
        quality_regime = self.frd_obj.quality_regime or "IMBRO/A"

        metadata = {
            "request_reference": self.filename,
            "delivery_accountable_party": self.frd_obj.delivery_accountable_party,
            "bro_id": self.frd_obj.frd_bro_id,
            "quality_regime": quality_regime,
        }

        measurement_date = self.method_obj.measurement_date.strftime("%Y-%m-%d")
        measurements_data = self._get_measurements()
        calculated_method = self._get_calculated_method()
        calculated_values = self._create_calculated_values_string(calculated_method)

        srcdocdata = {
            "measurement_date": measurement_date,
            "measuring_responsible_party": self.method_obj.measuring_responsible_party,
            "measuring_procedure": self.method_obj.measuring_procedure,
            "evaluation_procedure": self.method_obj.assessment_procedure,
            "measurements": measurements_data,
            "calculated_method_responsible_party": calculated_method.responsible_party,
            "calculated_method_procedure": calculated_method.assessment_procedure,
            "measurement_count": len(measurements_data),
            "calculated_values": calculated_values,
        }

        measurment_registration_tool = brx.GEMMeasurementTool(
            metadata, srcdocdata, "registration"
        )
        self.xml_file = measurment_registration_tool.generate_xml_file()

    def _get_measurements(self) -> list[dict]:
        """Queries the measurements linked to the method"""
        measurements = GeoOhmMeasurementValue.objects.filter(
            geo_ohm_measurement_method=self.method_obj
        )
        return [
            (
                measurement.measurement_configuration.configuration_name,
                measurement.formationresistance,
            )
            for measurement in measurements
        ]

    def _get_calculated_method(self) -> Type[CalculatedFormationresistanceMethod]:
        """Queries the related CalculatedFormationresistanceMethod"""
        return CalculatedFormationresistanceMethod.objects.filter(geo_ohm_measurement_method=self.method_obj).first()
    
    def _create_calculated_values_string(self, calculated_method) -> str:
        """Looks up all calulated apperent fromation resistance values.

        Returns the str format required for the FRD XML file.
        Example from the BRO: '-8.20,245,goedgekeurd -8.40,230,goedgekeurd -8.60,210,goedgekeurd -13.20,10.5,goedgekeurd -13.60,4.5,goedgekeurd'
        This consists of a list, seperated by spaces.
        Each item in the list consists of: vertical position, resistance value, status quality control.
        """
        series = self._get_series(calculated_method)
        calculated_resistance_values = self._get_calculated_resistance_values(series)

        string_elements = [
            f"{value_obj.vertical_position},{value_obj.formationresistance},{value_obj.status_qualitycontrol}"
            for value_obj in calculated_resistance_values
        ]

        string = " ".join(string_elements)

        return string

    def _get_series(self, calculated_method) -> Type[FormationresistanceSeries]:
        """Looks up the series related to calculated formation method"""
        return FormationresistanceSeries.objects.filter(calculated_formationresistance=calculated_method).first()

    def _get_calculated_resistance_values(
        self, series
    ) -> QuerySet[FormationresistanceRecord]:
        """Looks up the  calculated formation resistance values, based on a series"""
        return FormationresistanceRecord.objects.filter(series=series)

    def save_bro_id(self, delivery_status_info):
        pass
        self.method_obj.bro_id = delivery_status_info.json()[
            "brondocuments"
        ][0]["broId"]
        self.method_obj.save()



class EMMConfigurationRegistration(Registration):
    """Creates and delivers 13_FRD_EMM_InstrumentConfiguration.xml files."""

    def __init__(self, instrument_configuration: dict):
        super().__init__()
        self.instrument_configuration = instrument_configuration
        self.formation_resistance_dossier = (
            instrument_configuration.formation_resistance_dossier
        )
        self.log = FrdSyncLog.objects.update_or_create(
            event_type="FRD_EMM_InstrumentConfiguration",
            frd=self.formation_resistance_dossier,
            delivery_type="register",
        )[0]

        # Create filename
        if self.instrument_configuration.formation_resistance_dossier.frd_bro_id:
            naming = (
                self.instrument_configuration.formation_resistance_dossier.frd_bro_id
            )
        else:
            naming = self.instrument_configuration.formation_resistance_dossier.name

        self.filename = f"configuration_registration_{naming}_{date.today()}.xml"

    def construct_xml_tree(self):
        quality_regime = self.formation_resistance_dossier.quality_regime or "IMBRO/A"

        metadata = {
            "request_reference": self.instrument_configuration.configuration_name,
            "delivery_accountable_party": self.formation_resistance_dossier.delivery_accountable_party,
            "bro_id": self.formation_resistance_dossier.frd_bro_id,
            "quality_regime": quality_regime,
        }

        srcdocdata = {
            "instrument_configuration_id": self.instrument_configuration.configuration_name,
            "relative_position_transmitter_coil": self.instrument_configuration.relative_position_send_coil,
            "relative_position_primary_receiver_coil": self.instrument_configuration.relative_position_receive_coil,
            "secondary_receiver_coil_available": self.instrument_configuration.secondary_receive_coil,
            "coil_frequency_known": self.instrument_configuration.coilfrequency_known,
            "instrument_length": self.instrument_configuration.instrument_length,
        }

        if self.instrument_configuration.secondary_receive_coil == "ja":
            srcdocdata[
                "relative_position_secondary_receiver_coil"
            ] = self.instrument_configuration.relative_position_secondary_coil

        if self.instrument_configuration.coilfrequency_known == "ja":
            srcdocdata["coilfrequency"] = self.instrument_configuration.coilfrequency

        configuration_registration_tool = brx.EMMConfigurationTool(
            metadata, srcdocdata, "registration"
        )
        self.xml_file = configuration_registration_tool.generate_xml_file()

    def save_bro_id(self, delivery_status_info):
        self.instrument_configuration.bro_id = delivery_status_info.json()[
            "brondocuments"
        ][0]["broId"]
        self.instrument_configuration.save()


class EMMMeasurementRegistration(Registration):
    """Creates and delivers 14_FRD_EMM_Measurement.xml files."""

    def __init__(self, method: Type[ElectromagneticMeasurementMethod]):
        super().__init__()
        self.method_obj = method
        self.frd_obj = self.method_obj.formation_resistance_dossier
        self.log = FrdSyncLog.objects.update_or_create(
            event_type="FRD_EMM_Measurement",
            frd=self.frd_obj,
            delivery_type="register",
            electomagnetic_method=self.method_obj,
        )[0]
        self.filename = (
            f"measurement_registration_{self.frd_obj.frd_bro_id}_{date.today()}.xml"
        )

    def construct_xml_tree(self):
        quality_regime = self.frd_obj.quality_regime or "IMBRO/A"

        metadata = {
            "request_reference": self.filename,
            "delivery_accountable_party": self.frd_obj.delivery_accountable_party,
            "bro_id": self.frd_obj.frd_bro_id,
            "quality_regime": quality_regime,
        }

        measurement_date = self.method_obj.measurement_date.strftime("%Y-%m-%d")
        measurement_records, measurement_records_count = self._get_measurement_data()
        calculated_method = self._get_calculated_method()
        calculated_records, calculated_records_count = self._get_calculated_data(
            calculated_method
        )
        instrument_config = self._get_config()

        srcdocdata = {
            "measurement_date": measurement_date,
            "measuring_responsible_party": self.method_obj.measuring_responsible_party,
            "measuring_procedure": self.method_obj.measuring_procedure,
            "evaluation_procedure": self.method_obj.assessment_procedure,
            "element_count":measurement_records_count,
            "measurement_data":measurement_records,
            "related_instrument_config":instrument_config.configuration_name,
            "calculated_measurement_operator":calculated_method.responsible_party,
            "calculated_determination_procedure":calculated_method.assessment_procedure,
            "formation_measurement_data_count":calculated_records_count,
            "formation_measurement_data":calculated_records,

        }

        emm_measurment_registration_tool = brx.EMMMeasurementTool(
            metadata, srcdocdata, "registration"
        )
        self.xml_file = emm_measurment_registration_tool.generate_xml_file()

    def _get_config(self):
        return InstrumentConfiguration.objects.filter(formation_resistance_dossier=self.frd_obj).first()

    def _get_measurement_data(self):
        series = self._get_related_series()
        records = self._get_records(series)

        count = len(records)

        string_elements = [
            f"{value_obj.vertical_position},{value_obj.primary_measurement},{value_obj.secondary_measurement if value_obj.secondary_measurement is not None else 'NaN'}"
            for value_obj in records
        ]

        string = " ".join(string_elements)

        return string, count

    def _get_related_series(self):
        return ElectromagneticSeries.objects.filter(electromagnetic_measurement_method=self.method_obj).first()
    
    def _get_records(self,series):
        return ElectromagneticRecord.objects.filter(series=series)

    def _get_calculated_method(self) -> Type[CalculatedFormationresistanceMethod]:
        """Queries the related CalculatedFormationresistanceMethod"""
        return CalculatedFormationresistanceMethod.objects.filter(electromagnetic_measurement_method=self.method_obj).first()  

    def _get_calculated_data(self, calculated_method):
        series = self._get_related_formation_series(calculated_method)
        records = self._get_formation_records(series)

        count = len(records)

        string_elements = [
            f"{value_obj.vertical_position},{value_obj.formationresistance},{value_obj.status_qualitycontrol}"
            for value_obj in records
        ]

        string = " ".join(string_elements)

        return string, count

    def _get_related_formation_series(self, calculated_method):
        return FormationresistanceSeries.objects.filter(calculated_formationresistance=calculated_method).first()
    
    def _get_formation_records(self,series):
        return FormationresistanceRecord.objects.filter(series=series)

    def save_bro_id(self, delivery_status_info):
        self.method_obj.bro_id = delivery_status_info.json()[
            "brondocuments"
        ][0]["broId"]
        self.method_obj.save()
