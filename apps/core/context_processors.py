def theme_flags(request):
    """Flags globales de UI.

    El modo oscuro queda comentado temporalmente para mantener el sistema
    siempre en tema claro.
    """

    # return {"theme_allowed": True}
    return {"theme_allowed": False}
