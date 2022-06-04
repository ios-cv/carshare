from crispy_forms.layout import Field


class CustomImageField(Field):
    template = "drivers/fields/custom_image_field.html"
