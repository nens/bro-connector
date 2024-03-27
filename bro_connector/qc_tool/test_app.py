import logging
import os

import dash_bootstrap_components as dbc
import i18n
import pastastore as pst
from .callbacks import register_callbacks
from dash import CeleryManager, Dash, DiskcacheManager
from django_plotly_dash import DjangoDash

from .src.cache import cache
from .src.components.layout import create_layout
from .src.data.source import DataInterface,  DataSource, TravalInterface

from django.apps import AppConfig



logger = logging.getLogger("waitress")
logger.setLevel(logging.ERROR)

# %% set some variables
external_stylesheets = [
    dbc.themes.FLATLY,
    "https://use.fontawesome.com/releases/v6.5.1/css/all.css",
]

# %% main app

# %% set the locale and load the translations
LOCALE = "en"

i18n.set("locale", LOCALE)
i18n.load_path.append("locale")

# %% Set up backend

# connect to the database
db = DataSource()
# data = DataSourceHydropandas(fname="obs_collection_dino.pickle")

# load pastastore
# name = "zeeland"
name = "zeeland_bro"
conn = pst.ArcticDBConnector(name=name, uri="lmdb://../../traval_scripts/pastasdb/")
pstore = pst.PastaStore(conn)
print(pstore)

# load ruleset
traval_interface = TravalInterface(db, pstore)

# add all components to our data interface object
data = DataInterface(db=db, pstore=pstore, traval=traval_interface)

# %%

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

# %% build app

app = DjangoDash('QCTool')

app.title = i18n.t("general.app_title")
app.layout = create_layout(app, data)

# register callbacks
register_callbacks(app, data)