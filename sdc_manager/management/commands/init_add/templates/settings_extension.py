
STATIC_ROOT = './static/'

STATICFILES_DIRS = ["./§PROJECT§/static"]

ASGI_APPLICATION = '§PROJECT§.asgi.application'

if DEBUG:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [('redis', 6379)],
            },
        },
    }

MEDIA_URL = '/media/'
MEDIA_ROOT = './media/'

#EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
#EMAIL_HOST =''
#EMAIL_PORT = 587
#EMAIL_HOST_USER = ''
#DEFAULT_FROM_EMAIL = ''
#EMAIL_HOST_PASSWORD = ''
#EMAIL_USE_TLS = True