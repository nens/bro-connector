from typing import List, Optional

from dash import dash_table, html
from dash.dash_table.Format import Format

from gwdatalens.app.constants import UI, ColumnNames
from gwdatalens.app.src.components import ids
from gwdatalens.app.src.components.styling import DATA_TABLE_HEADER_BGCOLOR
from gwdatalens.app.src.data.data_manager import DataManager


def render(data: DataManager, selected_data: Optional[List[int]] = None) -> html.Div:
    """Render an the piezometer overview table.

    Parameters
    ----------
    data : DataInterface
        An interface to the data source containing the required data.
    selected_data : optional
        Data that is selected, by default None.

    Returns
    -------
    html.Div
        A Dash HTML Div component containing the rendered DataTable.

    Notes
    -----
    The table displays columns ['bro_id', 'nitg_code', 'tube_number',
    'screen_top', 'screen_bot', 'x', 'y', and 'metingen']. The table supports
    native filtering and sorting, and has fixed headers with virtualization
    enabled for better performance with large datasets. The style of the table
    and its cells is customized, including conditional styling for selected
    rows.
    """
    df = data.db.gmw_gdf.copy()
    usecols = [
        ColumnNames.ID,
        ColumnNames.DISPLAY_NAME,
        ColumnNames.BRO_ID,
        ColumnNames.WELL_CODE,
        ColumnNames.TUBE_NUMBER,
        ColumnNames.SCREEN_TOP,
        ColumnNames.SCREEN_BOT,
        "x",
        "y",
        "metingen",
    ]
    return html.Div(
        id="table-div",
        children=[
            dash_table.DataTable(
                id=ids.OVERVIEW_TABLE,
                data=df.loc[:, usecols].to_dict("records"),
                columns=[
                    {
                        "id": ColumnNames.DISPLAY_NAME,
                        "name": "Putcode",
                        "type": "text",
                    },
                    {
                        "id": ColumnNames.BRO_ID,
                        "name": "BRO-ID",
                        "type": "text",
                    },
                    {
                        "id": ColumnNames.TUBE_NUMBER,
                        "name": "Filternummer",
                        "type": "numeric",
                        # "format": Format(scheme="r", precision=1),
                    },
                    {
                        "id": ColumnNames.SCREEN_TOP,
                        "name": "Bovenzijde filter\n[m NAP]",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "id": ColumnNames.SCREEN_BOT,
                        "name": "Onderzijde filter\n[m NAP]",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "id": ColumnNames.X,
                        "name": "X\n[m RD]",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=5),
                    },
                    {
                        "id": ColumnNames.Y,
                        "name": "Y\n[m RD]",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=6),
                    },
                    {
                        "id": ColumnNames.NUMBER_OF_OBSERVATIONS,
                        "name": "Metingen",
                        "type": "numeric",
                        "format": {"specifier": ".0f"},
                    },
                ],
                fixed_rows={"headers": True},
                page_action="none",
                filter_action="native",
                sort_action="native",
                style_table={
                    "height": "47cqh",
                    "maxHeight": "45cqh",
                    "overflowY": "auto",
                    "margin-top": UI.MARGIN_TOP_LARGE,
                },
                # NOTE: table will have scroll bar despite fitting on page when
                # virtualization is set to True...
                virtualization=True,
                style_cell={"whiteSpace": "pre-line", "fontSize": 12},
                style_cell_conditional=[
                    {
                        "if": {"column_id": c},
                        "textAlign": "left",
                    }
                    for c in [ColumnNames.BRO_ID, ColumnNames.DISPLAY_NAME]
                ]
                + [
                    {"if": {"column_id": ColumnNames.DISPLAY_NAME}, "width": "15%"},
                    {"if": {"column_id": ColumnNames.BRO_ID}, "width": "10%"},
                    {"if": {"column_id": ColumnNames.TUBE_NUMBER}, "width": "10%"},
                    {"if": {"column_id": ColumnNames.SCREEN_TOP}, "width": "15%"},
                    {"if": {"column_id": ColumnNames.SCREEN_BOT}, "width": "15%"},
                    {"if": {"column_id": ColumnNames.X}, "width": "7.5%"},
                    {"if": {"column_id": ColumnNames.Y}, "width": "7.5%"},
                    {
                        "if": {"column_id": ColumnNames.NUMBER_OF_OBSERVATIONS},
                        "width": "10%",
                    },
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
            ),
        ],
        className="dbc dbc-row-selectable",
    )
