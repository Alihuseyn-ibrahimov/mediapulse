from .views import _get_landing_content

def nav_settings(request):
    lc = _get_landing_content()
    return {"nav": lc}
