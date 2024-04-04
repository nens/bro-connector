from app import app
from icecream import ic
from waitress import serve

# try:
    # from .src.cache import cache
# except ImportError:  # if running app.py directly
    # from src.cache import cache

ic.configureOutput(includeContext=True)


def run(app, debug=False, port=8050):
    if debug:
        app.run_server(debug=debug)
    else:
        ic(
            f"\nRunning QC Grondwaterstanden on http://127.0.0.1:{port}/"
            "\nPress Ctrl+C to quit."
        )
        serve(app.server, host="127.0.0.1", port=port)
    # cache.clear()


# define alias
run_dashboard = run

# set to True to run app in debug mode
DEBUG = True

# %% Run app

if __name__ == "__main__":
    if DEBUG:
        app.run_server(debug=True)
    else:
        run(app)
