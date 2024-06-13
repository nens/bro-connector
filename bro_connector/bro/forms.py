import django.forms as forms
from . import models
from .widgets import PasswordMaskWidget

class CompanyForm(forms.ModelForm):
    class Meta:
        model = models.Organisation
        fields = "__all__"
        widgets = {
            'bro_token': PasswordMaskWidget(),
        }