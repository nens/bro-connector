import threading

_user = threading.local()

def set_current_user(user):
    _user.value = user

def get_current_user():
    return getattr(_user, "value", None)

class CurrentUserMiddleware:
    """
    Stores request.user in thread-local storage so signals can use it.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(request.user)
        return self.get_response(request)
