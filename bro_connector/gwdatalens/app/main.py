from gwdatalens.app.settings import settings


def get_app():
    try:
        from gwdatalens.app.app import app
    except ImportError:
        from app.app import app
    return app


def run(debug=settings["DEBUG"], port=settings["PORT"]):
    app = get_app()
    if debug:
        app.run_server(debug=debug, port=port)
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
    if settings["DEBUG"]:
        app = get_app()
        app.run_server(debug=settings["DEBUG"])
    else:
        run()
