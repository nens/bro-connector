from django.contrib import admin
from django.contrib import messages
import os
from . import models
from main.settings.base import gld_SETTINGS
from gld.management.tasks import gld_actions
from reversion_compare.helpers import patch_admin
import reversion
from gld.management.commands.gld_sync_to_bro import (
    GldSyncHandler,
    get_observation_gld_source_document_data,
)
from .custom_filters import (
    HasOpenObservationFilter,
    CompletelyDeliveredFilter,
    TubeFilter,
    GLDFilter,
    ObservationFilter,
)
import datetime
from gmw.models import GroundwaterMonitoringWellStatic
from gld.models import GroundwaterLevelDossier


def _register(model, admin_class):
    admin.site.register(model, admin_class)


# %% GLD model registration

gld = GldSyncHandler()


class GroundwaterLevelDossierAdmin(admin.ModelAdmin):
    list_display = (
        "groundwater_monitoring_tube",
        "research_start_date",
        "research_last_date",
        "gld_bro_id",
        "quality_regime",
        "first_measurement",
        "completely_delivered",
        "has_open_observation",
        "monitoring_networks",
    )
    list_filter = (
        TubeFilter,
        "quality_regime",
        "research_start_date",
        "research_last_date",
        HasOpenObservationFilter,
        CompletelyDeliveredFilter,
    )

    autocomplete_fields = ("groundwater_monitoring_tube",)

    search_fields = [
        "groundwater_level_dossier_id",
        "gld_bro_id",
        "groundwater_monitoring_tube__groundwater_monitoring_well_static__well_code",
        "groundwater_monitoring_tube__groundwater_monitoring_well_static__bro_id",
        "groundwater_monitoring_tube__groundwater_monitoring_well_static__groundwater_monitoring_well_static_id",
    ]

    autocomplete_fields = ("groundwater_monitoring_tube",)

    readonly_fields = [
        "gld_bro_id",
        "gmw_bro_id",
        "tube_number",
        "most_recent_measurement",
    ]

    actions = ["deliver_to_bro", "check_status"]

    @admin.display(boolean=True)
    def completely_delivered(self, obj):
        return obj.completely_delivered

    completely_delivered.short_description = "Volledig geleverd"

    @admin.display(boolean=True)
    def has_open_observation(self, obj):
        return obj.has_open_observation

    has_open_observation.short_description = "Actief bemeten"

    def monitoring_networks(self, obj):
        nets = ""
        for net in obj.groundwater_monitoring_net.all():
            nets += f"{net.name} "
        return nets

    monitoring_networks.short_description = "Meetnetten"

    def deliver_to_bro(self, request, queryset):
        for dossier in queryset:
            gld_actions.check_and_deliver(dossier)

    def check_status(self, request, queryset):
        for dossier in queryset:
            gld_actions.check_status(dossier)

    deliver_to_bro.short_description = "Deliver GLD to BRO"
    check_status.short_description = "Check GLD status from BRO"


class MeasurementPointMetadataAdmin(admin.ModelAdmin):
    list_max_show_all = 1000  # Prevents loading all records

    search_fields = ["measurement_point_metadata_id", "censor_reason_artesia"]
    list_display = ("__str__",)

    list_filter = (
        "status_quality_control",
        "censor_reason",
    )


class MeasurementTvpAdmin(admin.ModelAdmin):
    list_max_show_all = 1000  # Prevents loading all records

    list_display = ("__str__",)
    autocomplete_fields = ("measurement_point_metadata",)
    list_filter = (ObservationFilter,)


class ObservationAdmin(admin.ModelAdmin):
    list_display = (
        "groundwater_level_dossier",
        "observation_starttime",
        "observation_endtime",
        "result_time",
        "observation_type",
        "measurement_type",
        "status",
        "validation_status",
        "up_to_date_in_bro",
    )
    list_filter = (
        GLDFilter,
        "observation_starttime",
        "observation_endtime",
        "result_time",
        "up_to_date_in_bro",
    )

    search_fields = [
        "groundwater_level_dossier__groundwater_monitoring_tube__groundwater_monitoring_well_static__well_code",
        "groundwater_level_dossier__groundwater_monitoring_tube__groundwater_monitoring_well_static__bro_id",
        "groundwater_level_dossier__gld_bro_id",
    ]

    autocomplete_fields = [
        "groundwater_level_dossier",
        "observation_metadata",
        "observation_process",
    ]

    readonly_fields = [
        "status",
        "validation_status",
        "timestamp_first_measurement",
        "timestamp_last_measurement",
    ]

    actions = ["close_observation", "change_up_to_date_status"]

    def observation_type(self, obj: models.Observation):
        if obj.observation_metadata is not None:
            if obj.observation_metadata.observation_type is not None:
                return obj.observation_metadata.observation_type
        return "-"

    @admin.action(description="Close Observation")
    def close_observation(self, request, queryset):
        for item in queryset.filter(observation_endtime__isnull=True):
            with reversion.create_revision():
                item.observation_endtime = (
                    datetime.datetime.now().astimezone() - datetime.timedelta(seconds=1)
                )
                item.result_time = item.timestamp_last_measurement
                item.save(update_fields=["observation_endtime", "result_time"])
                reversion.set_comment("Closed the observation with a manual action.")

    @admin.action(description="Change up-to-date status.")
    def change_up_to_date_status(self, request, queryset):
        for item in queryset:
            with reversion.create_revision():
                if item.up_to_date_in_bro:
                    item.up_to_date_in_bro = False
                else:
                    item.up_to_date_in_bro = True

                item.save(update_fields=["up_to_date_in_bro"])
                reversion.set_comment("Changed up_to_date_in_bro with a manual action.")


class ObservationMetadataAdmin(admin.ModelAdmin):
    list_display = (
        "observation_metadata_id",
        "observation_type",
        "status",
        "responsible_party",
    )
    list_filter = (
        "observation_metadata_id",
        "observation_type",
        "status",
        "responsible_party",
    )

    search_fields = [
        "observation_type",
        "status",
        "responsible_party",
    ]


class ObservationProcessAdmin(admin.ModelAdmin):
    list_display = (
        "observation_process_id",
        "process_reference",
        "measurement_instrument_type",
        "air_pressure_compensation_type",
        "process_type",
        "evaluation_procedure",
    )
    list_filter = (
        "observation_process_id",
        "process_reference",
        "measurement_instrument_type",
        "air_pressure_compensation_type",
        "process_type",
        "evaluation_procedure",
    )

    search_fields = [
        "process_reference",
        "measurement_instrument_type",
        "air_pressure_compensation_type",
        "evaluation_procedure",
    ]


class gld_registration_logAdmin(admin.ModelAdmin):
    # Retry generate startregistration
    actions = [
        "regenerate_start_registration_sourcedocument",
        "validate_startregistration_sourcedocument",
        "deliver_startregistration_sourcedocument",
        "check_status_startregistration",
    ]

    @admin.action(description="Regenerate startregistration sourcedocument")
    def regenerate_start_registration_sourcedocument(self, request, queryset):
        gld = GldSyncHandler()
        for registration_log in queryset:
            well = GroundwaterMonitoringWellStatic.objects.get(
                bro_id=registration_log.gwm_bro_id
            )
            gld._set_bro_info(well)

            if registration_log.delivery_id is not None:
                self.message_user(
                    request,
                    "Can't generate startregistration sourcedocuments for an existing registration",
                    messages.ERROR,
                )
            else:
                gld.create_start_registration_sourcedocs(
                    well, registration_log.filter_number
                )
                self.message_user(
                    request,
                    "Attempted startregistration sourcedocument regeneration",
                    messages.INFO,
                )

    @admin.action(description="Validate startregistration sourcedocument")
    def validate_startregistration_sourcedocument(self, request, queryset):
        gld = GldSyncHandler()

        for registration_log in queryset:
            well = GroundwaterMonitoringWellStatic.objects.get(
                bro_id=registration_log.gwm_bro_id,
            )
            gld._set_bro_info(well)

            sourcedoc_file = os.path.join(
                gld_SETTINGS["startregistrations_dir"], registration_log.file
            )

            if registration_log.process_status == "failed_to_generate_source_documents":
                self.message_user(
                    request,
                    "Can't validate a startregistration that failed to generate",
                    messages.ERROR,
                )
            elif registration_log.file is None or not os.path.exists(sourcedoc_file):
                self.message_user(
                    request,
                    "There is no sourcedocument file for this startregistration",
                    messages.ERROR,
                )
            elif registration_log.delivery_id is not None:
                self.message_user(
                    request,
                    "Can't validate a document that has already been delivered",
                    messages.ERROR,
                )
            else:
                gld.validate_gld_startregistration_request(
                    registration_log,
                )
                self.message_user(
                    request,
                    "Succesfully validated startregistration sourcedocument",
                    messages.INFO,
                )

    @admin.action(description="Deliver startregistration sourcedocument")
    def deliver_startregistration_sourcedocument(self, request, queryset):
        for registration_log in queryset:
            well = GroundwaterMonitoringWellStatic.objects.get(
                bro_id=registration_log.gwm_bro_id
            )
            gld._set_bro_info(well)

            if registration_log.delivery_id is not None:
                self.message_user(
                    request,
                    "Can't deliver a registration that has already been delivered",
                    messages.ERROR,
                )
            elif registration_log.validation_status == "NIET_VALIDE":
                self.message_user(
                    request,
                    "Can't deliver an invalid document or not yet validated document",
                    messages.ERROR,
                )
            elif registration_log.delivery_status in [
                "AANGELEVERD",
                "OPGENOM EN_LVBRO",
            ]:
                self.message_user(
                    request,
                    "Can't deliver a document that has been already been delivered",
                    messages.ERROR,
                )
            else:
                gld.deliver_startregistration_sourcedocuments(registration_log)

                self.message_user(
                    request,
                    "Attempted registration sourcedocument delivery",
                    messages.INFO,
                )

    @admin.action(description="Check status of startregistration")
    def check_status_startregistration(self, request, queryset):
        gld = GldSyncHandler()

        for registration_log in queryset:
            well = GroundwaterMonitoringWellStatic.objects.get(
                bro_id=registration_log.gwm_bro_id
            )
            gld._set_bro_info(well)

            delivery_id = registration_log.delivery_id
            if delivery_id is None:
                self.message_user(
                    request,
                    "Can't check status of a delivery with no 'delivery_id'",
                    messages.ERROR,
                )
            else:
                gld.check_delivery_status_levering(registration_log)
                self.message_user(
                    request, "Attempted registration status check", messages.INFO
                )

    list_display = (
        "date_modified",
        "gld_bro_id",
        "gwm_bro_id",
        "filter_number",
        "quality_regime",
        "validation_status",
        "delivery_id",
        "delivery_status",
        "process_status",
        "comments",
        "last_changed",
        "corrections_applied",
        "timestamp_end_registration",
        "file",
    )
    list_filter = (
        "date_modified",
        "validation_status",
        "delivery_status",
    )
    readonly_fields = (
        "date_modified",
        "gwm_bro_id",
        "gld_bro_id",
        "filter_number",
        "validation_status",
        "delivery_id",
        "delivery_type",
        "delivery_status",
        "comments",
        "last_changed",
        "corrections_applied",
        "timestamp_end_registration",
        "quality_regime",
        "file",
        "process_status",
    )


class gld_addition_log_Admin(admin.ModelAdmin):
    list_display = (
        "date_modified",
        "broid_registration",
        "observation",
        "observation_identifier",
        "start_date",
        "end_date",
        "validation_status",
        "delivery_type",
        "delivery_status",
        "comments",
        "addition_type",
        "process_status",
    )
    list_filter = (
        "observation",
        "validation_status",
        "delivery_status",
        "addition_type",
    )

    # Retry functions
    readonly_fields = (
        "date_modified",
        "broid_registration",
        "start_date",
        "end_date",
        "validation_status",
        "delivery_id",
        "delivery_type",
        "delivery_status",
        "comments",
        "last_changed",
        "corrections_applied",
        "file",
        "addition_type",
        "process_status",
    )

    autocomplete_fields = ("observation",)

    actions = [
        "regenerate_sourcedocuments",
        "validate_sourcedocuments",
        "deliver_sourcedocuments",
        "check_status_delivery",
    ]
    # Regenerate addition sourcedocuments

    # Check the current status before it is allowed
    @admin.action(description="Regenerate sourcedocuments")
    def regenerate_sourcedocuments(self, request, queryset):
        gld = GldSyncHandler()
        for addition_log in queryset:
            groundwaterleveldossier = GroundwaterLevelDossier.objects.get(
                gld_bro_id=addition_log.broid_registration
            )
            well = groundwaterleveldossier.groundwater_monitoring_tube.groundwater_monitoring_well_static
            gld._set_bro_info(well)
            if addition_log.delivery_id is not None:
                self.message_user(
                    request,
                    "Can't create new sourcedocuments for an observation that has already been delivered",
                    messages.ERROR,
                )
            else:
                observation_id = addition_log.observation_id
                observation = models.Observation.objects.get(
                    observation_id=observation_id
                )
                (
                    observation_source_document_data,
                    addition_type,
                ) = get_observation_gld_source_document_data(observation)
                gld.generate_gld_addition_sourcedoc_data(
                    observation,
                    observation_source_document_data,
                    addition_type,
                )

                self.message_user(
                    request,
                    "Succesfully attempted sourcedocument regeneration",
                    messages.INFO,
                )

    # Retry validate sourcedocuments (only if file is present)
    @admin.action(description="Validate sourcedocuments")
    def validate_sourcedocuments(self, request, queryset):
        gld = GldSyncHandler()
        for addition_log in queryset:
            groundwaterleveldossier = GroundwaterLevelDossier.objects.get(
                gld_bro_id=addition_log.broid_registration
            )
            well = groundwaterleveldossier.groundwater_monitoring_tube.groundwater_monitoring_well_static
            gld._set_bro_info(well)

            additions_dir = gld_SETTINGS["additions_dir"]

            filename = addition_log.file
            addition_file_path = os.path.join(additions_dir, filename)
            if addition_log.delivery_id is not None:
                self.message_user(
                    request,
                    "Can't revalidate document for an observation that has already been delivered",
                    messages.ERROR,
                )
            elif not os.path.exists(addition_file_path):
                self.message_user(
                    request,
                    "Source document file does not exists in the file system",
                    messages.ERROR,
                )
                # Validate the sourcedocument for this observation
            else:
                gld.validate_gld_addition_source_document(addition_log, filename)
                self.message_user(
                    request, "Succesfully attemped document validation", messages.INFO
                )

    # Retry deliver sourcedocuments
    @admin.action(description="Deliver sourcedocuments")
    def deliver_sourcedocuments(self, request, queryset):
        gld = GldSyncHandler()
        for addition_log in queryset:
            groundwaterleveldossier = GroundwaterLevelDossier.objects.get(
                gld_bro_id=addition_log.broid_registration
            )
            well = groundwaterleveldossier.groundwater_monitoring_tube.groundwater_monitoring_well_static
            gld._set_bro_info(well)

            filename = addition_log.file

            if addition_log.validation_status is None:
                self.message_user(
                    request,
                    "Can't deliver an invalid document or not yet validated document",
                    messages.ERROR,
                )
            elif addition_log.delivery_status in ["AANGELEVERD", "OPGENOM EN_LVBRO"]:
                self.message_user(
                    request,
                    "Can't deliver a document that has been already been delivered",
                    messages.ERROR,
                )
            else:
                gld.deliver_gld_addition_source_document(addition_log, filename)
                self.message_user(
                    request, "Succesfully attemped document delivery", messages.INFO
                )

    # Check status of a delivery
    @admin.action(description="Check status delivery")
    def check_status_delivery(self, request, queryset):
        gld = GldSyncHandler()
        for addition_log in queryset:
            groundwaterleveldossier = GroundwaterLevelDossier.objects.get(
                gld_bro_id=addition_log.broid_registration
            )
            well = groundwaterleveldossier.groundwater_monitoring_tube.groundwater_monitoring_well_static
            gld._set_bro_info(well)

            if addition_log.delivery_id is None:
                self.message_user(
                    request,
                    "Can't check status of a delivery with no 'delivery_id'",
                    messages.ERROR,
                )
            else:
                gld.check_status_gld_addition(addition_log)
                self.message_user(
                    request, "Succesfully attemped status check", messages.INFO
                )


_register(models.GroundwaterLevelDossier, GroundwaterLevelDossierAdmin)
_register(models.MeasurementPointMetadata, MeasurementPointMetadataAdmin)
_register(models.MeasurementTvp, MeasurementTvpAdmin)
_register(models.ObservationMetadata, ObservationMetadataAdmin)
_register(models.ObservationProcess, ObservationProcessAdmin)
_register(models.Observation, ObservationAdmin)
_register(models.gld_registration_log, gld_registration_logAdmin)
_register(models.gld_addition_log, gld_addition_log_Admin)

patch_admin(models.GroundwaterLevelDossier)
patch_admin(models.MeasurementPointMetadata)
patch_admin(models.MeasurementTvp)
patch_admin(models.ObservationMetadata)
patch_admin(models.ObservationProcess)
patch_admin(models.Observation)
patch_admin(models.gld_registration_log)
patch_admin(models.gld_addition_log)

admin.site.site_header = "BRO connector"
admin.site.site_title = "Dashboard"
admin.site.index_title = "BRO connector"

# %%
