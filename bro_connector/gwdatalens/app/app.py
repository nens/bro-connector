# %%
import logging
import os
from pathlib import Path

import dash_bootstrap_components as dbc
import i18n
import pandas as pd
import pastastore as pst
from dash import CeleryManager, Dash, DiskcacheManager

from gwdatalens.app.callbacks import register_callbacks
from gwdatalens.app.config import config
from gwdatalens.app.messages import t_
from gwdatalens.app.paths import CUSTOM_CSS_PATH, LOCALE_PATH
from gwdatalens.app.src.cache import cache
from gwdatalens.app.src.components.layout import create_layout
from gwdatalens.app.src.data import (
    DataManager,
    # HydropandasDataSource,
    PostgreSQLDataSource,
    QCCoordinator,
)

logger = logging.getLogger("gwdatalens")
logger.setLevel(config.get("LOG_LEVEL"))

# Load Django database configuration if applicable
if config.get("DJANGO_APP"):
    try:
        from main import localsecret  # noqa

        config.update_database_from_django(localsecret)
        logger.info("Loaded database configuration from Django")
    except ImportError:
        logger.error("DJANGO_APP=True but 'main.localsecret' not available")

# %% set some variables
external_stylesheets = [
    dbc.themes.FLATLY,
    "https://use.fontawesome.com/releases/v6.5.1/css/all.css",
]

# %% main app

# set the locale and load the translations
i18n.set("locale", config.get("LOCALE"))
i18n.load_path.append(LOCALE_PATH)

# %% Connect to database

# postgreql database
db = PostgreSQLDataSource(config=config.get_database_config())

# hydropandas 'database'
# db = HydropandasDataSource(extent=[116500, 120000, 439000, 442000], source="bro")
# db = HydropandasDataSource(
#     fname=Path(__file__).parent / ".." / "data" / "example_obscollection.zip",
#     source="bro",
# )

# %% load pastastore
pastastore_config = config.get("pastastore")
name = pastastore_config["name"]
pastastore_path = Path(pastastore_config["path"])

if name.endswith(".zip"):
    pstore = pst.PastaStore.from_zip(pastastore_path / name)
else:
    connector_type = pastastore_config["connector"]
    if connector_type == "arcticdb":
        conn = pst.ArcticDBConnector(name=name, uri=f"lmdb://{pastastore_path}")
    elif connector_type == "pas":
        conn = pst.PasConnector(name=name, path=pastastore_path)
    else:
        raise ValueError(f"Unknown connector type '{connector_type}'")
    pstore = pst.PastaStore(conn)
    logger.info(pstore)

# update KNMI time series
if pastastore_config["update_knmi"] and not pstore.empty:
    from pastastore.extensions import activate_hydropandas_extension  # noqa: I001

    activate_hydropandas_extension()
    # update to yesterday
    tmax = pd.Timestamp.today().normalize() - pd.Timedelta(days=1)
    pstore.hpd.update_knmi_meteo(tmax=tmax)


# %% traval interface

qc = QCCoordinator(data_source=db, pastastore=pstore)

# %%
# add all components to our data manager object
data = DataManager(db=db, pastastore=pstore, qc=qc)

# %% background callbacks (for cancelling workflows)
# NOTE: still some difficulty remaining with database engine with multiple processes,
# causing performance issues. It is currently recommended to not use background
# callbacks.

if config.get("BACKGROUND_CALLBACKS"):
    msg = (
        "It is currently recommended to not use background callbacks due to "
        "performance issues caused by running the database engine in multiple "
        "processes."
    )
    logger.warning(msg)
    if "REDIS_URL" in os.environ:
        # Use Redis & Celery if REDIS_URL set as an env variable
        from celery import Celery

        celery_app = Celery(
            __name__,
            broker=os.environ["REDIS_URL"],
            backend=os.environ["REDIS_URL"],
        )
        background_callback_manager = CeleryManager(celery_app)

    else:
        # Diskcache for non-production apps when developing locally
        import diskcache

        callback_cache = diskcache.Cache("./.cache")
        background_callback_manager = DiskcacheManager(callback_cache)
else:
    background_callback_manager = None

# %% build app


if config.get("DJANGO_APP"):
    from django.conf import settings as django_settings  # noqa
    from django_plotly_dash import DjangoDash  # noqa

    # create app
    app = DjangoDash(
        "gwdatalens",
        external_stylesheets=external_stylesheets,
        external_scripts=[
            {"src": django_settings.STATIC_URL + "dash/custom_scripts.js"},
        ],
        suppress_callback_exceptions=True,
        add_bootstrap_links=True,
        background_callback_manager=background_callback_manager,
    )
    app.title = t_("general.app_title")
    app.layout = create_layout(app, data)
    app.css.append_css(
        {
            "external_url": [
                django_settings.STATIC_URL + "dash/custom.css",
            ]
        }
    )

    # register callbacks
    register_callbacks(app, data)
else:
    # create app
    app = Dash(
        "gwdatalens",
        external_stylesheets=external_stylesheets + [CUSTOM_CSS_PATH],
        suppress_callback_exceptions=True,
        background_callback_manager=background_callback_manager,
        compress=True,
    )
    app.title = t_("general.app_title")
    app.layout = create_layout(app, data)

    # register callbacks
    register_callbacks(app, data)

    # initialize cache
    cache.init_app(
        app.server,
        config={
            "CACHE_TYPE": "filesystem",
            "CACHE_DIR": ".cache",
        },
    )
