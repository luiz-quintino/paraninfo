from django import template

register = template.Library()

@register.filter(name='split')
def split(value, key):
    """
    Divide uma string com base no delimitador fornecido.
    """
    if not isinstance(value, str):
        return []
    return value.split(key)