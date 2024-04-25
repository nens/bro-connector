
import datetime as dt
from django.core.exceptions import ValidationError



#### GMW models validators

def tube_number_validation(value):
    if value >= 1:
        return
    else:
        raise ValidationError("Filternummer moet groter of gelijk zijn aan 1.")
    

def date_validation(value):
    if value is None:
        return
    if value > dt.datetime.now().date():
        raise ValidationError("Datum in de toekomst is niet toegestaan")
    elif value < dt.date(1880, 1, 1):
        raise ValidationError("Datum voor 1-1-1880 is niet toegestaan")


def maaiveldhoogte_validation(value):
    if value is None:
        return
    if value < -10 or value > 325:
        raise ValidationError(
            "Maaiveldhoogte boven 325 mNAP en onder -10 mNAP niet toegestaan"
        )

def referentiehoogte_validation(value):
    if value is None:
        return
    if value < -10 or value > 325:
        raise ValidationError(
            "Referentiehoogte boven 325 mNAP en onder -10 mNAP niet toegestaan"
        )

def lengte_ingeplaatst_deel_validation(value):
    if value is None:
        return
    if value < 1 or value > 200:
        raise ValidationError("Lengte ingeplaatst deel buiten de marges (1 m - 200 m)")

def diameter_bovenkant_ingeplaatst_deel_validation(value):
    if value is None:
        return
    if value < 20 or value > 50:
        raise ValidationError(
            "Diameter ingeplaatst deel buiten de marges (20 mm - 50 mm)"
        )

def elektrodepositie_validator(value):
    value = float(value)
    print(value)
    if value is None:
        return
    if value <= -750 or value >= 50:
        raise ValidationError(
            "Elektrodepositie buiten de marges -750 m en 50 m t.o.v. bovenkant buis niet toegestaan"
        )

def aantal_elektrodes_validator(value):
    if value < 2:
        raise ValidationError("Iedere Geo-ohmkabel heeft minimaal twee elektrodes")


def buisdiameter_validator(value):
    if value < 3 or value > 1000:
        raise ValidationError("Diameter buiten marges (3 mm - 1000 mm)")


def zandvanglengte_validator(value):
    if value < 0.05:
        raise ValidationError("Zandvanglengte mag niet kleiner zijn dan 0.05 m")


def datetime_validation(value):
    if value is None:
        return
    if value.date() > dt.datetime.now().date():
        raise ValidationError("Tijdstip in de toekomst is niet toegestaan")
    elif value.date() < dt.datetime(1880, 1, 1).date():
        raise ValidationError("Tijdstip voor 1-1-1880 is niet toegestaan")
