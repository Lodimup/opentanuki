from django import template

register = template.Library()


@register.filter
def basename(value):
    import os
    return os.path.basename(str(value))
