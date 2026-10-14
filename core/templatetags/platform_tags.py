from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def query_page(context, page):
    query = context["request"].GET.copy()
    query["page"] = page
    return "?" + query.urlencode()


@register.filter
def pretty(value):
    return str(value).replace("_", " ").title()


@register.filter
def stars(value):
    count = max(0, min(5, round(float(value or 0))))
    return "★" * count + "☆" * (5 - count)
