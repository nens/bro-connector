from django.contrib import admin
from django.contrib import messages
from django.db.models import fields
import os
from . import models
from main.settings.base import gld_SETTINGS
from gld.management.tasks import gld_actions
from reversion_compare.helpers import patch_admin
import reversion
from gld.management.commands.gld_sync_to_bro import (
    GldSyncHandler,
)
from .custom_filters import (
    HasOpenObservationFilter,
    CompletelyDeliveredFilter,
    TubeFilter,
    GLDFilter,
    OrganisationFilter,
    ObservationFilter,
)
from ..main.constants import *

import datetime
from gmw.models import GroundwaterMonitoringWellStatic
from gld.models import GroundwaterLevelDossier


def _register(model, admin_class):
    admin.site.register(model, admin_class)


def get_searchable_fields(model_class):
    return [
        f.name
        for f in model_class._meta.fields
        if isinstance(f, (fields.CharField, fields.AutoField))
    ]


# %% GLD model registration

gld = GldSyncHandler()


class ObservationInline(admin.TabularInline):
    model = models.Observation
    show_change_link = True
    search_fields = get_searchable_fields(models.Observation)
    fields = (
        "observation_type",
        "all_measurements_validated",
        "up_to_date_in_bro",
        "observation_id_bro",
        "observation_starttime",
        "observation_endtime",
        "result_time",
    )

    readonly_fields = [
        "observation_type",
        "all_measurements_validated",
        "up_to_date_in_bro",
        "observation_id_bro",
        "observation_starttime",
        "observation_endtime",
        "result_time",
    ]

    ordering = ["observation_starttime"]
    extra = 0
    max_num = 0


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

    inlines = (ObservationInline,)

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
        gld_actions.create_registrations_folder()

        # First create all registration logs and deliver them to the BRO
        for dossier in queryset:
            gld_actions.check_and_deliver_start(dossier)

        # Then check the status of each individual registration log
        for dossier in queryset.exclude(gld_bro_id__isnull=False):
            start_log = models.gld_registration_log.objects.get(
                gmw_bro_id=dossier.gmw_bro_id,
                gld_bro_id=dossier.gld_bro_id,
                filter_number=dossier.tube_number,
                quality_regime=dossier.quality_regime
                if dossier.quality_regime
                else dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static.quality_regime,
            )
            start_log.check_delivery_status()

        for dossier in queryset:
            gld_actions.check_and_deliver_additions(dossier)

        # Then check the status of each individual registration log
        for dossier in queryset:
            for observation in dossier.observation.filter(up_to_date_in_bro=False):
                obs = models.Observation.objects.get(
                    observation_id=observation.observation_id
                )
                addition_log = models.gld_addition_log.objects.filter(
                    observation=obs, addition_type=obs.addition_type
                ).first()
                if addition_log:
                    addition_log.check_delivery_status()

    def check_status(self, request, queryset):
        for dossier in queryset:
            gld_actions.check_status(dossier)

    deliver_to_bro.short_description = "Deliver GLD to BRO"
    check_status.short_description = "Check GLD status from BRO"


class MeasurementPointMetadataAdmin(admin.ModelAdmin):
    list_max_show_all = 1000  # Prevents loading all records

    search_fields = ["measurement_point_metadata_id", "censor_reason_datalens"]
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
        "all_measurements_validated",
        "up_to_date_in_bro",
    )
    list_filter = (
        GLDFilter,
        OrganisationFilter,
        "observation_starttime",
        "observation_endtime",
        "result_time",
        "up_to_date_in_bro",
    )

    search_fields = [
        "groundwater_level_dossier__groundwater_monitoring_tube__groundwater_monitoring_well_static__groundwater_monitoring_well_static_id",
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
        "all_measurements_validated",
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

    @admin.action(description=RegistrationLog.Action.REGENERATE)
    def regenerate_start_registration_sourcedocument(self, request, queryset: list[models.gld_registration_log]):
        for registration_log in queryset:
            if (
                registration_log.validation_status == RegistrationLog.ValidationStatus.VALID or
                registration_log.delivery_status in [RegistrationLog.DeliveryStatus.DELIVERED, RegistrationLog.DeliveryStatus.ADDED]
            ):
                self.message_user(
                    request,
                    RegistrationLog.Message.GENERATE_ERROR,
                    messages.ERROR,
                )
            else:
                registration_log.generate_sourcedocument()
                print("delivery id after generating: ",registration_log.delivery_id)
                self.message_user(
                    request,
                    RegistrationLog.Message.GENERATE_SUCCESS,
                    messages.INFO,
                )

    @admin.action(description=RegistrationLog.Action.VALIDATE)
    def validate_startregistration_sourcedocument(self, request, queryset: list[models.gld_registration_log]):
        for registration_log in queryset:
            if registration_log.process_status == RegistrationLog.ProcessStatus.GENERATE_FAIL:
                self.message_user(
                    request,
                    RegistrationLog.Message.VALIDATE_ERROR_GENERATE,
                    messages.ERROR,
                )
            elif (
                registration_log.delivery_id is not None or 
                registration_log.delivery_status in [RegistrationLog.DeliveryStatus.DELIVERED, RegistrationLog.DeliveryStatus.ADDED]
            ):
                self.message_user(
                    request,
                    RegistrationLog.Message.VALIDATE_ERROR_VALIDATE,
                    messages.ERROR,
                )
            else:
                registration_log.validate_sourcedocument()
                self.message_user(
                    request,
                    RegistrationLog.Message.VALIDATE_SUCCESS,
                    messages.INFO,
                )

    @admin.action(description=RegistrationLog.Action.DELIVER)
    def deliver_startregistration_sourcedocument(self, request, queryset: list[models.gld_registration_log]):
        for registration_log in queryset:
            if registration_log.process_status == RegistrationLog.ProcessStatus.GENERATE_FAIL:
                self.message_user(
                    request,
                    RegistrationLog.Message.DELIVER_ERROR_GENERATE,
                    messages.ERROR,
                )
            if (
                registration_log.delivery_id is not None or 
                registration_log.delivery_status in [RegistrationLog.DeliveryStatus.DELIVERED, RegistrationLog.DeliveryStatus.ADDED]
            ):
                self.message_user(
                    request,
                    RegistrationLog.Message.DELIVER_ERROR_ALREADY_DELIVERED,
                    messages.ERROR,
                )
            elif registration_log.validation_status == RegistrationLog.ValidationStatus.INVALID:
                self.message_user(
                    request,
                    RegistrationLog.Message.DELIVER_ERROR_NOT_VALID,
                    messages.ERROR,
                )
            else:
                registration_log.deliver_sourcedocument()
                self.message_user(
                    request,
                    RegistrationLog.Message.DELIVER_SUCCESS,
                    messages.INFO,
                )

    @admin.action(description=RegistrationLog.Action.CHECK)
    def check_status_startregistration(self, request, queryset: list[models.gld_registration_log]):
        for registration_log in queryset:
            if registration_log.delivery_id is None:
                self.message_user(
                    request,
                    RegistrationLog.Message.CHECK_ERROR,
                    messages.ERROR,
                )
            else:
                registration_log.check_delivery_status()
                self.message_user(
                    request, RegistrationLog.Message.CHECK_SUCCESS, messages.INFO
                )

    list_display = (
        "date_modified",
        "gld_bro_id",
        "gmw_bro_id",
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
        "gmw_bro_id",
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
        "validation_status",
        "delivery_status",
    )

    # Retry functions
    readonly_fields = (
        "date_modified",
        "broid_registration",
        "observation_identifier",
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
    @admin.action(description=AdditionLog.Action.GENERATE)
    def regenerate_sourcedocuments(self, request, queryset: list[models.gld_addition_log]):
        for addition_log in queryset:
            if (
                addition_log.validation_status == AdditionLog.ValidationStatus.VALID or
                addition_log.delivery_status in [AdditionLog.DeliveryStatus.DELIVERED, AdditionLog.DeliveryStatus.APPROVED, AdditionLog.DeliveryStatus.VALIDATED]
            ):
                self.message_user(
                    request,
                    AdditionLog.Message.GENERATE_ERROR,
                    messages.ERROR,
                )
            else:
                addition_log.generate_sourcedocument()

                self.message_user(
                    request,
                    AdditionLog.Message.GENERATE_SUCCESS,
                    messages.INFO,
                )

    # Retry validate sourcedocuments (only if file is present)
    @admin.action(description=AdditionLog.Action.VALIDATE)
    def validate_sourcedocuments(self, request, queryset: list[models.gld_addition_log]):
        for addition_log in queryset:
            if addition_log.process_status == AdditionLog.ProcessStatus.GENERATE_FAIL:
                self.message_user(
                    request,
                    AdditionLog.Message.VALIDATE_ERROR_GENERATE,
                    messages.ERROR,
                )
            if (
                addition_log.delivery_id is not None or 
                addition_log.delivery_status in [AdditionLog.DeliveryStatus.DELIVERED, AdditionLog.DeliveryStatus.APPROVED, AdditionLog.DeliveryStatus.VALIDATED]
            ):
                self.message_user(
                    request,
                    AdditionLog.Message.VALIDATE_ERROR_VALIDATE,
                    messages.ERROR,
                )
                # Validate the sourcedocument for this observation
            else:
                addition_log.validate_sourcedocument()
                self.message_user(
                    request, AdditionLog.Message.VALIDATE_SUCCESS, messages.INFO
                )

    # Retry deliver sourcedocuments
    @admin.action(description=AdditionLog.Action.DELIVER)
    def deliver_sourcedocuments(self, request, queryset: list[models.gld_addition_log]):
        for addition_log in queryset:
            if addition_log.process_status == AdditionLog.ProcessStatus.GENERATE_FAIL:
                self.message_user(
                    request,
                    AdditionLog.Message.DELIVER_ERROR_GENERATE,
                    messages.ERROR,
                )
            elif (
                addition_log.delivery_id is not None or 
                addition_log.delivery_status in [AdditionLog.DeliveryStatus.DELIVERED, AdditionLog.DeliveryStatus.APPROVED, AdditionLog.DeliveryStatus.VALIDATED]
            ):
                self.message_user(
                    request,
                    AdditionLog.Message.DELIVER_ERROR_ALREADY_DELIVERED,
                    messages.ERROR,
                )
            elif addition_log.validation_status in [AdditionLog.ValidationStatus.INVALID, AdditionLog.ValidationStatus.PENDING]:
                self.message_user(
                    request,
                    AdditionLog.Message.DELIVER_ERROR_NOT_VALID,
                    messages.ERROR,
                )
            else:
                addition_log.deliver_sourcedocument()
                self.message_user(
                    request, AdditionLog.Message.DELIVER_SUCCESS, messages.INFO
                )

    # Check status of a delivery
    @admin.action(description=AdditionLog.Action.DELIVER)
    def check_status_delivery(self, request, queryset: list[models.gld_addition_log]):
        for addition_log in queryset:
            if addition_log.delivery_id is None:
                self.message_user(
                    request,
                    AdditionLog.Message.CHECK_ERROR,
                    messages.ERROR,
                )
            else:
                addition_log.check_delivery_status()
                self.message_user(
                    request, AdditionLog.Message.CHECK_SUCCESS, messages.INFO
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
