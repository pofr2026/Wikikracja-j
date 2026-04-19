from django.utils import translation


class UserLanguageMiddleware:
    """
    Activates the language saved in the user's profile (Uzytkownik.language).
    Runs after LocaleMiddleware so it can override the auto-detected language
    for authenticated users who have set an explicit preference.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                lang = request.user.uzytkownik.language
                if lang:
                    translation.activate(lang)
                    request.LANGUAGE_CODE = lang
            except Exception:
                pass
        return self.get_response(request)
