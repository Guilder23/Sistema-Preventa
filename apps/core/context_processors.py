def theme_flags(request):
    """Flags globales de UI.

    En el proyecto guía esto depende del plan/empresa. Aquí se permite siempre.
    """

    return {"theme_allowed": True}
