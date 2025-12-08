import datetime

import django.contrib.gis.db.models as geo_models
import main.utils.validators_models as validators_models
from bro.models import BROProject, Organisation
from django.db import models
from django.db.models import Manager
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from gmw.choices import (
    BOOLEAN_CHOICES,
    COLLISION_PROTECTION_TYPES,
    CONSTRUCTIONSTANDARD,
    CORRECTION_REASON_OPTIONS,
    DELIVERY_TYPE_CHOICES,
    DELIVERYCONTEXT,
    DEPTH_CHOICES,
    ELECTRODEPACKINGMATERIAL,
    ELECTRODESTATUS,
    EVENTNAME,
    FOUNDATIONS,
    GLUE,
    GROUNDLEVELPOSITIONINGMETHOD,
    HORIZONTALPOSITIONINGMETHOD,
    INITIALFUNCTION,
    KRW_CHOICES,
    LABELS,
    LOCALVERTICALREFERENCEPOINT,
    LOCKS,
    QUALITYREGIME,
    SALINITY_CHOICES,
    SOCKMATERIAL,
    TUBEMATERIAL,
    TUBEPACKINGMATERIAL,
    TUBESTATUS,
    TUBETOPPOSITIONINGMETHOD,
    TUBETYPE,
    VERTICALDATUM,
    WELLHEADPROTECTOR,
    WELLHEADPROTECTOR_SUBTYPES,
    WELLSTABILITY,
    WELLSTATUS,
)
from gmw.utils import generate_put_code
from main.models import BaseModel
from PIL import Image
from PIL.ExifTags import TAGS


def _get_token(owner: Organisation):
    return {
        "user": owner.bro_user,
        "pass": owner.bro_token,
    }


class GroundwaterMonitoringWellStatic(BaseModel):
    groundwater_monitoring_well_static_id = models.AutoField(
        primary_key=True, verbose_name="DB ID"
    )
    internal_id = models.CharField(
        max_length=50, verbose_name="Veldnaam", null=True, blank=True, unique=True
    )
    bro_id = models.CharField(
        max_length=15, blank=True, null=True, verbose_name="BRO ID", unique=True
    )
    project = models.ForeignKey(
        BROProject,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=1,
        verbose_name="Project",
    )
    delivery_accountable_party = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=1,
        related_name="delivery_accountable_party",
        verbose_name="Bronhouder",
    )
    delivery_responsible_party = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=1,
        related_name="delivery_responsible_party",
        verbose_name="Dataleverancier",
    )
    quality_regime = models.CharField(
        choices=QUALITYREGIME,
        default="IMBRO",
        max_length=256,
        blank=True,
        null=True,
        verbose_name="Kwaliteitsregime",
    )
    delivery_context = models.CharField(
        choices=DELIVERYCONTEXT,
        max_length=200,
        blank=True,
        null=True,
        default="OW",
        verbose_name="Kader aanlevering",
    )
    construction_standard = models.CharField(
        choices=CONSTRUCTIONSTANDARD,
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Bouw standaard",
    )
    initial_function = models.CharField(
        choices=INITIALFUNCTION,
        max_length=200,
        blank=True,
        null=True,
        default="stand",
        verbose_name="Initiële functie",
    )
    nitg_code = models.CharField(
        max_length=256, blank=True, null=True, verbose_name="NITG-code"
    )
    olga_code = models.CharField(
        max_length=256, blank=True, null=True, verbose_name="OLGA-code"
    )
    well_code = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        verbose_name="Putcode",
    )
    monitoring_pdok_id = models.IntegerField(blank=True, null=True)
    coordinates = geo_models.PointField(
        srid=28992, blank=True, null=True, editable=False, verbose_name="RD Coordinaten"
    )  # This field type is a guess.
    coordinates_4326 = geo_models.PointField(
        srid=4326,
        blank=True,
        null=True,
        editable=False,
        help_text="Passief veld. Vul deze niet in. Wordt automatisch berekend op basis van de RD coordinaten in het coordinates field.",
        verbose_name="Standaard coordinaten",
    )
    reference_system = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        verbose_name="Referentie stelsel",
        default="RD",
    )
    horizontal_positioning_method = models.CharField(
        choices=HORIZONTALPOSITIONINGMETHOD,
        max_length=200,
        blank=True,
        null=True,
        default="GPS200tot1000cm",
        verbose_name="Methode horizontale locatiebepaling",
    )
    local_vertical_reference_point = models.CharField(
        choices=LOCALVERTICALREFERENCEPOINT,
        default="NAP",
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Lokaal verticaal referentiepunt",
    )
    well_offset = models.FloatField(
        blank=True, null=True, verbose_name="Putverschuiving"
    )
    vertical_datum = models.CharField(
        choices=VERTICALDATUM,
        default="NAP",
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Verticaal referentievlak",
    )
    construction_date = models.DateField(
        blank=True, null=True, verbose_name="Inrichtingsdatum"
    )
    removal_date = models.DateField(
        blank=True, null=True, verbose_name="Verwijderingsdatum"
    )
    aquifer_layer = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name="Watervoerend pakket",
        help_text="Bijv. WVP1",
    )
    salinity = models.CharField(
        max_length=30,
        choices=SALINITY_CHOICES,
        blank=True,
        null=True,
        verbose_name="Zoutgehalte",
    )

    # Added for additional wells that are not owned by the user
    in_management = models.BooleanField(
        null=True, blank=True, default=True, editable=True, verbose_name="In beheer"
    )
    well_status = models.CharField(
        max_length=50,
        choices=WELLSTATUS,
        default="inGebruik",
        editable=True,
        verbose_name="Putstatus",
    )
    bro_actions = models.TextField(
        blank=True, null=True, verbose_name="Benodigde acties om BRO Compleet te maken"
    )
    # Added for GMW delivery
    deliver_gmw_to_bro = models.BooleanField(
        blank=True, default=False, verbose_name="Moet naar de BRO"
    )  # Should information of this well be delivered to the BRO
    complete_bro = models.BooleanField(
        blank=True, default=False, verbose_name="BRO Compleet"
    )  # Is the data in the table complete as required for the BRO

    # Customization fields
    last_horizontal_positioning_date = models.DateField(
        blank=True, null=True, verbose_name="Laatste horizontale positioneringsdatum"
    )
    construction_coordinates = geo_models.PointField(
        srid=28992, blank=True, null=True, editable=False
    )  # This field type is a guess.

    state: Manager["GroundwaterMonitoringWellDynamic"]
    tube: Manager["GroundwaterMonitoringTubeStatic"]
    picture: Manager["Picture"]
    event: Manager["Event"]
    maintenance: Manager["Maintenance"]
    delivery_accountable_party: Manager["Organisation"]

    @property
    def is_surface(self):
        return self.internal_id.lower().startswith("p")

    is_surface.fget.short_description = "Is oppervlakte put"

    @property
    def report(self):
        remarks = self.state.all().order_by("date_from")
        report = ""
        for remark in remarks:
            report += f"{remark.date_from.date()}: {remark.comment}\n\n"

        return report

    report.fget.short_description = "Rapport"

    @property
    def x(self):
        return self.coordinates.x

    @property
    def y(self):
        return self.coordinates.y

    @property
    def lat(self):
        return self.coordinates_4326.y

    @property
    def lon(self):
        return self.coordinates_4326.x

    @property
    def project_number(self):
        if self.project:
            return self.project.project_number
        else:
            None

    def get_bro_info(self):
        return {
            "token": _get_token(self.delivery_accountable_party),
            "projectnummer": self.project_number,
        }

    project_number.fget.short_description = "Projectnummer"

    def cx(self):
        return self.construction_coordinates.x

    def cy(self):
        return self.construction_coordinates.y

    @property
    def bro_loket_link(self):
        if self.bro_id:
            bro_loket = (
                f"https://www.broloket.nl/ondergrondgegevens?bro-id={self.bro_id}"
            )
            return format_html(f'<a href="{bro_loket}">{bro_loket}</a>')
        return "-"

    bro_loket_link.fget.short_description = "BROloket link:"

    @property
    def map_preview(self):
        """
        Render the map preview HTML snippet for this well.
        """
        if self.lat and self.lon:
            context = {
                "lat": self.lat,
                "lon": self.lon,
                "id": self.groundwater_monitoring_well_static_id,
            }
            html = render_to_string("partials/map_preview_iframe.html", context)
            return mark_safe(html)
        else:
            return mark_safe("""
                <div style="padding: 20px; text-align: center; color: #666; border: 1px dashed #ddd; border-radius: 4px;">
                    📍 Enter coordinates above to see the location on the map
                </div>
            """)

    map_preview.fget.short_description = "Preview locatie"

    @property
    def open_comments_well_ids(self):
        filter_ids = []
        wells_dynamic_unprocessed = GroundwaterMonitoringWellDynamic.objects.filter(
            groundwater_monitoring_well_static=self,
            comment_processed=False,
        ).all()
        if wells_dynamic_unprocessed:
            for well_dynamic in wells_dynamic_unprocessed:
                id = well_dynamic.groundwater_monitoring_well_dynamic_id
                filter_ids.append(id)

        return filter_ids

    open_comments_well_ids.fget.short_description = (
        "Dynamische put ids met openstaand commentaar"
    )

    @property
    def open_comments_tube_ids(self):
        tubes_static = GroundwaterMonitoringTubeStatic.objects.filter(
            groundwater_monitoring_well_static=self
        ).all()
        filter_ids = []
        for tube in tubes_static:
            tubes_dynamic_unprocessed = GroundwaterMonitoringTubeDynamic.objects.filter(
                groundwater_monitoring_tube_static=tube,
                comment_processed=False,
            ).all()
            if tubes_dynamic_unprocessed:
                for tube_dynamic in tubes_dynamic_unprocessed:
                    id = tube_dynamic.groundwater_monitoring_tube_dynamic_id
                    filter_ids.append(id)

        return filter_ids

    open_comments_tube_ids.fget.short_description = (
        "Dynamische filter ids met openstaand commentaar"
    )

    @property
    def has_open_comments(self):
        if self.open_comments_well_ids or self.open_comments_tube_ids:
            return True
        return False

    def __str__(self):
        if self.internal_id:
            return str(self.internal_id)
        elif self.well_code:
            return str(self.well_code)
        elif self.bro_id:
            return str(self.bro_id)
        else:
            return str(self.groundwater_monitoring_well_static_id)

    def save(self, *args, **kwargs):
        # Call the parent class's save method
        super().save(*args, **kwargs)
        if (
            self.removal_date is not None
            and self.event.filter(event_name="opruimen").count() == 0
        ):
            Event.objects.create(
                event_name="opruimen",
                groundwater_monitoring_well_static=self,
                event_date=self.removal_date,
            )

        if self.well_code is None and self.nitg_code is not None:
            print("Generate wellcode.")
            self.well_code = generate_put_code(self.nitg_code)
            super().save(update_fields=["well_code"])

        # If coordinates are available, convert and save them to coordinates_4236
        if self.coordinates:
            self.coordinates_4326 = self.coordinates.transform(4326, clone=True)
            # Save the updated instance
            super().save(update_fields=["coordinates_4326"])

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_well_static'
        verbose_name = "Grondwatermonitoring Put - Statisch"
        verbose_name_plural = "Grondwatermonitoring Putten - Statisch"


class GroundwaterMonitoringWellDynamic(BaseModel):
    groundwater_monitoring_well_dynamic_id = models.AutoField(
        primary_key=True, verbose_name="DB ID"
    )
    groundwater_monitoring_well_static = models.ForeignKey(
        GroundwaterMonitoringWellStatic,
        on_delete=models.CASCADE,
        related_name="state",
        verbose_name="Put",
    )
    date_from = models.DateTimeField(
        help_text="formaat: YYYY-MM-DD", verbose_name="Geldig vanaf"
    )
    ground_level_position = models.FloatField(
        blank=True,
        null=True,
        validators=[validators_models.maaiveldhoogte_validation],
        verbose_name="Maaiveld hoogte",
        help_text="m NAP",
    )
    ground_level_positioning_method = models.CharField(
        choices=GROUNDLEVELPOSITIONINGMETHOD,
        max_length=200,
        blank=True,
        null=True,
        default="RTKGPS20tot100cm",
        verbose_name="Methode positiebepaling maaiveld",
    )
    ground_level_stable = models.CharField(
        choices=BOOLEAN_CHOICES,
        max_length=254,
        null=True,
        blank=True,
        default="ja",
        verbose_name="Maaiveld stabiliteit",
    )
    well_stability = models.CharField(
        choices=WELLSTABILITY,
        max_length=200,
        blank=True,
        null=True,
        default="stabielNAP",  # Ik ga er vanuit dat dit niet standaard verankert is.
        verbose_name="Putstabiliteit",
    )
    owner = models.IntegerField(
        blank=True, null=True, verbose_name="Eigenaar", default=20168636
    )  # Should actually also be an organisation
    maintenance_responsible_party = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Onderhoud verantwoordelijke partij",
        default=20168636,
    )
    well_head_protector = models.CharField(
        choices=WELLHEADPROTECTOR,
        max_length=200,
        blank=True,
        null=True,
        default="kokerDeelsMetaal",
        verbose_name="Beschermconstructie",
    )
    # CUSTOMIZATION FIELDS
    well_head_protector_subtype = models.CharField(
        max_length=254,
        choices=WELLHEADPROTECTOR_SUBTYPES,
        null=True,
        blank=True,
        default="DN200",
        verbose_name="Beschermconstructie subtype",
    )
    foundation = models.CharField(
        max_length=254,
        choices=FOUNDATIONS,
        null=True,
        blank=True,
        default="geen",
        verbose_name="Fundering",
    )
    collision_protection = models.CharField(
        max_length=254,
        choices=COLLISION_PROTECTION_TYPES,
        null=True,
        blank=True,
        default="geen",
        verbose_name="Aanrijbescherming",
    )
    lock = models.CharField(
        max_length=254,
        choices=LOCKS,
        null=True,
        blank=True,
        verbose_name="Slot",
        default="sleutel",
    )
    key = models.CharField(
        max_length=254,
        blank=True,
        null=True,
        verbose_name="Sleutel",
        default="ABUS Titalium sleutel te vinden bij Provincie Zeeland Meetnetbeheerder",
    )
    place = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Plaats"
    )
    street = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Straat"
    )
    location_description = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Toegankelijkheid"
    )
    label = models.CharField(
        max_length=254,
        choices=LABELS,
        null=True,
        blank=True,
        verbose_name="Label",
        default="aluplaatje",
    )

    comment = models.TextField(blank=True, null=True, verbose_name="Commentaar")
    comment_processed = models.BooleanField(
        blank=True, default=True, verbose_name="Commentaar verwerkt"
    )
    bro_actions = models.TextField(
        blank=True, null=True, verbose_name="Benodigde acties om BRO Compleet te maken"
    )
    complete_bro = models.BooleanField(
        blank=True, default=False, verbose_name="BRO Compleet"
    )  # Is the data in the table complete as required for the BRO

    def save(self, *args, **kwargs):
        if self.comment in [None, ""]:
            self.comment_processed = True
        super().save(*args, **kwargs)

    def __str__(self):
        if self.date_till:
            till = self.date_till.date()
            return f"{self.groundwater_monitoring_well_static.__str__()} ({self.date_from.date()} - {till})"
        return f"{self.groundwater_monitoring_well_static.__str__()} ({self.date_from.date()} - Present)"

    @property
    def date_till(self):
        next_dynamic = (
            GroundwaterMonitoringWellDynamic.objects.filter(
                groundwater_monitoring_well_static=self.groundwater_monitoring_well_static,
                date_from__gt=self.date_from,
            )
            .order_by("date_from")
            .first()
        )

        if next_dynamic:
            return next_dynamic.date_from
        return None

    date_till.fget.short_description = "Geldig tot"

    @property
    def number_of_standpipes(self):
        return GroundwaterMonitoringTubeStatic.objects.filter(
            groundwater_monitoring_well_static=self.groundwater_monitoring_well_static
        ).count()

    number_of_standpipes.fget.short_description = "Aantal buizen"

    @property
    def deliver_gld_to_bro(self):
        return (
            GroundwaterMonitoringTubeStatic.objects.filter(
                deliver_gld_to_bro=True,
                groundwater_monitoring_well_static=self.groundwater_monitoring_well_static,
            ).count()
            > 0
        )

    deliver_gld_to_bro.fget.short_description = "GLD aanleveren aan BRO"

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_well_dynamic'
        verbose_name = "Grondwatermonitoring Put - Dynamisch"
        verbose_name_plural = "Grondwatermonitoring Putten - Dynamisch"


class GroundwaterMonitoringTubeStatic(BaseModel):
    groundwater_monitoring_tube_static_id = models.AutoField(
        primary_key=True, verbose_name="DB ID"
    )
    groundwater_monitoring_well_static = models.ForeignKey(
        GroundwaterMonitoringWellStatic,
        on_delete=models.CASCADE,
        related_name="tube",
        verbose_name="Put",
    )
    deliver_gld_to_bro = models.BooleanField(
        blank=True, default=False, verbose_name="Lever GLD aan naar BRO"
    )
    tube_number = models.IntegerField(
        blank=True,
        null=True,
        validators=[validators_models.tube_number_validation],
        verbose_name="Buisnummer",
    )
    tube_type = models.CharField(
        choices=TUBETYPE,
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Buistype",
        default="standaardbuis",
    )
    artesian_well_cap_present = models.CharField(
        choices=BOOLEAN_CHOICES,
        max_length=200,
        blank=True,
        null=True,
        default="nee",
        verbose_name="Voorzien van drukdop",
    )
    sediment_sump_present = models.CharField(
        choices=BOOLEAN_CHOICES,
        max_length=200,
        blank=True,
        null=True,
        default="nee",
        verbose_name="Voorzien van zandvang",
    )
    tube_material = models.CharField(
        choices=TUBEMATERIAL,
        max_length=200,
        blank=True,
        null=True,
        default="peHighDensity",
        verbose_name="Buismateriaal",
    )
    screen_length = models.FloatField(
        blank=True, null=True, verbose_name="Filterlengte", default=1.0
    )
    sock_material = models.CharField(
        choices=SOCKMATERIAL,
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Kousmateriaal",
        default="nylon",
    )
    sediment_sump_length = models.FloatField(
        blank=True,
        null=True,
        validators=[validators_models.zandvanglengte_validator],
        verbose_name="Zandvanglengte",
    )
    bro_actions = models.TextField(
        blank=True, null=True, verbose_name="Benodigde acties om BRO Compleet te maken"
    )
    krw_body = models.CharField(
        choices=KRW_CHOICES,
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Grondwaterlichaam",
    )
    gwl_depth = models.CharField(
        max_length=30,
        choices=DEPTH_CHOICES,
        blank=True,
        null=True,
        verbose_name="Diepte grondwaterlichaam",
    )
    # bro_complete

    state: Manager["GroundwaterMonitoringTubeDynamic"]
    geo_ohm_cable: Manager["GeoOhmCable"]

    @property
    def report(self):
        remarks = self.state.all().order_by("date_from")
        report = ""
        for remark in remarks:
            report += f"{remark.date_from.date()}: {remark.comment}\n\n"

        return report

    report.fget.short_description = "Rapport"

    @property
    def number_of_geo_ohm_cables(self):
        return GeoOhmCable.objects.filter(
            groundwater_monitoring_tube_static=self
        ).count()

    number_of_geo_ohm_cables.fget.short_description = "Aantal geo ohm kabels"

    @property
    def gmn_ids(self) -> list[str]:
        gmn_ids = []
        for mp in self.measuring_point.all():
            gmn_ids.append(mp.gmn.gmn_bro_id)

        return gmn_ids

    def __str__(self):
        if self.groundwater_monitoring_well_static:
            well = f"{self.groundwater_monitoring_well_static.__str__()}"
            return f"{well}-{format_integer(int(self.tube_number))}"
        return self.groundwater_monitoring_tube_static_id

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_tube_static'
        verbose_name = "Grondwatermonitoring Filter - Statisch"
        verbose_name_plural = "Grondwatermonitoring Filters - Statisch"


class GroundwaterMonitoringTubeDynamic(BaseModel):
    groundwater_monitoring_tube_dynamic_id = models.AutoField(
        primary_key=True, verbose_name="DB ID"
    )
    groundwater_monitoring_tube_static = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        related_name="state",
        verbose_name="Filter",
    )
    date_from = models.DateTimeField(
        help_text="formaat: YYYY-MM-DD", verbose_name="Geldig vanaf"
    )
    tube_top_diameter = models.IntegerField(
        blank=True, null=True, verbose_name="Diameter bovenkantbuis"
    )
    variable_diameter = models.CharField(
        choices=BOOLEAN_CHOICES,
        max_length=200,
        blank=True,
        null=True,
        default="nee",
        verbose_name="Variabele diameter",
    )
    tube_status = models.CharField(
        choices=TUBESTATUS,
        max_length=200,
        blank=True,
        null=True,
        default="gebruiksklaar",
        verbose_name="Buisstatus",
    )
    tube_top_position = models.FloatField(
        blank=True,
        null=True,
        validators=[validators_models.referentiehoogte_validation],
        help_text="Hoogte bovenkant buis. Eenheid: mNAP",
        verbose_name="Positie bovenkant buis",
    )

    sensor_depth = models.FloatField(
        blank=True,
        null=True,
        help_text="Hoogte bovenkant buis. Eenheid: m tov bkb.",
        verbose_name="Sensor diepte",
    )
    sensor_id = models.CharField(
        blank=True,
        null=True,
        help_text="Serienummer van de sensor",
        verbose_name="Sensor ID",
        max_length=50,
    )

    tube_top_positioning_method = models.CharField(
        choices=TUBETOPPOSITIONINGMETHOD,
        max_length=200,
        blank=True,
        null=True,
        default="RTKGPS20tot100cm",
        verbose_name="Methode locatiebepaling bovenkantbuis",
    )
    tube_packing_material = models.CharField(
        choices=TUBEPACKINGMATERIAL,
        max_length=200,
        blank=True,
        null=True,
        default="bentonietFiltergrind",
        verbose_name="Aanvul materiaal buis",
    )
    glue = models.CharField(
        choices=GLUE,
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Lijm",
        default="geen",
    )
    plain_tube_part_length = models.FloatField(
        blank=True, null=True, verbose_name="Lengte stijgbuis"
    )  # Lengte stijbuisdeel
    inserted_part_diameter = models.FloatField(
        blank=True,
        null=True,
        validators=[validators_models.diameter_bovenkant_ingeplaatst_deel_validation],
        verbose_name="Diameter ingeplaatst deel",
    )  # This field type is a guess.
    inserted_part_length = models.FloatField(
        blank=True,
        null=True,
        validators=[validators_models.lengte_ingeplaatst_deel_validation],
        verbose_name="Lengte ingeplaatst deel",
    )  # This field type is a guess.
    inserted_part_material = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Materiaal ingeplaatst deel"
    )
    comment = models.TextField(blank=True, null=True, verbose_name="Commentaar")
    comment_processed = models.BooleanField(
        blank=True, default=True, verbose_name="Commentaar verwerkt"
    )
    bro_actions = models.TextField(
        blank=True, null=True, verbose_name="Benodigde acties om BRO Compleet te maken"
    )

    event: Manager["Event"]

    def save(self, *args, **kwargs):
        if self.comment in [None, ""]:
            self.comment_processed = True
        super().save(*args, **kwargs)

    @property
    def date_till(self):
        next_dynamic = (
            GroundwaterMonitoringTubeDynamic.objects.filter(
                groundwater_monitoring_tube_static=self.groundwater_monitoring_tube_static,
                date_from__gt=self.date_from,
            )
            .order_by("date_from")
            .first()
        )

        if next_dynamic:
            return next_dynamic.date_from
        return None

    date_till.fget.short_description = "Geldig tot"

    @property
    def tube_inserted(self):
        if (
            self.inserted_part_diameter
            or self.inserted_part_length
            or self.inserted_part_material
        ):
            return True
        return False

    @property
    def screen_top_position(self):
        if (
            self.tube_top_position is not None
            and self.plain_tube_part_length is not None
        ):
            return self.tube_top_position - self.plain_tube_part_length
        return None

    @property
    def screen_bottom_position(self):
        if (
            self.screen_top_position is not None
            and self.groundwater_monitoring_tube_static.screen_length is not None
        ):
            return (
                self.screen_top_position
                - self.groundwater_monitoring_tube_static.screen_length
            )
        return None

    @property
    def tube_bottom_position(self):
        if self.screen_bottom_position is not None:
            if self.groundwater_monitoring_tube_static.sediment_sump_present:
                return self.screen_bottom_position
            elif (
                self.groundwater_monitoring_tube_static.sediment_sump_length is not None
            ):
                return (
                    self.screen_bottom_position
                    - self.groundwater_monitoring_tube_static.sediment_sump_length
                )
        return None

    def __str__(self):
        if self.groundwater_monitoring_tube_static:
            if self.date_till:
                till = self.date_till.date()
                return f"{self.groundwater_monitoring_tube_static.__str__()} ({self.date_from.date()} - {till})"

            return f"{self.groundwater_monitoring_tube_static.__str__()} ({self.date_from.date()} - Present)"
        else:
            return self.groundwater_monitoring_tube_dynamic_id

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_tube_dynamic'
        verbose_name = "Grondwatermonitoring Filter - Dynamisch"
        verbose_name_plural = "Grondwatermonitoring Filters - Dynamisch"


class GeoOhmCable(BaseModel):
    geo_ohm_cable_id = models.AutoField(primary_key=True, verbose_name="DB ID")
    groundwater_monitoring_tube_static = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        verbose_name="Buis",
        related_name="geo_ohm_cable",
    )
    cable_number = models.IntegerField(
        blank=True, null=True, verbose_name="Kabelnummer"
    )
    bro_actions = models.TextField(
        blank=True, null=True, verbose_name="Benodigde acties om BRO Compleet te maken"
    )

    electrode: Manager["Electrode"]

    def __str__(self):
        return f"{self.groundwater_monitoring_tube_static}-K{self.cable_number}"

    @property
    def electrode_count(self):
        number_of_electrodes = Electrode.objects.filter(geo_ohm_cable=self).count()
        # validators_models.aantal_elektrodes_validator(number_of_electrodes)
        if number_of_electrodes < 2:
            return "minimaal aantal elektrodes van 2 nog niet gelinkt aan Geo-ohmkabel"
        else:
            return number_of_electrodes

    electrode_count.fget.short_description = "Aantal electrodes"

    class Meta:
        managed = True
        db_table = 'gmw"."geo_ohm_cable_static'
        verbose_name = "Geo Ohm Kabel"
        verbose_name_plural = "Geo Ohm Kabels"


class Electrode(BaseModel):
    electrode_static_id = models.AutoField(primary_key=True, verbose_name="DB ID")
    geo_ohm_cable = models.ForeignKey(
        GeoOhmCable,
        on_delete=models.CASCADE,
        related_name="electrode",
        verbose_name="Geo Ohm Kabel",
    )
    electrode_packing_material = models.CharField(
        choices=ELECTRODEPACKINGMATERIAL,
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Aanvulmateriaal elektrode",
    )
    electrode_position = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        validators=[validators_models.elektrodepositie_validator],
        verbose_name="Positie",
        help_text="m NAP",
    )
    electrode_number = models.IntegerField(blank=True, null=True, verbose_name="Nummer")
    electrode_status = models.CharField(
        choices=ELECTRODESTATUS,
        max_length=50,
        blank=True,
        null=True,
        default="gebruiksklaar",
    )
    bro_actions = models.TextField(
        blank=True, null=True, verbose_name="Benodigde acties om BRO Compleet te maken"
    )

    def __str__(self):
        return f"{self.geo_ohm_cable.groundwater_monitoring_tube_static}-K{self.geo_ohm_cable.cable_number}E{self.electrode_number}"

    class Meta:
        managed = True
        db_table = 'gmw"."electrode'
        verbose_name = "Electrode"
        verbose_name_plural = "Electrodes"


class Event(BaseModel):
    change_id = models.AutoField(primary_key=True, verbose_name="DB ID")
    event_name = models.CharField(
        choices=EVENTNAME,
        max_length=200,
        verbose_name="Naam gebeurtenis",
    )
    event_date = models.DateField(
        null=True,
        blank=True,
        help_text="Formaat: YYYY-MM-DD",
        validators=[validators_models.datetime_validation],
        verbose_name="Datum gebeurtenis",
    )
    groundwater_monitoring_well_static = models.ForeignKey(
        GroundwaterMonitoringWellStatic,
        on_delete=models.CASCADE,
        related_name="event",
        verbose_name="Put",
    )
    groundwater_monitoring_well_dynamic = models.ForeignKey(
        GroundwaterMonitoringWellDynamic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event",
        verbose_name="Put - dynamisch",
    )
    groundwater_monitoring_tube_dynamic = models.ManyToManyField(
        GroundwaterMonitoringTubeDynamic,
        blank=True,
        verbose_name="Buizen - dynamisch",
        related_name="event",
    )
    electrodes = models.ManyToManyField(
        Electrode,
        blank=True,
        verbose_name="Electrodes",
        related_name="event",
    )
    correction_reason = models.CharField(
        choices=CORRECTION_REASON_OPTIONS,
        null=True,
        blank=True,
        verbose_name="Correctie reden",
    )
    delivered_to_bro = models.BooleanField(
        blank=True, default=False, verbose_name="Aangeleverd aan BRO"
    )
    bro_actions = models.TextField(
        blank=True, null=True, verbose_name="Benodigde acties om BRO Compleet te maken"
    )
    complete_bro = models.BooleanField(
        blank=True, default=False, verbose_name="BRO Compleet"
    )  # Is the data in the table complete as required for the BRO

    def __str__(self):
        return str(self.change_id)

    class Meta:
        managed = True
        db_table = 'gmw"."event'
        verbose_name = "Tussentijdse Gebeurtenis"
        verbose_name_plural = "Tussentijdse Gebeurtenissen"

    def save(self, *args, **kwargs):
        if self.change_id is not None:
            current_db = Event.objects.get(change_id=self.change_id)
            if current_db.correction_reason != self.correction_reason:
                self.delivered_to_bro = False

        super().save(*args, **kwargs)


def get_current_values(instance):
    """Get a dictionary of the current field values."""
    return {
        field.name: getattr(instance, field.name) for field in instance._meta.fields
    }


class gmw_registration_log(BaseModel):
    bro_id = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="BRO ID"
    )
    event_id = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Evenement ID"
    )
    validation_status = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Validatiestatus"
    )
    delivery_id = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Levering ID"
    )
    delivery_type = models.CharField(
        choices=DELIVERY_TYPE_CHOICES,
        blank=False,
        max_length=40,
        default="register",
        verbose_name="Type levering",
    )
    delivery_status = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Leveringsstatus"
    )
    comments = models.CharField(
        max_length=10000, null=True, blank=True, verbose_name="Commentaar"
    )
    last_changed = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Laatst veranderd"
    )
    corrections_applied = models.BooleanField(
        blank=True, null=True, verbose_name="Correcties toegepast"
    )
    quality_regime = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Kwaliteitsregime"
    )
    file = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Bestand"
    )
    process_status = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Verwerkingsstatus"
    )
    # Could possibly be removed later
    object_id_accountable_party = models.CharField(
        max_length=254,
        null=True,
        blank=True,
        verbose_name="Verantwoordelijke partij ID",
    )

    @property
    def event_type(self):
        if self.event_id is not None:
            return Event.objects.get(change_id=self.event_id).event_name
        return "-"

    event_type.fget.short_description = "Type evenement"

    def __str__(self):
        if self.bro_id is None:
            return f"{self.id}-{self.delivery_type}_log ({self.date_modified})"
        return f"{self.bro_id}-{self.delivery_type}_log ({self.date_modified})"

    def _set_original_values(self, instance):
        self._original_values = get_current_values(instance)

    def has_changed(self):
        """Check if any field has changed."""
        current_values = get_current_values(self)
        return any(
            current_values[field] != self._original_values[field]
            for field in current_values
        )

    def save(self, *args, **kwargs):
        if self.id is not None:
            db_instance = gmw_registration_log.objects.get(id=self.id)
            self._set_original_values(db_instance)

            if self.has_changed():
                # If there is any change
                self.last_changed = datetime.datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        super().save(*args, **kwargs)

    class Meta:
        managed = True
        db_table = 'aanlevering"."gmw_registration_log'
        verbose_name = "GMW Synchronisatie Log"
        verbose_name_plural = "GMW Synchronisatie Logs"


class Picture(BaseModel):
    picture_id = models.AutoField(primary_key=True)
    groundwater_monitoring_well_static = models.ForeignKey(
        GroundwaterMonitoringWellStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Put",
        related_name="picture",
    )
    recording_datetime = models.DateTimeField(
        blank=True, null=True, verbose_name="Fotomoment"
    )
    is_main = models.BooleanField(blank=True, default=False, verbose_name="Hoofdfoto")
    picture = models.ImageField(
        upload_to="static/gmw/pictures/",
        blank=True,
        null=True,
        editable=True,
        verbose_name="Foto",
    )
    description = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Beschrijving"
    )

    @property
    def image_tag(self):
        if self.picture:
            return format_html(
                f'<img src="{self.picture.url}" style="max-width:100px; max-height:100px"/>'
            )
        else:
            return format_html("No image available.")

    def save(self, *args, **kwargs):
        # If no recording_datetime is set and there's an image
        if self.picture and not self.recording_datetime:
            try:
                timestamp = None
                image = Image.open(self.picture)

                if image.format.lower() in ["jpeg", "jpg"]:
                    exif_data = image._getexif()
                    if exif_data:
                        readable = {
                            TAGS.get(tag): val for tag, val in exif_data.items()
                        }
                        timestamp_str = readable.get(
                            "DateTimeOriginal"
                        ) or readable.get("DateTime")
                        if timestamp_str:
                            timestamp = datetime.datetime.strptime(
                                timestamp_str, "%Y:%m:%d %H:%M:%S"
                            )

                elif image.format.lower() == "png":
                    info = image.info
                    for key in ["date:create", "Creation Time", "creation_time"]:
                        timestamp_str = info.get(key)
                        if timestamp_str:
                            try:
                                timestamp = datetime.datetime.fromisoformat(
                                    timestamp_str
                                )
                                break
                            except ValueError:
                                print("PNG timestamp not in isoformat")
                                pass

                if not timestamp:
                    timestamp = datetime.datetime.now()

                self.recording_datetime = timestamp

            except Exception as e:
                print(f"Error extracting time stamp: {e}")
                self.recording_datetime = None

        super().save(*args, **kwargs)

    class Meta:
        managed = True
        db_table = 'gmw"."picture'
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"


class MaintenanceParty(BaseModel):
    maintenance_party_id = models.AutoField(primary_key=True, verbose_name="DB ID")
    surname = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Achternaam"
    )
    first_name = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Voornaam"
    )
    function = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Functie"
    )
    organisation = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Organisatie"
    )
    adress = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Adres"
    )
    postal_code = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Postcode"
    )
    place = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Woonplaats"
    )
    phone = models.IntegerField(blank=True, null=True, verbose_name="Telefoon")
    mobilephone = models.IntegerField(null=True, blank=True, verbose_name="Mobiel")
    email = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Email"
    )

    def __str__(self):
        return f"{self.first_name} {self.surname}"

    class Meta:
        db_table = 'gmw"."maintenance_party'
        verbose_name = "Onderhoudsteam"
        verbose_name_plural = "Onderhoudsteams"


class Maintenance(BaseModel):
    maintenance_id = models.AutoField(primary_key=True, verbose_name="DB ID")
    groundwater_monitoring_well_static = models.ForeignKey(
        GroundwaterMonitoringWellStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Put",
        related_name="maintenance",
    )
    groundwater_monitoring_tube_static = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Filter",
    )
    notification_date = models.DateField(
        blank=True, null=True, verbose_name="Meldingsdatum"
    )
    kind_of_maintenance = models.CharField(
        max_length=254, verbose_name="Type onderhoud"
    )
    description = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Beschrijving"
    )
    picture = models.ForeignKey(
        Picture, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Foto"
    )
    reporter = models.ForeignKey(
        MaintenanceParty,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reporter",
        verbose_name="Melder",
    )  # Maintenance_party_id
    execution_date = models.DateField(
        blank=True, null=True, verbose_name="Uitvoeringsdatum"
    )
    execution_by = models.ForeignKey(
        MaintenanceParty,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="executioner",
        verbose_name="Uitvoerder",
    )  # Maintenance_party_id

    class Meta:
        managed = True
        db_table = 'gmw"."maintenance'
        verbose_name = "Onderhoudsmoment"
        verbose_name_plural = "Onderhoudsmomenten"


def format_integer(num):
    if num < 10:
        return f"00{num}"
    elif num < 100:
        return f"0{num}"
    else:
        return str(num)
