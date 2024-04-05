from django.contrib import admin
from django.contrib import messages
import os
from . import models
from main.settings.base import gld_SETTINGS
from main.management.tasks import gld_actions
from reversion_compare.helpers import patch_admin
import reversion
from main.management.commands.gld_sync_to_bro import GldSyncHandler, get_observation_gld_source_document_data


def _register(model, admin_class):
    admin.site.register(model, admin_class)


# %% GLD model registration

gld = GldSyncHandler(gld_SETTINGS)

class GroundwaterLevelDossierAdmin(admin.ModelAdmin):
    list_display = (
        "groundwater_level_dossier_id",
        "groundwater_monitoring_tube",
        "research_start_date",
        "research_last_date",
        "gld_bro_id",
    )
    list_filter = (
        "groundwater_level_dossier_id",
        "groundwater_monitoring_tube",
        "research_start_date",
        "research_last_date",
    )

    readonly_fields = ["gld_bro_id", "gmw_bro_id", "tube_number"]

    actions = ["deliver_to_bro", "check_status"]

    def deliver_to_bro(self, request, queryset):
        for dossier in queryset:
            gld_actions.check_and_deliver(dossier)

    def check_status(self, request, queryset):
        for dossier in queryset:
            gld_actions.check_status(dossier)

    deliver_to_bro.short_description = "Deliver GLD to BRO"
    check_status.short_description = "Check GLD status from BRO"


class MeasurementPointMetadataAdmin(admin.ModelAdmin):
    list_display = (
        "measurement_point_metadata_id",
        "status_quality_control",
        "censor_reason",
        "censor_reason_artesia",
        "value_limit",
    )

    list_filter = (
        "measurement_point_metadata_id",
        "status_quality_control",
        "censor_reason",
    )


class MeasurementTvpAdmin(admin.ModelAdmin):
    list_display = (
        "measurement_tvp_id",
        "observation",
        "measurement_time",
        "field_value",
    )

    list_filter = ("observation",)

    readonly_fields = ("measurement_point_metadata",)


class ObservationAdmin(admin.ModelAdmin):
    list_display = (
        "observation_id",
        "groundwater_level_dossier",
        "observation_starttime",
        "observation_endtime",
        "result_time",
        "observation_type",
        "status",
        "up_to_date_in_bro",
    )
    list_filter = (
        "observation_id",
        "observation_starttime",
        "observation_endtime",
        "groundwater_level_dossier",
        "result_time",
    )

    readonly_fields = ["status"]

    actions = ["change_up_to_date_status"]

    def observation_type(self, obj: models.Observation):
        return obj.observation_metadata.observation_type

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
        "date_stamp",
        "observation_type",
        "status",
        "responsible_party_id",
    )
    list_filter = (
        "date_stamp",
        "observation_metadata_id",
        "date_stamp",
        "observation_type",
        "status",
        "responsible_party_id",
    )


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


class ResponsiblePartyAdmin(admin.ModelAdmin):
    list_display = (
        "responsible_party_id",
        "identification",
        "organisation_name",
    )
    list_filter = (
        "responsible_party_id",
        "identification",
        "organisation_name",
    )


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
        for registration_log in queryset:
            tube = models.GroundwaterMonitoringTubeStatic.objects.get(
                groundwater_monitoring_well_static__bro_id=registration_log.gwm_bro_id
            )
            well = tube.groundwater_monitoring_well_static

            gld = GldSyncHandler(gld_SETTINGS)

            if registration_log.levering_id is not None:
                self.message_user(
                    request,
                    "Can't generate startregistration sourcedocuments for an existing registration",
                    messages.ERROR,
                )
            else:
                startregistration = gld.create_start_registration_sourcedocs(
                    well,
                    tube.tube_number
                )
                self.message_user(
                    request,
                    "Attempted startregistration sourcedocument regeneration",
                    messages.INFO,
                )

    @admin.action(description="Validate startregistration sourcedocument")
    def validate_startregistration_sourcedocument(self, request, queryset):
        gld = GldSyncHandler(gld_SETTINGS)

        for registration_log in queryset:
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
            elif registration_log.levering_id is not None:
                self.message_user(
                    request,
                    "Can't validate a document that has already been delivered",
                    messages.ERROR,
                )
            else:
                validation_status = gld.validate_gld_startregistration_request(
                    registration_log.id,
                )
                self.message_user(
                    request,
                    "Succesfully validated startregistration sourcedocument",
                    messages.INFO,
                )

    @admin.action(description="Deliver startregistration sourcedocument")
    def deliver_startregistration_sourcedocument(self, request, queryset):
        for registration_log in queryset:
            if registration_log.levering_id is not None:
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
            elif registration_log.levering_status is not None:
                self.message_user(
                    request,
                    "Can't deliver a document that has been already been delivered",
                    messages.ERROR,
                )
            else:
                delivery_status = gld.deliver_startregistration_sourcedocuments(
                    registration_log.id
                )

                self.message_user(
                    request,
                    "Attempted registration sourcedocument delivery",
                    messages.INFO,
                )

    @admin.action(description="Check status of startregistration")
    def check_status_startregistration(self, request, queryset):
        gld = GldSyncHandler(gld_SETTINGS)

        for registration_log in queryset:
            levering_id = registration_log.levering_id
            if levering_id is None:
                self.message_user(
                    request,
                    "Can't check status of a delivery with no 'levering_id'",
                    messages.ERROR,
                )
            else:
                status = gld.check_delivery_status_levering(registration_log.id)
                self.message_user(
                    request, "Attempted registration status check", messages.INFO
                )

    list_display = (
        "date_modified",
        "gld_bro_id",
        "gwm_bro_id",
        "filter_id",
        "quality_regime",
        "validation_status",
        "levering_id",
        "levering_status",
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
        "levering_status",
    )


class gld_addition_log_Admin(admin.ModelAdmin):
    # Retry functions
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
        for addition_log in queryset:
            if addition_log.levering_id is not None:
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
        demo = gld_SETTINGS["demo"]
        if demo:
            acces_token_bro_portal = gld_SETTINGS["acces_token_bro_portal_demo"]
        else:
            acces_token_bro_portal = gld_SETTINGS[
                "acces_token_bro_portal_bro_connector"
            ]

        gld = GldSyncHandler(gld_SETTINGS)

        for addition_log in queryset:
            observation_id = addition_log.observation_id
            observation = models.Observation.objects.get(observation_id=observation_id)
            additions_dir = gld_SETTINGS["additions_dir"]

            filename = addition_log.file
            addition_file_path = os.path.join(additions_dir, filename)
            if addition_log.levering_id is not None:
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
                validation_status = gld.validate_gld_addition_source_document(
                    observation_id, filename
                )
                self.message_user(
                    request, "Succesfully attemped document validation", messages.INFO
                )

    # Retry deliver sourcedocuments
    @admin.action(description="Deliver sourcedocuments")
    def deliver_sourcedocuments(self, request, queryset):
        demo = gld_SETTINGS["demo"]
        if demo:
            acces_token_bro_portal = gld_SETTINGS["acces_token_bro_portal_demo"]
        else:
            acces_token_bro_portal = gld_SETTINGS[
                "acces_token_bro_portal_bro_connector"
            ]

        for addition_log in queryset:
            observation_id = addition_log.observation_id
            filename = addition_log.file

            if (
                addition_log.validation_status == "NIET_VALIDE"
                or addition_log.validation_status is None
            ):
                self.message_user(
                    request,
                    "Can't deliver an invalid document or not yet validated document",
                    messages.ERROR,
                )
            elif addition_log.levering_status is not None:
                self.message_user(
                    request,
                    "Can't deliver a document that has been already been delivered",
                    messages.ERROR,
                )
            else:
                delivery_status = gld.deliver_gld_addition_source_document(
                    observation_id, filename
                )
                self.message_user(
                    request, "Succesfully attemped document delivery", messages.INFO
                )

    # Check status of a delivery
    @admin.action(description="Check status delivery")
    def check_status_delivery(self, request, queryset):
        demo = gld_SETTINGS["demo"]
        if demo:
            acces_token_bro_portal = gld_SETTINGS["acces_token_bro_portal_demo"]
        else:
            acces_token_bro_portal = gld_SETTINGS[
                "acces_token_bro_portal_bro_connector"
            ]

        for addition_log in queryset:
            if addition_log.levering_id is None:
                self.message_user(
                    request,
                    "Can't check status of a delivery with no 'levering_id'",
                    messages.ERROR,
                )
            else:
                gld.check_status_gld_addition(
                    addition_log
                )
                self.message_user(
                    request, "Succesfully attemped status check", messages.INFO
                )

    # Custom delete method

    list_display = (
        "date_modified",
        "observation_id",
        "start_date",
        "end_date",
        "broid_registration",
        "validation_status",
        "levering_id",
        "levering_status",
        "addition_type",
        "comments",
        "file",
    )
    list_filter = (
        "validation_status",
        "levering_status",
    )


_register(models.GroundwaterLevelDossier, GroundwaterLevelDossierAdmin)
_register(models.MeasurementPointMetadata, MeasurementPointMetadataAdmin)
_register(models.MeasurementTvp, MeasurementTvpAdmin)
_register(models.ObservationMetadata, ObservationMetadataAdmin)
_register(models.ObservationProcess, ObservationProcessAdmin)
_register(models.ResponsibleParty, ResponsiblePartyAdmin)
_register(models.Observation, ObservationAdmin)
_register(models.gld_registration_log, gld_registration_logAdmin)
_register(models.gld_addition_log, gld_addition_log_Admin)

patch_admin(models.GroundwaterLevelDossier)
patch_admin(models.MeasurementPointMetadata)
patch_admin(models.MeasurementTvp)
patch_admin(models.ObservationMetadata)
patch_admin(models.ObservationProcess)
patch_admin(models.ResponsibleParty)
patch_admin(models.Observation)
patch_admin(models.gld_registration_log)
patch_admin(models.gld_addition_log)

admin.site.site_header = "BRO connector"
admin.site.site_title = "Dashboard"
admin.site.index_title = "BRO connector"

# %%
