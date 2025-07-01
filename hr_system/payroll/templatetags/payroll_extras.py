import calendar
from django import template

register = template.Library()

@register.filter(name='month_name_filter')
def month_name_custom(month_number):
    try:
        month_number = int(month_number)
        if 1 <= month_number <= 12:
            return calendar.month_name[month_number]
    except (ValueError, TypeError):
        pass # Fall through to return empty string or original value
    return '' # Or you could return month_number if conversion fails

@register.simple_tag
def get_verbose_field_name(instance, field_name):
    """
    Returns the verbose name of a field.
    """
    try:
        return instance._meta.get_field(field_name).verbose_name
    except: # noqa
        return field_name.replace("_", " ").title()

@register.filter
def get_field_value(instance, field_name):
    """
    Returns the value of a field, handling potential AttributeError.
    """
    try:
        return getattr(instance, field_name)
    except AttributeError:
        return None
