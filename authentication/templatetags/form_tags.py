from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Adds a CSS class to a form field widget.
    Usage: {{ form.field_name|add_class:"css_class" }}
    """
    return field.as_widget(attrs={"class": css_class})