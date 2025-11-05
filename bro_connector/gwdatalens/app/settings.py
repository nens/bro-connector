from pathlib import Path

import tomli

# %% load settings
DALALENS_APP_ROOT = Path(__file__).parent.parent
DATALENS_APP_PATH = Path(__file__).parent

with open(DATALENS_APP_PATH / "config.toml", "rb") as f:
    config = tomli.load(f)
    settings = config["settings"]

# %%
if settings["DJANGO_APP"]:
    from main import localsecret  # noqa

    # NOTE: edit for other database configurations
    config["database"] = {
        "database": localsecret.database,
        "user": localsecret.user,
        "password": localsecret.password,
        "host": localsecret.host,
        "port": localsecret.port,
    }
else:
    try:
        with open(DATALENS_APP_PATH / "database.toml", "rb") as f:
            dbase = tomli.load(f)
            config["database"] = dbase["database"]
    except FileNotFoundError:
        print(
            f"No {DATALENS_APP_PATH}/database.toml file found. "
            "Ignore this message if using HydropandasDataSource."
        )

# %% set paths accordingly

if settings["DJANGO_APP"]:
    ASSETS_PATH = Path(__file__).parent.parent.parent / "static" / "dash"
else:
    ASSETS_PATH = DATALENS_APP_PATH / ".." / "assets"

LOCALE_PATH = ASSETS_PATH / "locale"
CUSTOM_CSS_PATH = str(ASSETS_PATH / "custom.css")
MAPBOX_ACCESS_TOKEN = str(ASSETS_PATH / ".mapbox_access_token")
