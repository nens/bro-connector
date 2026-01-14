from gwdatalens.app.config import config


def get_app():
    from gwdatalens.app.app import app

    return app


def run(debug=None, port=None):
    """Run the GWDataLens application.

    Parameters
    ----------
    debug : bool, optional
        Enable debug mode. Defaults to config DEBUG setting.
    port : int, optional
        Port to run on. Defaults to config PORT setting.
    """
    if debug is None:
        debug = config.get("DEBUG")
    if port is None:
        port = config.get("PORT")

    app = get_app()
    if debug:
        app.run(debug=debug, port=port)
    else:
        from waitress import serve

        print(
            f"\nRunning QC Grondwaterstanden on http://127.0.0.1:{port}/"
            "\nPress Ctrl+C to quit."
        )
        serve(app.server, host="127.0.0.1", port=port)


# define alias
run_dashboard = run

# %% Run app

if __name__ == "__main__":
    if config.get("DEBUG"):
        app = get_app()
        app.run(debug=config.get("DEBUG"))
    else:
        run()
