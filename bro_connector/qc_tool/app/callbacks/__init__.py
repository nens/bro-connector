from .general import register_general_callbacks
from .models import register_model_callbacks
from .overview import register_overview_callbacks
from .qc import register_qc_callbacks
from .result import register_result_callbacks


def register_callbacks(app, data):
    register_general_callbacks(app, data)
    register_overview_callbacks(app, data)
    register_model_callbacks(app, data)
    register_qc_callbacks(app, data)
    register_result_callbacks(app, data)
