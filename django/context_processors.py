# _paraninfo/context_processors.py
from _paraninfo import settings

def development_environment(request):
    return {
        'DEVELOPMENT_ENVIRONMENT': settings.DEVELOPMENT_ENVIRONMENT
    }