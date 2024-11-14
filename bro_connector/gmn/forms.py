from django.forms import ModelForm, TextInput

from . import models


class GroundwaterMonitoringNetForm(ModelForm):
    class Meta:
        model = models.GroundwaterMonitoringNet
        fields = "__all__"
        widgets = {
            "color": TextInput(attrs={"type": "color"}),
        }


class SubgroupForm(ModelForm):
    class Meta:
        model = models.Subgroup
        fields = "__all__"
        widgets = {
            "color": TextInput(attrs={"type": "color"}),
        }