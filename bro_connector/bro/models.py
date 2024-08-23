from django.db import models
import os
import base64
from django.db.models import CharField
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import random


def get_color_value():
    # Generate random values for red, green, and blue components
    red = random.randint(0, 255)
    green = random.randint(0, 255)
    blue = random.randint(0, 255)

    # Convert decimal values to hexadecimal and format them
    color_code = "#{:02x}{:02x}{:02x}".format(red, green, blue)

    return color_code

class SecureCharField(CharField):
    """
    Safe string field that gets encrypted before being stored in the database, and
    decrypted when retrieved. Since the stored values have a fixed length, using the
    "max_length" parameter in your field will not work, it will be overridden by default.
    """

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 512
        kwargs['null'] = True
        kwargs['blank'] = True
        super().__init__(*args, **kwargs)

    salt = bytes(os.environ["SECURE_STRING_SALT"], 'utf-8')
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )

    # Encode the FERNET encryption key
    key = base64.urlsafe_b64encode(kdf.derive(
        bytes(os.environ['FERNET_ENCRYPTION_KEY'], 'utf-8')
    ))

    # Create a "fernet" object using the key stored in the .env file
    f = Fernet(key)

    def from_db_value(self, value: str, expression, connection) -> str:
        """
        Decrypts the value retrieved from the database.
        """
        if type(value) != str:
            return value
        value = str(self.f.decrypt(bytes(value, 'cp1252')), encoding='utf-8')
        return value

    def get_prep_value(self, value: str) -> str:
        """
        Encrypts the value before storing it in the database.
        """
        if type(value) != str:
            return value
        value = str(self.f.encrypt(bytes(value, 'utf-8')), 'cp1252')
        return value

class Organisation(models.Model):
    name = models.CharField(max_length=50, null=True, blank=True)
    company_number = models.IntegerField(blank=True)
    color = models.CharField(max_length=50, null=True, blank=True)
    bro_user = SecureCharField()
    bro_token = SecureCharField()


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
        super().save(*args, **kwargs)

class BROProject(models.Model):
    name = models.CharField(max_length=50, null=True, blank=True)
    project_number = models.IntegerField(null=False, blank=False)
    owner = models.ForeignKey(Organisation,on_delete=models.SET_NULL, null=True, blank=False, related_name='owner')
    authorized = models.ManyToManyField(Organisation, blank=True, related_name='authorized_company')

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
