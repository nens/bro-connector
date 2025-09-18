import base64
import random

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.db import models
from django.db.models import CharField
from main import localsecret as ls
from main.models import BaseModel
from main.utils.kvk_company_name import KVK_COMPANY_NAME


def get_color_value():
    # Generate random values for red, green, and blue components
    red = random.randint(0, 255)
    green = random.randint(0, 255)
    blue = random.randint(0, 255)

    # Convert decimal values to hexadecimal and format them
    color_code = f"#{red:02x}{green:02x}{blue:02x}"

    return color_code


def get_company_name(company_number: int):
    # Extract company based on known company kvks. Manually extracted from: https://basisregistratieondergrond.nl/service-contact/formulieren/aangemeld-bro/
    # Use main.utils.convert_kvk_company_to_python_dict.py to generate a dictionary (outputted in a .txt file) and paste this into main.utils.kvk_company_name
    for kvk, company in KVK_COMPANY_NAME.items():
        if int(kvk) == company_number:
            return company

    return None


class SecureCharField(CharField):
    """
    Safe string field that gets encrypted before being stored in the database, and
    decrypted when retrieved. Since the stored values have a fixed length, using the
    "max_length" parameter in your field will not work, it will be overridden by default.
    """

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 512
        kwargs["null"] = True
        kwargs["blank"] = True
        super().__init__(*args, **kwargs)

    salt = bytes(ls.SALT_STRING, "utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )

    # Encode the FERNET encryption key
    key = base64.urlsafe_b64encode(kdf.derive(bytes(ls.FERNET_ENCRYPTION_KEY, "utf-8")))

    # Create a "fernet" object using the key stored in the .env file
    f = Fernet(key)

    def from_db_value(self, value: str, expression, connection) -> str:
        """
        Decrypts the value retrieved from the database.
        """
        if not isinstance(value, str):
            return value
        value = str(self.f.decrypt(bytes(value, "cp1252")), encoding="utf-8")
        return value

    def get_prep_value(self, value: str) -> str:
        """
        Encrypts the value before storing it in the database.
        """
        if not isinstance(value, str):
            return value
        value = str(self.f.encrypt(bytes(value, "utf-8")), "cp1252")
        return value


class Organisation(BaseModel):
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Naam")
    company_number = models.IntegerField(blank=True, verbose_name="KvK")
    color = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Kleurcode"
    )
    bro_user = SecureCharField(verbose_name="BRO Gebruikerstoken")
    bro_token = SecureCharField(
        verbose_name="BRO Wachtwoordtoken",
        help_text="Beide tokens komen uit het bronhoudersportaal.",
    )

    class Meta:
        managed = True
        db_table = 'bro"."organisation'
        verbose_name = "Organisatie"
        verbose_name_plural = "Organisaties"

    def __str__(self):
        if self.name:
            return self.name
        elif self.company_number:
            return str(self.company_number)
        else:
            return str(self.id)

    def save(self, *args, **kwargs):
        # Set a default color only if it's not already set
        if not self.color:
            self.color = get_color_value()
        if not self.name and self.company_number:
            self.name = get_company_name(self.company_number)
        super().save(*args, **kwargs)


class BROProject(BaseModel):
    name = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Projectnaam"
    )
    project_number = models.IntegerField(
        null=False, blank=False, verbose_name="Projectnummer"
    )
    owner = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        null=True,
        blank=False,
        related_name="owner",
        verbose_name="Eigenaar",
    )
    authorized = models.ManyToManyField(
        Organisation, blank=True, related_name="authorized_company"
    )

    class Meta:
        managed = True
        db_table = 'bro"."project'
        verbose_name = "Project"
        verbose_name_plural = "Projecten"

    def __str__(self):
        if self.name:
            return f"{self.name} ({self.project_number}) - {self.owner}"
        else:
            return f"{self.project_number} - {self.owner}"
