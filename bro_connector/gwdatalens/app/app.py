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
    PastaStoreDataSource,
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


def _create_pastastore_from_config() -> pst.PastaStore:
    """Create PastaStore from config with safe fallback to DictConnector."""
    pst_cfg = config.get("pastastore")
    name = pst_cfg["name"]
    pastastore_path = Path(pst_cfg["path"])
    connector_type = pst_cfg.get("connector", "dict")

    try:
        if name.endswith(".zip"):
            return pst.PastaStore.from_zip(pastastore_path / name)

        if connector_type == "arcticdb":
            conn = pst.ArcticDBConnector(name=name, uri=f"lmdb://{pastastore_path}")
        elif connector_type == "pas":
            conn = pst.PasConnector(name=name, path=pastastore_path)
        elif connector_type == "dict":
            conn = pst.DictConnector(name=name)
        else:
            raise ValueError(f"Unknown connector type '{connector_type}'")

        store = pst.PastaStore(conn)
        logger.info(store)
        return store
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as e:
        logger.warning(
            "Failed to initialize configured pastastore (%s). Falling back to "
            "in-memory DictConnector PastaStore. Error: %s",
            connector_type,
            e,
        )
        return pst.PastaStore(pst.DictConnector(name="runtime"))


def _create_startup_pastastore_from_extent(extent: list[float]) -> pst.PastaStore:
    """Create in-memory PastaStore from BRO data within EPSG:28992 extent."""
    import hydropandas as hpd

    xmin, xmax, ymin, ymax = [float(v) for v in extent]
    extent_28992 = [xmin, xmax, ymin, ymax]

    logger.info(
        "Bootstrapping startup data from BRO extent EPSG:28992: %s",
        extent_28992,
    )
    oc = hpd.read_bro(extent=extent_28992, epsg=28992)
    conn = pst.DictConnector(name="startup_bro")
    startup_pstore = oc.to_pastastore(conn=conn, pstore_name="startup_bro")
    logger.info(
        "Startup BRO extent load completed. Pastastore '%s' contains %s oseries.",
        startup_pstore.name,
        len(startup_pstore.oseries),
    )
    return startup_pstore


# %% Connect to database

data_backend = str(config.get("DATA_BACKEND", "postgresql")).lower()
startup_extent = config.get("EXTENT")

# %%
if startup_extent is not None:
    pstore = _create_startup_pastastore_from_extent(startup_extent)
    db = PastaStoreDataSource(pstore=pstore)
elif data_backend == "postgresql":
    db = PostgreSQLDataSource(
        config=config.get_database_config(),
        use_cache=config.get("USE_LRU_CACHE"),
        max_cache_size=config.get("MAX_CACHE_SIZE"),
        cache_timeout=config.get("CACHE_TIMEOUT"),
    )
    pstore = _create_pastastore_from_config()
elif data_backend == "pastastore":
    pstore = _create_pastastore_from_config()
    db = PastaStoreDataSource(pstore=pstore)
else:
    raise ValueError(
        f"Unknown DATA_BACKEND '{data_backend}'. Expected one of: postgresql, pastastore"
    )

# update KNMI time series
pastastore_config = config.get("pastastore")
if pastastore_config["update_knmi"] and not pstore.empty and startup_extent is None:
    from pastastore.extensions import activate_hydropandas_extension  # noqa: I001

    activate_hydropandas_extension()
    # update to yesterday
    tmax = pd.Timestamp.today().normalize() - pd.Timedelta(days=1)
    pstore.hpd.update_knmi_meteo(tmax=tmax)
elif pastastore_config["update_knmi"] and startup_extent is not None:
    logger.info(
        "Skipping startup KNMI bulk update for extent bootstrap; "
        "KNMI data will be downloaded on-demand during modeling."
    )


# %% traval interface

qc = QCCoordinator(data_source=db)

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
