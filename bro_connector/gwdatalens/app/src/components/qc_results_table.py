from typing import Any

import pandas as pd
from dash import dash_table, html
from dash.dash_table.Format import Format

from gwdatalens.app.constants import ColumnNames
from gwdatalens.app.messages import t_
from gwdatalens.app.src.components import ids
from gwdatalens.app.src.components.styling import DATA_TABLE_HEADER_BGCOLOR
from gwdatalens.app.src.data.qc_definitions import qc_categories


def render(data: Any) -> html.Div:
    """Render the QC results table.

    Parameters
    ----------
    data : object
        An object containing the data to be rendered. It is expected to have a
        `traval` attribute with a `traval_result` DataFrame.

    Returns
    -------
    html.Div
        A Dash HTML Div component containing the QC results table.

    Notes
    -----
    - If `data.qc.traval_result` is None, an empty DataFrame is used.
    - The table includes columns for [datetime, values, comments, incoming QC status,
      update QC status, category].
    - The table supports native filtering and virtualization for performance.
    """
    if data.qc.traval_result is None:
        columns = [
            ColumnNames.ID,
            ColumnNames.VALUE,
            ColumnNames.COMMENT,
            ColumnNames.STATUS_QUALITY_CONTROL,
            ColumnNames.CATEGORY,
        ]
        df = pd.DataFrame(columns=columns)
        df.index.name = ColumnNames.DATETIME
        df = df.reset_index(names=ColumnNames.DATETIME)
        df_records = df.to_dict("records")
    else:
        df = data.qc.traval_result.copy()
        df_records = df.reset_index(names="datetime").to_dict("records")

    options = [
        {"label": v + f" ({k})", "value": v + f"({k})"}
        for k, v in qc_categories.items()
    ]
    # options = [{"label": t_("general.clear_qc_label"), "value": ""}] + options

    return html.Div(
        id="qc-table-div",
        children=[
            dash_table.DataTable(
                id=ids.QC_RESULT_TABLE,
                data=df_records,
                columns=[
                    {
                        "id": ColumnNames.DATETIME,
                        "name": t_("general.datetime"),
                        "type": "text",
                        "editable": False,
                    },
                    {
                        "id": ColumnNames.VALUE,
                        "name": t_("general.observations"),
                        "type": "numeric",
                        "format": Format(scheme="r", precision=5),
                        "editable": False,
                    },
                    {
                        "id": ColumnNames.COMMENT,
                        "name": t_("general.comment"),
                        "type": "text",
                        "editable": False,
                    },
                    {
                        "id": ColumnNames.INCOMING_STATUS_QUALITY_CONTROL,
                        "name": "Incoming QC Status",
                        "type": "text",
                        "editable": False,
                        # "on_change": {"action": "validate", "failure": "accept"},
                        # "validation": {"default": 1},
                    },
                    {
                        "id": ColumnNames.STATUS_QUALITY_CONTROL,
                        "name": "Update QC Status",
                        "type": "text",
                        "editable": False,
                        # "on_change": {"action": "validate", "failure": "accept"},
                        # "validation": {"default": 1},
                    },
                    {
                        "id": ColumnNames.CATEGORY,
                        "name": t_("general.qc_label"),
                        "editable": False,
                        "type": "text",
                        "presentation": "dropdown",
                    },
                ],
                editable=False,
                fixed_rows={"headers": True},
                dropdown={"category": {"options": options}},
                page_action="none",
                filter_action="native",
                filter_query='{comment} != ""',
                virtualization=True,  # NOTE: this causes clipping of the last row
                style_table={
                    "height": "35cqh",
                    "maxHeight": "35cqh",
                    "overflowY": "auto",
                },
                # row_selectable="multi",
                style_cell={"whiteSpace": "pre-line", "fontSize": 12},
                style_cell_conditional=[
                    {
                        "if": {"column_id": c},
                        "textAlign": "left",
                    }
                    for c in ["datetime", "comment"]
                ]
                + [
                    {"if": {"column_id": "datetime"}, "width": "16.5%"},
                    {"if": {"column_id": "values"}, "width": "16.5%"},
                    {"if": {"column_id": "comment"}, "width": "16.5%"},
                    {
                        "if": {"column_id": "incoming_status_quality_control"},
                        "width": "16.5%",
                    },
                    {"if": {"column_id": "status_quality_control"}, "width": "16.5%"},
                    {"if": {"column_id": "category"}, "width": "16.5%"},
                ],
                style_data_conditional=[
                    {
                        "if": {"state": "selected"},  # 'active' | 'selected'
                        "border": "1px solid #006f92",
                    },
                ],
                style_header={
                    "backgroundColor": DATA_TABLE_HEADER_BGCOLOR,
                    "fontWeight": "bold",
                },
                style_header_conditional=[
                    {
                        "if": {"column_id": ["status_quality_control", "category"]},
                        "textDecoration": "underline",
                        "textDecorationStyle": "dotted",
                    }
                ],
                tooltip_header={
                    "incoming_status_quality_control": {
                        # "use_with": "both",
                        "type": "markdown",
                        "value": t_("general.incoming_qc_status"),
                    },
                    "status_quality_control": {
                        # "use_with": "both",
                        "type": "markdown",
                        "value": t_("general.qc_status"),
                    },
                    "category": {
                        # "use_with": "both",
                        "type": "markdown",
                        "value": t_("general.category"),
                    },
                },
            ),
        ],
        className="dbc dbc-row-selectable",
    )
