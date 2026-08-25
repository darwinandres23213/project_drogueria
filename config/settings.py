import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key)
    if value is None or value.strip() == '':
        return default
    return value


def env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(key: str, default: str = '') -> list[str]:
    raw = os.getenv(key, default)
    return [item.strip() for item in raw.split(',') if item.strip()]


SECRET_KEY = env('SECRET_KEY', 'django-insecure-change-me-in-production')
DEBUG = env_bool('DEBUG', True)
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
for host in env_list('DJANGO_ALLOWED_HOSTS'):
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

koyeb_domain = env('KOYEB_PUBLIC_DOMAIN')
if koyeb_domain and koyeb_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(koyeb_domain)
if (koyeb_domain or env('KOYEB_APP_NAME')) and '.koyeb.app' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('.koyeb.app')

CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', '')
if koyeb_domain:
    koyeb_origin = f'https://{koyeb_domain}'
    if koyeb_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(koyeb_origin)

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    'django_filters',
    # Domains
    'apps.catalogo.apps.CatalogoConfig',
    'apps.inventario.apps.InventarioConfig',
    'apps.precios.apps.PreciosConfig',
    'apps.ventas.apps.VentasConfig',
    'apps.integraciones.apps.IntegracionesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database: SQLite por defecto; MySQL vía variables de entorno
DB_ENGINE = env('DB_ENGINE', 'django.db.backends.sqlite3')

if DB_ENGINE == 'django.db.backends.mysql':
    db_options: dict = {
        'charset': 'utf8mb4',
    }
    ssl_ca = env('DB_SSL_CA')
    if ssl_ca:
        ca_path = Path(ssl_ca)
        if not ca_path.is_absolute():
            ca_path = BASE_DIR / ca_path
        db_options['ssl'] = {'ca': str(ca_path.resolve())}
        db_options['ssl_mode'] = env('DB_SSL_MODE', 'VERIFY_CA')

    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': env('DB_NAME', ''),
            'USER': env('DB_USER', ''),
            'PASSWORD': env('DB_PASSWORD', ''),
            'HOST': env('DB_HOST', '127.0.0.1'),
            'PORT': env('DB_PORT', '3306'),
            'OPTIONS': db_options,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': env('DB_NAME', str(BASE_DIR / 'db.sqlite3')),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = env('LANGUAGE_CODE', 'es-co')
TIME_ZONE = env('TIME_ZONE', 'America/Bogota')
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# Imágenes de producto en disco (no OneDrive): se sirven en esta URL pública.
IMAGENES_PUBLIC_URL = env('IMAGENES_PUBLIC_URL', '/media/imagenes-productos/')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'shared.presentation.pagination.StandardPagination',
    'PAGE_SIZE': int(env('DRF_PAGE_SIZE', '20')),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

CORS_ALLOW_ALL_ORIGINS = env_bool('CORS_ALLOW_ALL_ORIGINS', True)
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', '')

# OneDrive / Microsoft Graph (HU-SIG-001+)
# PROVIDER=local → usa rutas locales (recomendado para probar sin Graph)
# PROVIDER=onedrive → Microsoft Graph (requiere app registration)
ONEDRIVE = {
    'PROVIDER': env('ONEDRIVE_PROVIDER', 'local'),
    'TENANT_ID': env('ONEDRIVE_TENANT_ID', ''),
    'CLIENT_ID': env('ONEDRIVE_CLIENT_ID', ''),
    'CLIENT_SECRET': env('ONEDRIVE_CLIENT_SECRET', ''),
    'DRIVE_ID': env('ONEDRIVE_DRIVE_ID', ''),
    'ROOT_FOLDER': env('ONEDRIVE_ROOT_FOLDER', '/'),
    'SHARE_URL': env('ONEDRIVE_SHARE_URL', ''),
    'CATALOGO_LOCAL_PATH': env('ONEDRIVE_CATALOGO_LOCAL_PATH', ''),
    'IMAGENES_LOCAL_PATH': env('ONEDRIVE_IMAGENES_LOCAL_PATH', ''),
    'CATALOGO_SHARE_URL': env('ONEDRIVE_CATALOGO_SHARE_URL', ''),
    'IMAGENES_SHARE_URL': env('ONEDRIVE_IMAGENES_SHARE_URL', ''),
    'CATALOGO_REMOTE_PATH': env('ONEDRIVE_CATALOGO_REMOTE_PATH', ''),
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': env('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'apps.integraciones': {
            'handlers': ['console'],
            'level': env('INTEGRACIONES_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}
