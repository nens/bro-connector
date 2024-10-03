from gwdatalens.app.callbacks.general import register_general_callbacks
from gwdatalens.app.callbacks.models import register_model_callbacks
from gwdatalens.app.callbacks.overview import register_overview_callbacks
from gwdatalens.app.callbacks.qc import register_qc_callbacks
from gwdatalens.app.callbacks.result import register_result_callbacks


def register_callbacks(app, data):
    """Register all the necessary callbacks for the application.

    This function registers various callback functions to the provided app instance.
    It organizes the registration into several categories: general, overview, model,
    quality control (QC), and result callbacks.

    Parameters
    ----------
    app : object
        The application instance to which the callbacks will be registered.
    data : object
        The data interface that will be used by the callbacks.
    """
    register_general_callbacks(app, data)
    register_overview_callbacks(app, data)
    register_model_callbacks(app, data)
    register_qc_callbacks(app, data)
    register_result_callbacks(app, data)
