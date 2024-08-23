INSTALLED_APPS = [
    "dpd_static_support",
    "bootstrap4",
]

MIDDLEWARE = [
    "django_plotly_dash.middleware.ExternalRedirectionMiddleware",
    "django_plotly_dash.middleware.BaseMiddleware",
]

X_FRAME_OPTIONS = "SAMEORIGIN"

PLOTLY_COMPONENTS = [
    "dpd_static_support",
    "dpd_components",
    "dash_bootstrap_components",
]

PLOTLY_DASH = {
    "ws_route": "dpd/ws/channel",
    "http_route": "dpd/views",
    "http_poke_enabled": True,
    "insert_demo_migrations": False,
    "cache_timeout_initial_arguments": 60,
    "view_decorator": None,
    "cache_arguments": False,
    "serve_locally": False,
}

STATICFILES_FINDERS = [
    "django_plotly_dash.finders.DashAssetFinder",
    "django_plotly_dash.finders.DashComponentFinder",
    "django_plotly_dash.finders.DashAppDirectoryFinder",
]


JAZZMIN_SETTINGS = {
    "topmenu_links": [
        # model admin to link to (Permissions checked against model)
        {"name": "GWDataLens", "url": "/gwdatalens", "permissions": ["auth.view_user"]},
    ]
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # needed for DASH APP
