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
    ElectrodeDynamic,
    ElectrodeStatic,
    GroundwaterMonitoringTubeDynamic,
    GroundwaterMonitoringTubeStatic,
    GeoOhmCable,
    GroundwaterMonitoringWellDynamic,
    GroundwaterMonitoringWellStatic,
    Event,
)

logger = logging.getLogger(__name__)


def datetime_convert(gmt_datetime):
    amsterdam_timezone = pytz.timezone("Europe/Amsterdam")
    amsterdam_datetime = gmt_datetime.astimezone(amsterdam_timezone)
    amsterdam_date = amsterdam_datetime.date()
    return amsterdam_date


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
            columns=["filter", "kabel", "elektrode", "positie", "status"]
        )
    else:
        electrode_dataframe = pd.DataFrame(electrodedata)
    return electrode_dataframe


def transform_putdata_to_df(putdata):
    columns = [
        "datum",
        "gebeurtenis",
        "maaiveldhoogte",
        "filtercode",
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
        row["filtercode"] = event["filters"][i]["code"]
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
        print(flter)
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
            hovertext=maaiveld_y,
            hovertemplate="<br>".join(
                [
                    "Hoogte: %{customdata[0]}",
                ]
            ),
            line=dict(color="green", width=2),
        )

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

        barchart.update_layout(
            title_text="{} - {}".format(selection["filtercode"].values[0][:-3], event),
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

        barchart.update_traces(
            marker=dict(
                size=8,
                symbol="arrow-bar-left",
                line=dict(width=2, color="DarkSlateGrey"),
            ),
            selector=dict(mode="markers"),
        )

        # Meetinstrument dieptes
        for f in selection["filternummer"]:
            diepte_meetinstrument = selection["diepte meetinstrument"][
                selection["filternummer"] == f
            ].values[0]

            bovenkant_buis = selection["bovenkant buis"][
                selection["filternummer"] == f
            ].values[0]
            try:
                if selection["lengte ingeplaatst deel"][f - 1] != 0:
                    positie_meetinstrument = (
                        bk_ingeplaatst_deel[f - 1] - diepte_meetinstrument
                    )

                else:
                    positie_meetinstrument = bovenkant_buis - diepte_meetinstrument
                    y = [bovenkant_buis, positie_meetinstrument]

            except:  # noqa: E722
                logger.exception("Bare except")
                positie_meetinstrument = bovenkant_buis - diepte_meetinstrument
                y = [bovenkant_buis, positie_meetinstrument]
            x = [f, f]
            if f == 1:
                showlegend = True
            else:
                showlegend = False

            if referentie == "m t.o.v. mv":
                name = 'Inhangdiepte -t.o.v. maaiveld'
            else:
                name="Inhangdiepte - t.o.v. mNAP"

            barchart.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    legendgroup="diepte meetinstrument",
                    showlegend=showlegend,
                    hoverinfo="y,text",
                    text=name,
                    marker=dict(
                        color="purple",
                        size=10,
                        symbol="arrow-bar-up",
                        angleref="previous",
                    ),
                ),
                row=1,
                col=1,
            )

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
                y0=selection["maaiveldhoogte"].values[0],
                y1=selection["maaiveldhoogte"].values[0],
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

        # n
        columns = [
            "filtercode",
            "maaiveldhoogte",
            "bovenkant buis",
            "bovenkant filter",
            "onderkant filter",
            "onderkant buis",
            "positie meetinstrument",
            "meetinstrumentsdiepte",
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
                selection_with_column_names_row.iloc[i]["filtercode"]
            ] = selection_with_column_names_row.iloc[i].to_dict()
        position_table = pd.DataFrame(positions_dict)
        position_table.index = range(len(position_table))
        position_table.drop(0, inplace=True)
        position_table = position_table.rename(columns={"filtercode": ""})
        position_table[""] = [
            "Maaiveldhoogte (m t.o.v. mv)",
            f"Bovenkant buis ({referentie})",
            f"Bovenkant filter ({referentie})",
            f"Onderkant filter ({referentie})",
            f"Onderkant buis ({referentie})",
            f"Hoogte meetinstrument ({referentie})",
            "Meetinstrumentsdiepte (m t.o.v. bvk buis)",
            "Beschermconstructie",
        ]

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


        # Update the x-axis layout to set the tick positions and labels
        barchart.update_xaxes(
            showticklabels=False 
        )
        

    except Exception as e:
        print(e)

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
                html.Div(id="business-id", children="", style={"display": "none"}),
                html.Div(
                    children=[
                        html.Br(),
                        html.Label("Geregistreerde werkzaamheden / wijzigingen"),
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
                    children=[dcc.Graph(id="graph")],
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
    Output("graph", "figure"),
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
    [Input("business-id", "children")],
)
def get_dropdown_events(well_id):
    monitoring_well = get_object_or_404(GroundwaterMonitoringWellStatic, groundwater_monitoring_well_static_id=well_id)
    meetpunt_date = monitoring_well.datum_plaatsing
    events = []

    def add_event(event_datetime, event_type, onderhoud, events):
        if onderhoud:
            label = (
                f"Onderhoud, {event_datetime}"
                if event_type != "Inrichting"
                else f"{event_type}, {event_datetime}"
            )
        else:
            label = (
                f"Onbekend, {event_datetime}"
                if event_type != "Inrichting"
                else f"{event_type}, {event_datetime}"
            )
        try:
            if label not in pd.DataFrame(events)["label"].values:
                events.append(
                    {
                        "datumtijd": str(event_datetime),
                        "label": label,
                        "strptime": event_datetime,
                    }
                )
        except:  # noqa: E722
            logger.exception("Bare except")
            events.append(
                {
                    "datumtijd": str(event_datetime),
                    "label": label,
                    "strptime": event_datetime,
                }
            )
        return events

    # Meetpuntgeschiedenis records
    well_histories = GroundwaterMonitoringWellDynamic.objects.filter(
        groundwater_monitoring_well_static=monitoring_well
    )
    for well_history in well_histories:
        event_datetime = datetime_convert(well_history.datum_vanaf)
        if event_datetime < monitoring_well.datum_plaatsing:
            event_datetime = monitoring_well.datum_plaatsing
        event_type = "Inrichting" if event_datetime <= meetpunt_date else "Onbekend"

        events = add_event(event_datetime, event_type, False, events)

    # Onderhoudsmoment records
    onderhoud = Event.objects.filter(
        meetpunt_id=monitoring_well.id, datum__gte=meetpunt_date
    )
    for well_history in onderhoud:
        event_datetime = datetime_convert(well_history.datum)
        events = add_event(event_datetime, well_history.id, True, events)

    # Filtergeschiedenis records
    for filtr in GroundwaterMonitoringTubeStatic.objects.filter(meetpunt_id=monitoring_well.id):
        filtr_historie = GroundwaterMonitoringTubeDynamic.objects.filter(filter_id=filtr.id)
        for filtr_historie_record in filtr_historie:
            event_datetime = datetime_convert(filtr_historie_record.datum_vanaf)
            if event_datetime < monitoring_well.datum_plaatsing:
                event_datetime = monitoring_well.datum_plaatsing
            if event_datetime not in [e["datumtijd"] for e in events]:
                event_type = filtr_historie_record.onderhoudsmoment_id
                events = add_event(event_datetime, event_type, False, events)

    # Post-processing (removing duplicates and formatting)
    events = pd.DataFrame(events)
    duplicates_events = events[events.duplicated(subset=["strptime"])]
    for i in duplicates_events.index:
        label = duplicates_events["label"][i].replace("Onderhoud", "Onbekend")
        events_i = events[events["label"] == label].index.values[0]
        events.drop(events_i, inplace=True)

    events = events.sort_values(by=["strptime"])
    events = events.to_dict(orient="records")
    value = len(events) - 1
    options = [{"label": event["label"], "value": i} for i, event in enumerate(events)]
    return options, value


@app.callback(
    [Output("event-tubes-view", "data"), Output("event-electrodes-view", "data")],
    [
        Input("business-id", "children"),
        Input("event-list", "options"),
        Input("event-list", "value"),
    ],
)
def get_event(business_id, eventlist, event):
    eventframe = pd.DataFrame(eventlist)
    event_label = eventframe["label"][eventframe["value"] == event].values[0]
    time = datetime.datetime.strptime(
        event_label.split(", ")[1] + "T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ"
    )
    meetpunt = GroundwaterMonitoringWellStatic.objects.get(business_id=business_id)
    meetpunt_hist = GroundwaterMonitoringWellDynamic.objects.filter(
        meetpunt_id=meetpunt.id, datum_vanaf__lte=time
    ).latest("datum_vanaf")
    beschermconstructie = meetpunt_hist.beschermconstructie

    putdata = {
        "date": meetpunt.datum_plaatsing,
        "constructie": True,
        "onderhoud": [],
        "put": {
            "maaiveld": meetpunt_hist.maaiveldhoogte,
        },
        "filters": [],
    }

    elektrode_data = []

    filters = GroundwaterMonitoringTubeStatic.objects.filter(meetpunt_id=meetpunt.id)
    for filtr in filters:
        filtr_gesch = GroundwaterMonitoringTubeDynamic.objects.filter(
            filter_id=filtr.id, datum_vanaf__lte=time
        ).latest("datum_vanaf")
        filtr_gesch_tot_inplaatsing = GroundwaterMonitoringTubeDynamic.objects.filter(
            filter_id=filtr.id, ingeplaatst_deel=False, datum_vanaf__lte=time
        ).latest("datum_vanaf")
        if not filtr_gesch.ingeplaatst_deel:
            putdata["filters"] += (
                {
                    "code": filtr.business_id,
                    "nummer": filtr.filternummer,
                    "bovenkant buis": filtr_gesch.referentiehoogte,
                    "bovenkant filter": filtr.diepte_bovenkant_filter,
                    "onderkant filter": filtr.diepte_onderkant_filter,
                    "onderkant buis": filtr.diepte_onderkant_buis,
                    "diepte meetinstrument": filtr_gesch.meetinstrumentdiepte,
                    "zandvang": filtr.zandvang,
                    "zandvang lengte": filtr.zandvanglengte,
                    "beschermconstructie": beschermconstructie,
                },
            )
        else:
            putdata["filters"] += (
                {
                    "code": filtr.business_id,
                    "nummer": filtr.filternummer,
                    "bovenkant buis": filtr_gesch_tot_inplaatsing.referentiehoogte,
                    "bovenkant ingeplaatst deel": filtr_gesch.referentiehoogte,
                    "lengte ingeplaatst deel": filtr_gesch.lengte_ingeplaatst_deel,
                    "bovenkant filter": filtr.diepte_bovenkant_filter,
                    "onderkant filter": filtr.diepte_onderkant_filter,
                    "onderkant buis": filtr.diepte_onderkant_buis,
                    "diepte meetinstrument": filtr_gesch.meetinstrumentdiepte,
                    "zandvang": filtr.zandvang,
                    "zandvang lengte": filtr.zandvanglengte,
                    "beschermconstructie": beschermconstructie,
                },
            )

        geo_ohmkabels = GeoOhmCable.objects.filter(filter_id=filtr.id)
        for kabel in geo_ohmkabels:
            elektrodes = ElectrodeStatic.objects.filter(geo_ohmkabel__id=kabel.id)
            for elektrode in elektrodes:
                elektrode_data += [
                    {
                        "filter": filtr.filternummer,
                        "kabel": kabel.kabelnummer,
                        "elektrode": elektrode.elektrodenummer,
                        "positie": elektrode.elektrodepositie,
                        "status": elektrode.elektrodestatus,
                    }
                ]
    try:
        putdataframe = transform_putdata_to_df(putdata)
    except Exception:
        putdataframe = pd.DataFrame()

    electrodedataframe = transform_electrodedata_to_df(elektrode_data)
    event_dates = list(putdataframe["datum"].unique())

    event = event_dates[0]

    width_original = 0.15
    selection = putdataframe[putdataframe["datum"] == event]
    selection["startpunten"] = putdataframe["onderkant buis"]

    for column in [
        "bovenkant buis",
        "onderkant buis",
        "bovenkant filter",
        "onderkant filter",
        "bovenkant ingeplaatst deel",
        "diepte meetinstrument",
        "onderkant ingeplaatst deel",
        "lengte ingeplaatst deel",
    ]:
        if column == "onderkant buis":
            selection[column] = selection[column].fillna(selection["onderkant filter"])
        if column == "onderkant ingeplaatst deel":
            selection[column] = selection[column].fillna(
                selection["bovenkant filter"] + 0.1
            )
        selection[column] = selection[column].fillna(0)

    nul_filter = 0
    for value in selection["filternummer"]:
        if value == 0:
            nul_filter = 1

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

    selection_electrode["x"] = selection_electrode["filter"] + (width_original / 2) + nul_filter
    return (selection.to_dict("records"), selection_electrode.to_dict("records"))


if __name__ == "__main__":
    app.run_server(debug=True)
