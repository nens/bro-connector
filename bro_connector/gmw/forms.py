import django.forms as forms
from . import models


class BinaryFileInput(forms.ClearableFileInput):
    def is_initial(self, value):
        """
        Return whether value is considered to be initial value.
        """
        return bool(value)

    def format_value(self, value):
        """Format the size of the value in the db.

        We can't render it's name or url, but we'd like to give some information
        as to wether this file is not empty/corrupt.
        """
        if self.is_initial(value):
            return f"{len(value)} bytes"

    def value_from_datadict(self, data, files, name):
        """Return the file contents so they can be put in the db."""
        upload = super().value_from_datadict(data, files, name)
        if upload:
            return upload.read()


class GroundwaterMonitoringWellStaticForm(forms.ModelForm):
    x = forms.CharField(required=True)
    y = forms.CharField(required=True)
    cx = forms.CharField(required=False)
    cy = forms.CharField(required=False)

    class Meta:
        model = models.GroundwaterMonitoringWellStatic
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.in_management == False:
            for name, field in self.fields.items():
                if name == "in_management":
                    continue
                field.widget.attrs["readonly"] = True
                field.disabled = True

        # Wijs de waarde toe aan het initial attribuut van het veld
        if self.instance.coordinates:
            self.fields["x"].initial = self.instance.x
            self.fields["y"].initial = self.instance.y

        if self.instance.construction_coordinates:
            self.fields["cx"].initial = self.instance.cx
            self.fields["cy"].initial = self.instance.cy


class GroundwaterMonitoringWellDynamicForm(forms.ModelForm):
    class Meta:
        model = models.GroundwaterMonitoringWellDynamic
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.groundwater_monitoring_well_static == None:
            pass

        elif self.instance.groundwater_monitoring_well_static.in_management == False:
            for name, field in self.fields.items():
                field.widget.attrs["readonly"] = True
                field.disabled = True


class GroundwaterMonitoringTubeStaticForm(forms.ModelForm):
    class Meta:
        model = models.GroundwaterMonitoringTubeStatic
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.groundwater_monitoring_well_static == None:
            pass

        elif self.instance.groundwater_monitoring_well_static.in_management == False:
            for name, field in self.fields.items():
                field.widget.attrs["readonly"] = True
                field.disabled = True


class GroundwaterMonitoringTubeDynamicForm(forms.ModelForm):
    class Meta:
        model = models.GroundwaterMonitoringTubeDynamic
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.groundwater_monitoring_tube_static == None:
            pass

        elif (
            self.instance.groundwater_monitoring_tube_static.groundwater_monitoring_well_static.in_management
            == False
        ):
            for name, field in self.fields.items():
                field.widget.attrs["readonly"] = True
                field.disabled = True


class GeoOhmCableForm(forms.ModelForm):
    class Meta:
        model = models.GeoOhmCable
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.groundwater_monitoring_tube_static == None:
            pass

        elif (
            self.instance.groundwater_monitoring_tube_static.groundwater_monitoring_well_static.in_management
            == False
        ):
            for name, field in self.fields.items():
                field.widget.attrs["readonly"] = True
                field.disabled = True


class ElectrodeStaticForm(forms.ModelForm):
    class Meta:
        model = models.ElectrodeStatic
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.geo_ohm_cable == None:
            pass

        elif (
            self.instance.geo_ohm_cable.groundwater_monitoring_tube_static.groundwater_monitoring_well_static.in_management
            == False
        ):
            for name, field in self.fields.items():
                field.widget.attrs["readonly"] = True
                field.disabled = True


class ElectrodeDynamicForm(forms.ModelForm):
    class Meta:
        model = models.ElectrodeDynamic
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.electrode_static == None:
            pass

        elif (
            self.instance.electrode_static.geo_ohm_cable.groundwater_monitoring_tube_static.groundwater_monitoring_well_static.in_management
            == False
        ):
            for name, field in self.fields.items():
                field.widget.attrs["readonly"] = True
                field.disabled = True


class EventForm(forms.ModelForm):
    class Meta:
        model = models.Event
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.groundwater_monitoring_well_static == None:
            pass

        elif self.instance.groundwater_monitoring_well_static.in_management == False:
            for name, field in self.fields.items():
                field.widget.attrs["readonly"] = True
                field.disabled = True
