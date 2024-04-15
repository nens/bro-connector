import datetime
import logging

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import pytz
from dash import dcc, html
from dash.dependencies import Input, Output, State
from django.shortcuts import get_object_or_404
from django_plotly_dash import DjangoDash
from plotly.subplots import make_subplots

from gmw.models import (
    ElectrodeStatic,
    GroundwaterMonitoringTubeDynamic,
    GroundwaterMonitoringTubeStatic,
    GeoOhmCable,
    GroundwaterMonitoringWellDynamic,
    GroundwaterMonitoringWellStatic,
    Event,
)

logger = logging.getLogger(__name__)


def convert_event_date_str_to_datetime(event_date: str) -> datetime.datetime:
    try:
        date = datetime.datetime.strptime(event_date,'%Y-%m-%d')
    except ValueError:
        date = datetime.datetime.strptime(event_date,'%Y')
    except TypeError:
        date = datetime.datetime.strptime("1900-01-01",'%Y-%m-%d')

    return date

def datetime_convert(gmt_datetime: str) -> datetime.date:
    date = convert_event_date_str_to_datetime(gmt_datetime)
    return date.astimezone().date()

def gen_gebeurtenis(event):
    if event["constructie"]:
        return "Inrichting"
    else:
        gebeurtenis = ""
        for werkzaamheid_id in range(len(event["onderhoud"])):
            gebeurtenis += event["onderhoud"][werkzaamheid_id]
            if werkzaamheid_id != len(event["onderhoud"]) - 1:
                gebeurtenis += ", "
        return gebeurtenis


def transform_electrodedata_to_df(electrodedata):
    if len(electrodedata) == 0:
        electrode_dataframe = pd.DataFrame(
            columns=["filter", "kabel", "elektrode", "positie"]
        )
    else:
        electrode_dataframe = pd.DataFrame(electrodedata)
    return electrode_dataframe


def transform_putdata_to_df(putdata):
    columns = [
        "datum",
        "gebeurtenis",
        "maaiveldhoogte",
        "filternummer",
        "bovenkant buis",
        "bovenkant filter",
        "onderkant filter",
        "onderkant buis",
        "bovenkant ingeplaatst deel",
        "onderkant ingeplaatst deel",
        "lengte ingeplaatst deel",
        "diepte meetinstrument",
        "beschermconstructie",
    ]

    df = pd.DataFrame(columns=columns)

    event = putdata
    for i in range(len(event["filters"])):
        row = dict.fromkeys(columns)
        row["datum"] = event["date"]
        row["beschermconstructie"] = event["filters"][i]["beschermconstructie"]
        row["gebeurtenis"] = gen_gebeurtenis(event)
        row["maaiveldhoogte"] = event["put"]["maaiveld"]
        row["filternummer"] = event["filters"][i]["nummer"]
        row["bovenkant buis"] = event["filters"][i]["bovenkant buis"]
        row["onderkant buis"] = event["filters"][i]["onderkant buis"]
        row["bovenkant filter"] = event["filters"][i]["bovenkant filter"]
        row["onderkant filter"] = event["filters"][i]["onderkant filter"]
        row["diepte meetinstrument"] = event["filters"][i]["diepte meetinstrument"]
        row["bovenkant ingeplaatst deel"] = np.nan
        if "onderkant zandvang" in event["filters"][i].keys():
            row["bovenkant zandvang"] = event["filters"][i]["onderkant filter"]
            row["onderkant zandvang"] = event["filters"][i]["onderkant zandvang"]
        else:
            row["bovenkant zandvang"] = np.nan
            row["onderkant zandvang"] = np.nan

        if (
            "bovenkant ingeplaatst deel" in event["filters"][i].keys()
            and "lengte ingeplaatst deel" in event["filters"][i]
        ):
            row["bovenkant ingeplaatst deel"] = event["filters"][i][
                "bovenkant ingeplaatst deel"
            ]
            row["onderkant ingeplaatst deel"] = (
                event["filters"][i]["bovenkant ingeplaatst deel"]
                - event["filters"][i]["lengte ingeplaatst deel"]
            )

            row["lengte ingeplaatst deel"] = event["filters"][i][
                "lengte ingeplaatst deel"
            ]
        else:
            row["bovenkant ingeplaatst deel"] = np.nan
            row["onderkant ingeplaatst deel"] = np.nan
            row["lengte ingeplaatst deel"] = np.nan

        df.loc[df.shape[0]] = row
    return df


def generate_graph(selection, selection_electrode, event, options, referentie):
    try:
        if referentie == "m t.o.v. mv":
            selection["meetinstrumentsdiepte"] = selection["meetinstrumentsdiepte"]
            selection["bovenkant buis"] = (
                selection["bovenkant buis"] - selection["maaiveldhoogte"].values[0]
            )
            selection["bovenkant buis"] = selection["bovenkant buis"].round(3)
            selection["bovenkant filter"] = (
                selection["bovenkant filter"] - selection["maaiveldhoogte"].values[0]
            )
            selection["bovenkant filter"] = selection["bovenkant filter"].round(3)
            selection["onderkant filter"] = (
                selection["onderkant filter"] - selection["maaiveldhoogte"].values[0]
            )
            selection["onderkant filter"] = selection["onderkant filter"].round(3)
            selection["onderkant buis"] = (
                selection["onderkant buis"] - selection["maaiveldhoogte"].values[0]
            )
            selection["onderkant buis"] = selection["onderkant buis"].round(3)
            try:
                selection["bovenkant ingeplaatst deel"] = (
                    selection["bovenkant ingeplaatst deel"]
                    - selection["maaiveldhoogte"].values[0]
                )
                selection["bovenkant ingeplaatst deel"] = selection[
                    "bovenkant ingeplaatst deel"
                ].round(3)
                selection["onderkant ingeplaatst deel"] = (
                    selection["onderkant ingeplaatst deel"]
                    - selection["maaiveldhoogte"].values[0]
                )
                selection["onderkant ingeplaatst deel"] = selection[
                    "onderkant ingeplaatst deel"
                ].round(3)
            except:  # noqa: E722
                logger.exception("Bare except")
                pass

            selection["positie meetinstrument"] = (
                selection["positie meetinstrument"]
                - selection["maaiveldhoogte"].values[0]
            )
            selection["positie meetinstrument"] = selection[
                "positie meetinstrument"
            ].round(3)


            try:
                selection_electrode["positie"] = (
                    selection_electrode["positie"]
                    - selection["maaiveldhoogte"].values[0]
                )
                selection_electrode["positie"] = selection_electrode["positie"].round(3)
            except:  # noqa: E722
                logger.exception("Bare except")
                pass

            selection["maaiveldhoogte"] = (
                selection["maaiveldhoogte"] - selection["maaiveldhoogte"].values[0]
            )
            selection["maaiveldhoogte"] = selection["maaiveldhoogte"].round(3)

        event = options[event]["label"]

        width_original = 0.15
        width_ingeplaatst = 0.1

        # Voorbeeldgegevens: startpunten en hoogtes van de bars
        startpunten = list(selection["startpunten"].values)

        flter = list(selection["filter"].values)
        print("FILTER: ", flter)
        stijgbuis = list(selection["stijgbuis"].values)
        ingeplaatst_deel = list(selection["ingeplaatst deel"].values)
        ok_filter = list(selection["onderkant filter"].astype(str).values)
        bk_filter = list(selection["bovenkant filter"].astype(str).values)
        bk_stijgbuis = list(selection["bovenkant buis"].astype(str).values)
        ok_stijgbuis = list(selection["onderkant buis"].astype(str).values)
        try:
            bk_ingeplaatst_deel = list(selection["bovenkant ingeplaatst deel"].values)
            ok_ingeplaatst_deel = list(selection["onderkant ingeplaatst deel"].values)
        except:  # noqa: E722
            logger.exception("Bare except")
            pass

        # Plot maaiveldhoogte (deze lijn dient alleen voor weergave label, de
        # echte volgt nog)
        maaiveld_x = np.linspace(0, len(startpunten) + 1, 100 * len(startpunten))
        maaiveld_y = [selection["maaiveldhoogte"].values[0] for _ in maaiveld_x]

        if referentie == "m t.o.v. mv":
            name = 'Maaiveld (als referentiehoogte)'
        else:
            name="Maaiveld - t.o.v. mNAP"

        mv = go.Scatter(
            x=maaiveld_x,
            y=maaiveld_y,
            showlegend=False,
            name=name,
            mode="lines",
            opacity=0.0,
            customdata=np.transpose([maaiveld_y]),
            line=dict(color="green", width=2),
        )

        print("NOT SCATTER")

        buis = go.Bar(
            x=list(range(1, len(startpunten) + 3)),
            y=stijgbuis,
            base=ok_stijgbuis,
            # Voor de spraakverwarring: onderkant buis is ook echt de
            # onderkant van de buis, daarom "stijbuis" i.p.v. "stijbuisdeel"
            name="stijgbuis",
            marker=dict(color="#8c8c8c", line=dict(color="black")),
            customdata=np.transpose([stijgbuis, bk_stijgbuis, ok_stijgbuis]),
            hovertext=bk_stijgbuis,
            width=width_original,
            hovertemplate="<br>".join(
                [
                    f"Bovenkant buis ({referentie})" + ": %{customdata[1]}",
                    f"Onderkant buis ({referentie})" + ": %{customdata[2]}",
                    "Diepte buis tov bovenkant peilbuis (m): %{customdata[0]}",
                ]
            ),
        )
        
        print("NOT BUIS")


        filter = go.Bar(
            x=list(range(1, len(startpunten) + 3)),
            y=flter,
            base=ok_filter,  # Startpunten van component 2
            name="filter",
            marker=dict(
                color="#abaaa9", line=dict(color="black")
            ),  # Kleur van component 2
            width=width_original,
            marker_pattern_shape=["|" for _ in range(len(ok_filter))],
            customdata=np.transpose(
                [
                    flter,
                    bk_filter,
                    ok_filter,
                ]
            ),
            hovertemplate="<br>".join(
                [
                    f"Bovenkant filter ({referentie})" + ": %{customdata[1]}",
                    f"Onderkant filter ({referentie})" + ": %{customdata[2]}",
                    "Lengte (m): %{customdata[0]}",
                ]
            ),
        )

        print("NOT FILTER")

        try:
            ingeplaatst_deel = go.Bar(
                x=list(range(1, len(startpunten) + 3)),
                y=ingeplaatst_deel,
                base=ok_ingeplaatst_deel,  # Startpunten van component 3
                name="ingeplaatst deel",
                marker=dict(
                    color="#abaaa9", line=dict(color="#8c8c8c")
                ),  # Kleur van component 3
                customdata=np.transpose([ingeplaatst_deel, bk_ingeplaatst_deel]),
                hovertext=bk_stijgbuis,
                width=width_ingeplaatst,
                hovertemplate="<br>".join(
                    [
                        f"Bovenkant ingeplaatst deel ({referentie})"
                        + ": %{customdata[1]}",
                        "Lengte (m): %{customdata[0]}",
                    ]
                ),
            )
        except:  # noqa: E722
            logger.exception("Bare except, hierdoor bestaat ingeplaatst_deel niet")
            ingeplaatst_deel = None
            pass
        
        print("NOT INGEPLAATST DEEL")
        

        # Maak een lijst met de traces
        barchart = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=False,
            vertical_spacing=0.03,
            specs=[
                [{"type": "scatter"}],
                [{"type": "table"}],
            ],
        )

        print("NOT SUBPLOTS")

        barchart.update_layout(
            title_text=f"{selection['gmw'].values[0]} - {event}",
            title_x=0.5,
        )
        if ingeplaatst_deel:
            for scatter in [mv, buis, filter, ingeplaatst_deel]:
                barchart.add_trace(scatter, row=1, col=1)
                # barchart = go.Figure(data=[mv, buis, filter, ingeplaatst_deel])
        else:
            for scatter in [mv, buis, filter]:
                barchart.add_trace(scatter, row=1, col=1)
        if len(selection_electrode) != 0:
            for i in range(len(selection_electrode["kabel"].unique())):
                subselection = selection_electrode[
                    selection_electrode["kabel"] == i + 1
                ]

                barchart.add_trace(
                    go.Scatter(
                        x=subselection["x"],
                        y=subselection["positie"],
                        mode="markers",
                        name=f"elektr. kabel {str(i+1)}",
                        customdata=np.transpose(
                            [
                                subselection["elektrode"].values,
                                subselection["positie"].values,
                            ]
                        ),
                        hovertemplate="<br>".join(
                            [
                                "Elektrodenummer: %{customdata[0]}",
                                f"Positie ({referentie})" + ": %{customdata[1]}",
                            ]
                        ),
                    ),
                    row=1,
                    col=1,
                )

        print("NOT TRACES 1")


        barchart.update_traces(
            marker=dict(
                size=8,
                symbol="arrow-bar-left",
                line=dict(width=2, color="DarkSlateGrey"),
            ),
            selector=dict(mode="markers"),
        )

        print("NOT TRACES 2")


        # Voeg een gekleurd vak op de achtergrond toe
        y_position = selection["maaiveldhoogte"].values[
            0
        ]  # Y-positie waar het gekleurde vak begint
        y_bottom = (
            -10000
        )  # Y-positie waar het gekleurde vak eindigt (onderkant van de grafiek)

        barchart.add_shape(
            go.layout.Shape(
                type="rect",
                x0=0,  # Begin op de x-as
                x1=len(startpunten) + 1,  # Eindig op de x-as
                y0=y_position,  # Begin op de opgegeven y-positie
                y1=y_bottom,  # Eindig op de opgegeven y-positie
                fillcolor="#f58807",  # Kleur van het vak (aardtint)
                opacity=0.25,  # Doorzichtigheid van het vak
                name="Maaiveld",
                layer="below",  # Plaats het vak onder de grafiek
                line=dict(width=0),  # Lijndikte van het vak
            ),
            row=1,
            col=1,
        )

        # Voeg hieronder de daadwerkelijke lijn voor de maaiveldhoogte toe
        barchart.add_shape(
            go.layout.Shape(
                type="line",
                x0=0,
                x1=len(startpunten) + 1,
                y0=y_position,
                y1=y_position,
                line=dict(color="green", width=2),
                layer="below",
            ),
            row=1,
            col=1,
        )

        barchart.add_shape(
            type="line",
            x0=0,  # Set the starting x-coordinate (can be adjusted based on your data range)
            x1=len(startpunten)
            + 1,  # Set the ending x-coordinate (can be adjusted based on your data range)
            y0=0,  # Set the y-coordinate for the horizontal line
            y1=0,  # Set the y-coordinate for the horizontal line
            line=dict(
                color="black", width=1, dash="dash"
            ),  # Customize line color, width, and style
            row=1,
            col=1,  # Make sure to adjust the row and col values based on your subplot configuration
        )

        print("NOT SHAPES")


        # n
        columns = [
            "filternummer",
            "maaiveldhoogte",
            "bovenkant buis",
            "bovenkant filter",
            "onderkant filter",
            "onderkant buis",
            "positie meetinstrument",
            "beschermconstructie",
        ]

        selection = selection[columns]
        # Nieuwe rij met kolomnamen
        column_names_row = pd.DataFrame([columns], columns=columns)

        # Voeg de rij met kolomnamen toe aan de DataFrame
        selection_with_column_names_row = pd.concat(
            [column_names_row, selection], ignore_index=True
        )
        positions_dict = {}
        for i in range(len(selection_with_column_names_row)):
            positions_dict[
                selection_with_column_names_row.iloc[i]["filternummer"]
            ] = selection_with_column_names_row.iloc[i].to_dict()
        position_table = pd.DataFrame(positions_dict)
        position_table.index = range(len(position_table))
        position_table.drop(0, inplace=True)
        position_table = position_table.rename(columns={"filternummer": ""})
        position_table[""] = [
            f"Maaiveldhoogte ({referentie})",
            f"Bovenkant buis ({referentie})",
            f"Bovenkant filter ({referentie})",
            f"Onderkant filter ({referentie})",
            f"Onderkant buis ({referentie})",
            f"Hoogte meetinstrument ({referentie})",
            "Beschermconstructie",
        ]

        print("NOT TABLE")


        barchart.add_trace(
            go.Table(
                header=dict(
                    values=list(position_table.columns.values),
                    font=dict(size=10),
                    align="left",
                ),
                cells=dict(
                    values=[
                        position_table[k].tolist()
                        for k in list(position_table.columns.values)
                    ],
                    align="left",
                ),
            ),
            row=2,
            col=1,
            # row=1, col=1
        )

        print("NOT TRACES 3")


        # Update de layout van de grafiek
        barchart.update_layout(
            yaxis1_title=f"Hoogte ({referentie})",
            xaxis1=dict(
                showline=False, showgrid=False, zeroline=False, fixedrange=True
            ),
            yaxis1_range=[
                selection["onderkant filter"].min() - 2,
                selection["bovenkant buis"].values[0] + 2,
            ],
            yaxis1=dict(showline=True, showgrid=False, zeroline=False, fixedrange=True),
            barmode="stack",  # Gebruik de gestapelde modus
            # paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=30, r=10, t=30, b=10),
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="right",
                x=1.15,
            ),
            height=800,
        )

        barchart.update_layout(barmode="relative")

        print("NOT LAYOUT")


        # Update the x-axis layout to set the tick positions and labels
        barchart.update_xaxes(
            showticklabels=False 
        )
        

    except Exception as e:
        print("EXCEPTION: ", e)

    barchart

    return barchart


# %% Dash App

app = DjangoDash(
    "VisualisatieMeetopstelling", external_stylesheets=[dbc.themes.BOOTSTRAP]
)

app.layout = html.Div(
    [
        dcc.Store(id="event-tubes-view"),
        dcc.Store(id="event-electrodes-view"),
        html.Div(
            [
                html.Div(id="groundwater-monitoring-well-static-id", children="", style={"display": "none"}),
                html.Div(
                    children=[
                        html.Br(),
                        html.Label("Geregistreerde werkzaamheden"),
                        dcc.Dropdown(id="event-list"),
                        html.Br(),
                        html.Label("Referentie"),
                        dcc.Dropdown(
                            id="referentie-list",
                            options=["mNAP", "m t.o.v. mv"],
                            value="mNAP",
                        ),
                    ],
                    style={"padding": 10, "flex": 1},
                ),
                html.Div(
                    children=[dcc.Graph(id="graphic")],
                    style={"padding-left": 20, "padding-right": 50, "flex": 4},
                ),
            ],
            style={"display": "flex", "flex-direction": "row"},
        ),
    ]
)


@app.callback(
    Output("collapse", "is_open"),
    [Input("collapse-button", "n_clicks")],
    [State("collapse", "is_open")],
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


@app.callback(
    Output("graphic", "figure"),
    [
        Input("event-tubes-view", "data"),
        Input("event-electrodes-view", "data"),
        Input("event-list", "value"),
        Input("event-list", "options"),
        Input("referentie-list", "value"),
    ],
)
def update_output_div(data_tube, data_electrodes, event, options, referentie):
    selection = pd.DataFrame(data_tube)
    selection_electrode = pd.DataFrame(data_electrodes)
    fig = generate_graph(selection, selection_electrode, event, options, referentie)

    return fig


@app.callback(
    [Output("event-list", "options"), Output("event-list", "value")],
    [Input("groundwater-monitoring-well-static-id", "children")],
)
def get_dropdown_events(groundwater_monitoring_well_static_id):
    monitoring_well = get_object_or_404(GroundwaterMonitoringWellStatic, bro_id=groundwater_monitoring_well_static_id)
    events = []

    def format_event(event_datetime:datetime.date, event: Event) -> dict:
        label = (
            f"{event.event_name} ({event_datetime})"
        )
        return {
            "datumtijd": str(event_datetime),
            "label": label,
            "strptime": event_datetime,
            "event_id": event.change_id,
        }

    # Onderhoudsmoment records
    onderhoudsmomenten = Event.objects.filter(
        groundwater_monitoring_well_static=monitoring_well,
    )
    for onderhoud in onderhoudsmomenten:
        event_datetime = datetime_convert(onderhoud.event_date)
        events.append(format_event(event_datetime, onderhoud))

    # Post-processing (removing duplicates and formatting)
    events = pd.DataFrame(events)

    events = events.sort_values(by=["strptime"])
    events = events.to_dict(orient="records")
    value = len(events) - 1
    options = [{"label": event["label"], "value": i, "event": event} for i, event in enumerate(events)]
    return options, value

def get_well_dynamic(event: Event) -> GroundwaterMonitoringWellDynamic:
    if event.groundwater_monitoring_well_dynamic:
        return event.groundwater_monitoring_well_dynamic
    
    datetime_event = convert_event_date_str_to_datetime(event.event_date)

    return GroundwaterMonitoringWellDynamic.objects.filter(
        groundwater_monitoring_well_static = event.groundwater_monitoring_well_static,
        date_from__lte =  datetime_event,
    ).order_by("date_from").last()

@app.callback(
    [Output("event-tubes-view", "data"), Output("event-electrodes-view", "data")],
    [
        Input("groundwater-monitoring-well-static-id", "children"),
        Input("event-list", "options"),
        Input("event-list", "value"),
    ],
)
def get_event(groundwater_monitoring_well_static_id, eventlist, event):
    eventframe = pd.DataFrame(eventlist)
    event_id = eventframe["event"][eventframe["value"] == event].values[0]["event_id"]
    monitoring_well = get_object_or_404(GroundwaterMonitoringWellStatic, bro_id=groundwater_monitoring_well_static_id)
    event = get_object_or_404(Event, change_id=event_id)
    well_dynamic = get_well_dynamic(event)
    datetime_event = convert_event_date_str_to_datetime(event.event_date)
    well_head_protector = well_dynamic.well_head_protector


    putdata = {
        "date": datetime_event,
        "constructie": (event.event_name == "constructie"),
        "onderhoud": [],
        "put": {
            "maaiveld": well_dynamic.ground_level_position,
        },
        "filters": [],
    }

    elektrode_data = []

    filters = GroundwaterMonitoringTubeStatic.objects.filter(groundwater_monitoring_well_static=monitoring_well)
    for filtr in filters:
        filtr_history = GroundwaterMonitoringTubeDynamic.objects.filter(
            groundwater_monitoring_tube_static=filtr, date_from__lte=datetime_event
        ).order_by("date_from").last()
        
        filt_dict = (
            {
                "nummer": filtr.tube_number,
                "bovenkant buis": filtr_history.tube_top_position,
                "bovenkant filter": filtr_history.screen_top_position,
                "onderkant filter": filtr_history.screen_bottom_position,
                # Onderkant buis wordt niet geregistreerd, daarom neem ik aan dat de onderkant van het filter de onderkant van de buis is.
                "onderkant buis": filtr_history.screen_bottom_position, 

                # Meet instrument diepte wordt op het moment ook nog niet geregistreerd (dummy waarde)
                "diepte meetinstrument": filtr_history.screen_top_position,

                # Zandvang wordt op het moment nog niks mee gedaan
                "zandvang": filtr.sediment_sump_present,
                "zandvang lengte": filtr.sediment_sump_length,
                "beschermconstructie": well_head_protector,
            },
        )

        if filtr_history.tube_inserted:
            filt_dict.update(
                {
                    "bovenkant ingeplaatst deel": filtr_history.tube_top_position,
                    "lengte ingeplaatst deel": filtr_history.inserted_part_length,
                }
            )

        putdata["filters"] += filt_dict

        geo_ohmkabels = GeoOhmCable.objects.filter(groundwater_monitoring_tube_static=filtr)
        for kabel in geo_ohmkabels:
            elektrodes = ElectrodeStatic.objects.filter(geo_ohm_cable=kabel)
            for elektrode in elektrodes:
                elektrode_data += [
                    {
                        "filter": filtr.tube_number,
                        "kabel": kabel.cable_number,
                        "elektrode": elektrode.electrode_number,
                        "positie": elektrode.electrode_position,
                    }
                ]
    
    try:
        putdataframe = transform_putdata_to_df(putdata)
    except:
        putdataframe = pd.DataFrame()

    electrodedataframe = transform_electrodedata_to_df(elektrode_data)
    
    event_dates = list(putdataframe["datum"].unique())

    event = event_dates[0]

    width_original = 0.15
    selection = putdataframe[putdataframe["datum"] == event]
    selection["gmw"] = monitoring_well.__str__()
    selection["startpunten"] = putdataframe["onderkant buis"]

    for column in [
        "onderkant buis",
        "onderkant ingeplaatst deel",
    ]:
        if column == "onderkant buis":
            selection[column] = selection[column].fillna(selection["onderkant filter"])
        if column == "onderkant ingeplaatst deel":
            selection[column] = selection[column].fillna(
                selection["bovenkant filter"] + 0.1
            )
        selection[column] = selection[column].fillna(0)

    selection["stijgbuis_onder_filter"] = (
        selection["onderkant filter"] - selection["onderkant buis"]
    )
    selection["stijgbuis_onder_filter"] = selection["stijgbuis_onder_filter"].round(3)

    selection["positie meetinstrument"] = (
        selection["bovenkant buis"] - selection["diepte meetinstrument"]
    )
    selection["positie meetinstrument"] = selection["positie meetinstrument"].round(3)

    selection["filter"] = selection["bovenkant filter"] - selection["onderkant filter"]
    selection["filter"] = selection["filter"].round(3)

    selection["stijgbuis"] = selection["bovenkant buis"] - selection["onderkant buis"]
    selection["stijgbuis"] = selection["stijgbuis"].round(3)

    selection["ingeplaatst deel"] = selection["lengte ingeplaatst deel"]


    selection["meetinstrumentsdiepte"] = selection["bovenkant buis"] - selection["positie meetinstrument"]
    selection["meetinstrumentsdiepte"] = selection["meetinstrumentsdiepte"].round(3)

    selection_electrode = electrodedataframe.copy()

    selection_electrode["x"] = selection_electrode["filter"] + (width_original / 2)
    return (selection.to_dict("records"), selection_electrode.to_dict("records"))


if __name__ == "__main__":
    app.run_server(debug=True)
