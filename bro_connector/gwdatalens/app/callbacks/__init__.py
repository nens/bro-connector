from gwdatalens.app.callbacks.general import register_general_callbacks
from gwdatalens.app.callbacks.models import register_model_callbacks
from gwdatalens.app.callbacks.overview import register_overview_callbacks
from gwdatalens.app.callbacks.qc import register_qc_callbacks
from gwdatalens.app.callbacks.result import register_result_callbacks


def register_callbacks(app, data):
    register_general_callbacks(app, data)
    register_overview_callbacks(app, data)
    register_model_callbacks(app, data)
    register_qc_callbacks(app, data)
    register_result_callbacks(app, data)
