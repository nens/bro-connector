from django import forms


class PasswordMaskWidget(forms.TextInput):
    template_name = "gmw/widgets/password_mask_widget.html"

    def __init__(self, *args, **kwargs):
        kwargs["attrs"] = {"type": "password", "value": "********"}
        super().__init__(*args, **kwargs)

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        if value == "********":
            return self.initial
        return value
