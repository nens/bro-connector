import csv
import datetime
import os
from collections import Counter

import reversion
from django.contrib import admin, messages
from django.db.models import fields
from django.http import HttpResponse
from gld.management.commands.gld_sync_to_bro import (
    GldSyncHandler,
)
from gld.management.tasks import gld_actions
from gld.models import GroundwaterLevelDossier
from gmw.models import GroundwaterMonitoringWellStatic
from main.settings.base import gld_SETTINGS
from reversion_compare.helpers import patch_admin

from . import models
from .custom_filters import (
    CompletelyDeliveredFilter,
    GLDFilter,
    HasOpenObservationFilter,
    ObservationFilter,
    OrganisationFilter,
    TubeFilter,
)


def Export_selected_items_to_csv(self, request, queryset):
    meta = self.model._meta
    field_names = [field.name for field in meta.fields]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={meta}.csv"
    writer = csv.writer(response)

    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in field_names])

    return response


admin.site.add_action(Export_selected_items_to_csv)


def _register(model, admin_class):
    admin.site.register(model, admin_class)


def get_searchable_fields(model_class):
    return [
        f.name
        for f in model_class._meta.fields
        if isinstance(f, fields.CharField | fields.AutoField)
    ]


def send_pending_messages(self, request, message_counter):
    for (msg_text, msg_level), count in message_counter.items():
        if count > 1:
            self.message_user(
                request,
                f"{msg_text} (Occurred {count} times)",
                msg_level,
            )
        else:
            self.message_user(
                request,
                msg_text,
                msg_level,
            )


# %% GLD model registration

gld = GldSyncHandler()


class ObservationInline(admin.TabularInline):
    model = models.Observation
    show_change_link = True
    search_fields = get_searchable_fields(models.Observation)
    fields = (
        "observation_type",
        "all_measurements_validated",
        "nr_measurements",
        "up_to_date_in_bro",
        "observation_starttime",
        "observation_endtime",
        "result_time",
        "observation_id_bro",
    )

    readonly_fields = [
        "observation_type",
        "all_measurements_validated",
        "nr_measurements",
        "up_to_date_in_bro",
        "observation_id_bro",
        "observation_starttime",
        "observation_endtime",
        "result_time",
    ]

    ordering = ["-observation_starttime"]
    extra = 0
    max_num = 0


class MeasurementTvpInline(admin.TabularInline):
    model = models.MeasurementTvp
    show_change_link = True
    search_fields = get_searchable_fields(models.MeasurementTvp)
    fields = (
        "measurement_time",
        "field_value",
        "field_value_unit",
        "comment",
    )

    readonly_fields = [
        "measurement_time",
        "field_value",
        "field_value_unit",
        "comment",
    ]

    ordering = ["-measurement_time"]
    extra = 0
    max_num = 0


class GroundwaterLevelDossierAdmin(admin.ModelAdmin):
    list_display = (
        "groundwater_monitoring_tube",
        "research_start_date",
        "research_last_date",
        "gld_bro_id",
        "quality_regime",
        "has_open_observation",
        "completely_delivered",
        # "first_measurement",
        # "last_measurement",
        "nr_measurements",
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

    readonly_fields = [
        "gld_bro_id",
        "gmw_bro_id",
        "tube_number",
        "first_measurement",
        "last_measurement",
        "nr_measurements",
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

    deliver_to_bro.short_description = "Lever GLD aan naar BRO"
    check_status.short_description = "Check GLD status in BRO"


class MeasurementPointMetadataAdmin(admin.ModelAdmin):
    list_max_show_all = 1000  # Prevents loading all records

    search_fields = ["measurement_point_metadata_id", "censor_reason_datalens"]
    list_display = ("__str__",)

    list_filter = (
        "status_quality_control",
        "censor_reason",
    )


class MeasurementTvpAdmin(admin.ModelAdmin):
    list_max_show_all = 10  # Prevents loading all records

    list_display = ("__str__",)
    ordering = ("-measurement_time",)
    autocomplete_fields = (
        "measurement_point_metadata",
        "observation",
    )
    list_filter = (ObservationFilter,)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.only("measurement_time", "observation")


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
        "nr_measurements",
        "up_to_date_in_bro",
        "observation_id_bro",
    )
    list_filter = (
        GLDFilter,
        OrganisationFilter,
        "observation_starttime",
        "observation_endtime",
        "result_time",
        "up_to_date_in_bro",
        "observation_id_bro",
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
        "nr_measurements",
        "timestamp_first_measurement",
        "timestamp_last_measurement",
        "observation_id_bro",
    ]

    inlines = (MeasurementTvpInline,)

    actions = ["close_observation", "change_up_to_date_status"]

    ordering = ["-observation_starttime"]
    # extra = 0
    # max_num = 0

    def observation_type(self, obj: models.Observation):
        if obj.observation_metadata is not None:
            if obj.observation_metadata.observation_type is not None:
                return obj.observation_metadata.observation_type
        return "-"

    @admin.action(description="Sluit Observatie")
    def close_observation(self, request, queryset):
        for item in queryset.filter(observation_endtime__isnull=True):
            with reversion.create_revision():
                item.observation_endtime = (
                    datetime.datetime.now().astimezone() - datetime.timedelta(seconds=1)
                )
                item.result_time = item.timestamp_last_measurement
                item.save(update_fields=["observation_endtime", "result_time"])
                reversion.set_comment("Closed the observation with a manual action.")

    @admin.action(description="Verander up-to-date status.")
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
    # Retry generate startregistration
    actions = [
        "regenerate_start_registration_sourcedocument",
        "validate_startregistration_sourcedocument",
        "deliver_startregistration_sourcedocument",
        "check_status_startregistration",
    ]

    @admin.action(description="Genereer startregistratie brondocument")
    def regenerate_start_registration_sourcedocument(self, request, queryset):
        gld = GldSyncHandler()
        # Collect messages to deduplicate later
        pending_messages = []

        for registration_log in queryset:
            well = GroundwaterMonitoringWellStatic.objects.get(
                bro_id=registration_log.gmw_bro_id
            )
            gld._set_bro_info(well)

            if registration_log.delivery_id is not None:
                pending_messages.append(
                    (
                        "Can't generate startregistration sourcedocuments for an existing registration",
                        messages.ERROR,
                    )
                )
            else:
                gld.create_start_registration_sourcedocs(
                    well, registration_log.filter_number
                )
                pending_messages.append(
                    (
                        "Attempted startregistration sourcedocument regeneration",
                        messages.INFO,
                    )
                )

        # Deduplicate and emit messages
        message_counter = Counter(pending_messages)
        send_pending_messages(self, request, message_counter)

    @admin.action(description="Valideer startregistratie brondocument")
    def validate_startregistration_sourcedocument(self, request, queryset):
        gld = GldSyncHandler()
        pending_messages = []
        for registration_log in queryset:
            well = GroundwaterMonitoringWellStatic.objects.get(
                bro_id=registration_log.gmw_bro_id,
            )
            gld._set_bro_info(well)

            sourcedoc_file = os.path.join(
                gld_SETTINGS["startregistrations_dir"], registration_log.file
            )

            if registration_log.process_status == "failed_to_generate_source_documents":
                pending_messages.append(
                    (
                        "Can't validate a startregistration that failed to generate",
                        messages.ERROR,
                    )
                )
            elif registration_log.file is None or not os.path.exists(sourcedoc_file):
                pending_messages.append(
                    (
                        "There is no sourcedocument file for this startregistration",
                        messages.ERROR,
                    )
                )
            elif registration_log.delivery_id is not None:
                pending_messages.append(
                    (
                        "Can't validate a document that has already been delivered",
                        messages.ERROR,
                    )
                )
            else:
                gld.validate_gld_startregistration_request(
                    registration_log,
                )
                pending_messages.append(
                    (
                        "Succesfully validated startregistration sourcedocument",
                        messages.INFO,
                    )
                )

        # Deduplicate and display
        message_counter = Counter(pending_messages)
        send_pending_messages(self, request, message_counter)

    @admin.action(description="Lever startregistratie brondocument")
    def deliver_startregistration_sourcedocument(self, request, queryset):
        pending_messages = []
        for registration_log in queryset:
            well = GroundwaterMonitoringWellStatic.objects.get(
                bro_id=registration_log.gmw_bro_id
            )
            gld._set_bro_info(well)

            if registration_log.delivery_id is not None:
                pending_messages.append(
                    (
                        "Can't deliver a registration that has already been delivered",
                        messages.ERROR,
                    )
                )
            elif registration_log.validation_status == "NIET_VALIDE":
                pending_messages.append(
                    (
                        "Can't deliver an invalid document or not yet validated document",
                        messages.ERROR,
                    )
                )
            elif registration_log.delivery_status in [
                "AANGELEVERD",
                "OPGENOM EN_LVBRO",
            ]:
                pending_messages.append(
                    (
                        "Can't deliver a document that has been already been delivered",
                        messages.ERROR,
                    )
                )
            else:
                gld.deliver_startregistration_sourcedocuments(registration_log)
                pending_messages.append(
                    (
                        "Attempted registration sourcedocument delivery",
                        messages.INFO,
                    )
                )

        # Deduplicate and display
        message_counter = Counter(pending_messages)
        send_pending_messages(self, request, message_counter)

    @admin.action(description="Check status startregistratie")
    def check_status_startregistration(self, request, queryset):
        gld = GldSyncHandler()
        pending_messages = []
        for registration_log in queryset:
            well = GroundwaterMonitoringWellStatic.objects.get(
                bro_id=registration_log.gmw_bro_id
            )
            gld._set_bro_info(well)
            delivery_id = registration_log.delivery_id
            if delivery_id is None:
                pending_messages.append(
                    (
                        "Can't check status of a delivery with no 'delivery_id'",
                        messages.ERROR,
                    )
                )
            else:
                gld.check_delivery_status_levering(registration_log)
                pending_messages.append(
                    ("Attempted registration status check", messages.INFO)
                )

        # Deduplicate and display
        message_counter = Counter(pending_messages)
        send_pending_messages(self, request, message_counter)


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
    @admin.action(description="Genereer brondocumenten")
    def regenerate_sourcedocuments(
        self, request, queryset: list[models.gld_addition_log]
    ):
        gld = GldSyncHandler()
        # Temp list to collect messages
        pending_messages = []

        for addition_log in queryset:
            groundwaterleveldossier = GroundwaterLevelDossier.objects.get(
                gld_bro_id=addition_log.broid_registration
            )
            well = groundwaterleveldossier.groundwater_monitoring_tube.groundwater_monitoring_well_static
            gld._set_bro_info(well)

            if addition_log.delivery_id is not None:
                pending_messages.append(
                    (
                        "Can't create new sourcedocuments for an observation that has already been delivered",
                        messages.ERROR,
                    )
                )
            else:
                observation_id = addition_log.observation_id
                observation = models.Observation.objects.get(
                    observation_id=observation_id
                )
                gld.generate_gld_addition_sourcedoc_data(observation)

                pending_messages.append(
                    (
                        "Succesfully attempted sourcedocument regeneration",
                        messages.INFO,
                    )
                )

        # Deduplicate and display
        message_counter = Counter(pending_messages)
        send_pending_messages(self, request, message_counter)

    # Retry validate sourcedocuments (only if file is present)
    @admin.action(description="Valideer brondocumenten")
    def validate_sourcedocuments(
        self, request, queryset: list[models.gld_addition_log]
    ):
        gld = GldSyncHandler()
        pending_messages = []
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
                pending_messages.append(
                    (
                        "Can't revalidate document for an observation that has already been delivered",
                        messages.ERROR,
                    )
                )
            elif not os.path.exists(addition_file_path):
                pending_messages.append(
                    (
                        "Source document file does not exists in the file system",
                        messages.ERROR,
                    )
                )
                # Validate the sourcedocument for this observation
            else:
                gld.validate_gld_addition_source_document(addition_log)
                pending_messages.append(
                    ("Succesfully attemped document validation", messages.INFO)
                )

        # Deduplicate and display
        message_counter = Counter(pending_messages)
        send_pending_messages(self, request, message_counter)

    # Retry deliver sourcedocuments
    @admin.action(description="Lever brondocumenten aan BRO")
    def deliver_sourcedocuments(self, request, queryset: list[models.gld_addition_log]):
        gld = GldSyncHandler()
        pending_messages = []
        for addition_log in queryset:
            groundwaterleveldossier = GroundwaterLevelDossier.objects.get(
                gld_bro_id=addition_log.broid_registration
            )
            well = groundwaterleveldossier.groundwater_monitoring_tube.groundwater_monitoring_well_static
            gld._set_bro_info(well)

            if addition_log.validation_status is None:
                pending_messages.append(
                    (
                        "Can't deliver an invalid document or not yet validated document",
                        messages.ERROR,
                    )
                )
            elif addition_log.delivery_status in ["AANGELEVERD", "OPGENOM EN_LVBRO"]:
                pending_messages.append(
                    (
                        "Can't deliver a document that has been already been delivered",
                        messages.ERROR,
                    )
                )
            else:
                gld.deliver_gld_addition_source_document(addition_log)
                pending_messages.append(
                    ("Succesfully attemped document delivery", messages.INFO)
                )

        # Deduplicate and display
        message_counter = Counter(pending_messages)
        send_pending_messages(self, request, message_counter)

    # Check status of a delivery
    @admin.action(description="Check status levering")
    def check_status_delivery(self, request, queryset: list[models.gld_addition_log]):
        gld = GldSyncHandler()
        pending_messages = []
        for addition_log in queryset:
            groundwaterleveldossier = GroundwaterLevelDossier.objects.get(
                gld_bro_id=addition_log.broid_registration
            )
            well = groundwaterleveldossier.groundwater_monitoring_tube.groundwater_monitoring_well_static
            gld._set_bro_info(well)

            if addition_log.delivery_id is None or addition_log.observation is None:
                pending_messages.append(
                    (
                        "Can't check status of a delivery with no 'delivery_id'",
                        messages.ERROR,
                    )
                )
            else:
                gld.check_status_gld_addition(addition_log)
                pending_messages.append(
                    ("Succesfully attemped status check", messages.INFO)
                )

        # Deduplicate and display
        message_counter = Counter(pending_messages)
        send_pending_messages(self, request, message_counter)


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
