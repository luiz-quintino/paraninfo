from decouple import config
from django.contrib.messages import constants as messages

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!

DEBUG = True

ALLOWED_HOSTS = ['212.85.21.167', 'srv791196.hstgr.cloud', '127.0.0.1', 'localhost']


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "credential",
    "users",
    "home",
    "paraninfo_admin",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'home.middleware.PersistentUserDataMiddleware',  # Middleware home para comissao e uuid
]

ROOT_URLCONF = "_paraninfo.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "_paraninfo/templates",
            BASE_DIR / "users/templates",
            BASE_DIR / "paraninfo_admin/templates",
            BASE_DIR / "home/templates",
                ],  # Diretório para templates personalizados
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "_paraninfo.wsgi.application"

MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases


DATABASES = {
    'default': {
        'ENGINE'    : 'django.db.backends.mysql',
        'NAME'      : config('DB_NAME'),
        'USER'      : config('DB_USER'),
        'PASSWORD'  : config('DB_PASSWORD'),
        'HOST'      : config('DB_HOST'),
        'PORT'      : config('DB_PORT', cast=int),
        'OPTIONS'   : {
                        'charset': 'utf8mb4',
        },
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "_paraninfo/static",
    BASE_DIR / "users/static",
    BASE_DIR / "credential/static",
    BASE_DIR / "static",
    BASE_DIR / "paraninfo_admin/static",
    
    ]

# Diretório onde os arquivos estáticos serão coletados (em produção)
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Configurações adicionais
LOGIN_URL = '/credential/login/'         # Caminho da sua página de login
LOGIN_REDIRECT_URL = 'home'   # Redirecionar após login
LOGOUT_REDIRECT_URL = 'home'  # Redirecionar após logout

# Mensagem personalizada para redirecionamento
from django.contrib.messages import constants as messages

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
MESSAGE_TAGS = {
    messages.ERROR: 'alert-error',
    messages.SUCCESS: 'alert-success',
    messages.INFO: 'alert-info',
}

# Configuração de sessões
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Usa o banco de dados para armazenar sessões
SESSION_COOKIE_NAME = 'sessionid'  # Nome do cookie de sessão
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Sessão não expira ao fechar o navegador
SESSION_COOKIE_AGE = 1209600  # Tempo de vida da sessão em segundos (2 semanas)
SESSION_SAVE_EVERY_REQUEST = True  # Salva a sessão a cada requisição