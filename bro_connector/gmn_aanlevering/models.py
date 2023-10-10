from django.db import models

KADER_AANLEVERING_GMN = (
    ("waterwetStrategischGrondwaterbeheer", "waterwetStrategischGrondwaterbeheer"),
    ("waterwetGrondwaterzorgplicht", "waterwetGrondwaterzorgplicht"),
    ("waterwetOnttrekkingInfiltratie", "waterwetOnttrekkingInfiltratie"),
    ("waterwetPeilbeheer", "waterwetPeilbeheer"),
    (
        "waterwetWaterstaatswerkAanlegWijziging",
        "waterwetWaterstaatswerkAanlegWijziging",
    ),
    ("waterwetWaterstaatswerkIngreep", "waterwetWaterstaatswerkIngreep"),
    ("waterwetWaterstaatswerkBeheer", "waterwetWaterstaatswerkBeheer"),
    ("kaderrichtlijnWater", "kaderrichtlijnWater"),
    ("waterschapswet", "waterschapswet"),
    ("drinkwaterwet", "drinkwaterwet"),
    ("ontgrondingenwet", "ontgrondingenwet"),
    ("wetNatuurbescherming", "wetNatuurbescherming"),
)

MONITORINGDOEL = (
    ("strategischBeheerKwaliteitLandelijk", "strategischBeheerKwaliteitLandelijk"),
    ("strategischBeheerKwantiteitLandelijk", "strategischBeheerKwantiteitLandelijk"),
    ("strategischBeheerKwaliteitRegionaal", "strategischBeheerKwaliteitRegionaal"),
    ("strategischBeheerKwantiteitRegionaal", "strategischBeheerKwantiteitRegionaal"),
    ("beheersingStedelijkGebied", "beheersingStedelijkGebied"),
    ("gevolgenOnttrekkingKwaliteit", "gevolgenOnttrekkingKwaliteit"),
    ("gevolgenOnttrekkingKwantiteit", "gevolgenOnttrekkingKwantiteit"),
    ("gevolgenPeilbeheer", "gevolgenPeilbeheer"),
    ("gevolgenWaterstaatswerkKwaliteit", "gevolgenWaterstaatswerkKwaliteit"),
    ("gevolgenWaterstaatswerkKwantiteit", "gevolgenWaterstaatswerkKwantiteit"),
    ("waterstaatswerkBeheerKwaliteit", "waterstaatswerkBeheerKwaliteit"),
    ("waterstaatswerkBeheerKwantiteit", "waterstaatswerkBeheerKwantiteit"),
    ("veiligstellingGrondwaterKwaliteit", "veiligstellingGrondwaterKwaliteit"),
    ("veiligstellingGrondwaterKwantiteit", "veiligstellingGrondwaterKwantiteit"),
    ("waterstaatkundigeVerzorgingKwaliteit", "waterstaatkundigeVerzorgingKwaliteit"),
    ("waterstaatkundigeVerzorgingKwantiteit", "waterstaatkundigeVerzorgingKwantiteit"),
    (
        "veiligstellingDrinkwatervoorzieningKwaliteit",
        "veiligstellingDrinkwatervoorzieningKwaliteit",
    ),
    (
        "veiligstellingDrinkwatervoorzieningKwantiteit",
        "veiligstellingDrinkwatervoorzieningKwantiteit",
    ),
    ("gevolgenOntgronding", "gevolgenOntgronding"),
    ("natuurbescherming", "natuurbescherming"),
    ("natuurbeheer", "natuurbeheer"),
)

# Create your models here.
class GroundwaterMonitoringNet(models.Model):
    id = models.AutoField(primary_key=True)
    broid_gmn = models.CharField(
        max_length=255, null=True, blank=True, editable=False, verbose_name="Broid GMN"
    )
    name = models.CharField(
        max_length=255, null=True, blank=True, editable=False, verbose_name="Broid GMN"
    )
    delivery_context = models.CharField(
        blank=False,
        max_length=235,
        verbose_name="Kader aanlevering",
        choices=KADER_AANLEVERING_GMN,
    )
    monitoringPurpose = models.CharField(
        blank=False,
        max_length=235,
        verbose_name="Monitoringdoel",
        choices= MONITORINGDOEL,
    )
    groundwaterAspect = models.CharField(
        blank=True,
        max_length=235,
        verbose_name="Grondwateraspect",
        choices=(
            ("kwaliteit", "kwaliteit"),
            ("kwantiteit", "kwantiteit"),
        ),
    )

    def __str__(self):
        return self.naam
    
    def __unicode__(self):
        return self.naam
    
class Meta:
        managed = True
        db_table = 'gmn"."Meetnet'
        verbose_name = "BRO meetnet"
        verbose_name_plural = "BRO meetnetten (2.1)"
        _admin_name = "BRO meetnet"
        ordering = ("naam",)