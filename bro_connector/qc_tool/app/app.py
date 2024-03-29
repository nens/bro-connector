import logging
import os

import dash_bootstrap_components as dbc
import i18n
import pastastore as pst

# from dash import CeleryManager, Dash, DiskcacheManager
from django_plotly_dash import DjangoDash

try:
    from .callbacks import register_callbacks

    # from .src.cache import cache
    from .src.components.layout import create_layout
    from .src.data.source import DataInterface, DataSource, TravalInterface
except ImportError:  # if running app.py directly
    from callbacks import register_callbacks

    # from src.cache import cache
    from src.components.layout import create_layout
    from src.data.source import DataInterface, DataSource, TravalInterface

logger = logging.getLogger("waitress")
logger.setLevel(logging.ERROR)

# %% set some variables
external_stylesheets = [
    dbc.themes.FLATLY,
    "https://use.fontawesome.com/releases/v6.5.1/css/all.css",
]

# %% main app

# %% set the locale and load the translations
LOCALE = "nl"

i18n.set("locale", LOCALE)
i18n.load_path.append(os.path.join(os.path.dirname(__file__), "locale"))

# %% Set up backend

# connect to the database
db = DataSource()
# data = DataSourceHydropandas(fname="obs_collection_dino.pickle")

# load pastastore
# name = "zeeland"
name = "zeeland_bro"
conn = pst.ArcticDBConnector(
    name=name, uri="lmdb:///home/david/github/gws_qc/traval_scripts/pastasdb/"
)
# conn = pst.PasConnector(
#     name=name, path="/home/david/github/gws_qc/pastas_db/"
# )


pstore = pst.PastaStore(conn)
print(pstore)

# load ruleset
traval_interface = TravalInterface(db, pstore)

# add all components to our data interface object
data = DataInterface(db=db, pstore=pstore, traval=traval_interface)

# %%

# if "REDIS_URL" in os.environ:
#     # Use Redis & Celery if REDIS_URL set as an env variable
#     from celery import Celery

#     celery_app = Celery(
#         __name__,
#         broker=os.environ["REDIS_URL"],
#         backend=os.environ["REDIS_URL"],
#     )
#     background_callback_manager = CeleryManager(celery_app)

# else:
#     # Diskcache for non-production apps when developing locally
#     import diskcache

#     callback_cache = diskcache.Cache("./.cache")
#     background_callback_manager = DiskcacheManager(callback_cache)

# %% build app

# create app
app = DjangoDash(
    "QCTool",
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,
    add_bootstrap_links=True,
    # background_callback_manager=background_callback_manager,
)
app.title = i18n.t("general.app_title")
app.layout = create_layout(app, data)
app.css.append_css({ "external_url" : "/static/dash/custom.css" })

# register callbacks
register_callbacks(app, data)

# # initialize cache
# cache.init_app(
#     app.server,
#     config={
#         "CACHE_TYPE": "filesystem",
#         "CACHE_DIR": ".cache",
#     },
# )
