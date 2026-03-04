from django import template


register = template.Library()


@register.filter
def safe_file_url(file_field):
    try:
        return file_field.url if file_field else ''
    except Exception:
        return ''
