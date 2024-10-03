from dash import dash_table, html
from dash.dash_table.Format import Format

from ..data.interface import DataInterface
from . import ids
from .styling import DATA_TABLE_HEADER_BGCOLOR


def render(data: DataInterface, selected_data=None):
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
    df = data.db.gmw_gdf.reset_index()
    usecols = [
        "id",
        "bro_id",
        "nitg_code",
        "tube_number",
        "screen_top",
        "screen_bot",
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
                        "id": "bro_id",
                        "name": "Naam",
                        "type": "text",
                    },
                    {
                        "id": "nitg_code",
                        "name": "NITG",
                        "type": "text",
                    },
                    {
                        "id": "tube_number",
                        "name": "Filternummer",
                        "type": "numeric",
                        # "format": Format(scheme="r", precision=1),
                    },
                    {
                        "id": "screen_top",
                        "name": "Bovenzijde filter\n[m NAP]",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "id": "screen_bot",
                        "name": "Onderzijde filter\n[m NAP]",
                        "type": "numeric",
                        "format": {"specifier": ".2f"},
                    },
                    {
                        "id": "x",
                        "name": "X\n[m RD]",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=5),
                    },
                    {
                        "id": "y",
                        "name": "Y\n[m RD]",
                        "type": "numeric",
                        "format": Format(scheme="r", precision=6),
                    },
                    {
                        "id": "metingen",
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
                    "height": "45vh",
                    # "overflowY": "auto",
                    "margin-top": 15,
                },
                # row_selectable="multi",
                virtualization=True,
                style_cell={"whiteSpace": "pre-line", "fontSize": 12},
                style_cell_conditional=[
                    {
                        "if": {"column_id": c},
                        "textAlign": "left",
                    }
                    for c in ["bro_id"]
                ]
                + [
                    {"if": {"column_id": "bro_id"}, "width": "15%"},
                    {"if": {"column_id": "nitg_code"}, "width": "10%"},
                    {"if": {"column_id": "tube_number"}, "width": "10%"},
                    {"if": {"column_id": "screen_top"}, "width": "15%"},
                    {"if": {"column_id": "screen_bot"}, "width": "15%"},
                    {"if": {"column_id": "x"}, "width": "7.5%"},
                    {"if": {"column_id": "y"}, "width": "7.5%"},
                    {"if": {"column_id": "metingen"}, "width": "10%"},
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
