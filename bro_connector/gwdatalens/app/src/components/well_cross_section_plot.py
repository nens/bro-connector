# %%
import pandas as pd
import plotly.graph_objects as go

from gwdatalens.app.constants import ColumnNames


def plot_well_cross_section(df, tube_width=0.15):
    """
    Plot cross-section of observation wells showing tube positions and screen intervals.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing well data with columns:
        - tube_top_position: elevation of tube top (m)
        - ground_level_position: ground surface elevation (m)
        - screen_top: top of screen interval (m)
        - screen_bot: bottom of screen interval (m)
        Index should contain tube identifiers/numbers
    tube_width : float, optional
        Width of the tube representation (default: 0.15)

    Returns
    -------
    fig : plotly.graph_objects.Figure
        Plotly figure object
    """
    fig = go.Figure()

    # Sort by ground level position for better visualization
    df_sorted = df.sort_values(ColumnNames.GROUND_LEVEL_POSITION, ascending=False)

    # Create x-positions for each well
    x_positions = list(range(len(df_sorted)))
    df_sorted.index.tolist()

    # Determine plot bounds
    min_elevation = (
        df_sorted[[ColumnNames.SCREEN_BOT, ColumnNames.GROUND_LEVEL_POSITION]]
        .min()
        .min()
    )
    max_elevation = df_sorted[ColumnNames.TUBE_TOP_POSITION].max()
    ground_level = df_sorted[ColumnNames.GROUND_LEVEL_POSITION].iloc[
        0
    ]  # Assuming same ground level

    # Add subsurface shading (sand layer below ground level)
    fig.add_trace(
        go.Scatter(
            x=[-0.5, len(df_sorted) - 0.5, len(df_sorted) - 0.5, -0.5, -0.5],
            y=[
                ground_level,
                ground_level,
                min_elevation - 5,
                min_elevation - 5,
                ground_level,
            ],
            fill="toself",
            fillcolor="rgba(245, 222, 179, 0.4)",  # Light yellow/wheat color for sand
            line={"width": 0},
            mode="lines",
            showlegend=False,
            name="Subsurface (sand)",
            hoverinfo="skip",
        )
    )

    # Add ground level line
    fig.add_trace(
        go.Scatter(
            x=[-0.5, len(df_sorted) - 0.5],
            y=[ground_level, ground_level],
            mode="lines",
            line={"color": "green", "width": 3},
            showlegend=True,
            name="Ground level",
            hovertemplate=f"Ground level: {ground_level:.2f} m<extra></extra>",
        )
    )

    for i, (tube_name, row) in enumerate(df_sorted.iterrows()):
        x_pos = x_positions[i]
        half_width = tube_width / 2

        # Solid rectangle from tube top to screen top (tube casing)
        x_tube = [
            x_pos - half_width,
            x_pos + half_width,
            x_pos + half_width,
            x_pos - half_width,
            x_pos - half_width,
        ]
        y_tube = [
            row[ColumnNames.TUBE_TOP_POSITION],
            row[ColumnNames.TUBE_TOP_POSITION],
            row[ColumnNames.SCREEN_TOP],
            row[ColumnNames.SCREEN_TOP],
            row[ColumnNames.TUBE_TOP_POSITION],
        ]

        fig.add_trace(
            go.Scatter(
                x=x_tube,
                y=y_tube,
                fill="toself",
                fillcolor="rgba(0, 0, 0, 0.3)",  #'rgba(70, 130, 180, 0.7)', Steel blue
                line={"color": "black", "width": 2},
                mode="lines",
                showlegend=False,
                hoveron="fills+points",  # enable hover on the filled area
                name="Tube casing",  # avoid "trace n" fallback
                hovertemplate=(
                    f"{tube_name}<br>Top: "
                    f"NAP{row['tube_top_position']:+.2f} m<extra></extra>"
                ),
            )
        )
        # Add invisible hover point at center
        fig.add_trace(
            go.Scatter(
                x=[x_pos],
                y=[
                    (row[ColumnNames.TUBE_TOP_POSITION] + row[ColumnNames.SCREEN_TOP])
                    / 2
                ],
                # line=dict(color="black", width=2),
                mode="markers",
                marker={"size": 15, "opacity": 0, "color": "black"},  # invisible
                showlegend=False,
                hovertemplate=(
                    f"{tube_name}<br>Top: "
                    f"NAP{row['tube_top_position']:+.2f} m<extra></extra>"
                ),
            )
        )

        # Dashed rectangle from screen top to screen bottom (screen interval)
        x_screen = [
            x_pos - half_width,
            x_pos + half_width,
            x_pos + half_width,
            x_pos - half_width,
            x_pos - half_width,
        ]
        y_screen = [
            row[ColumnNames.SCREEN_TOP],
            row[ColumnNames.SCREEN_TOP],
            row[ColumnNames.SCREEN_BOT],
            row[ColumnNames.SCREEN_BOT],
            row[ColumnNames.SCREEN_TOP],
        ]

        fig.add_trace(
            go.Scatter(
                x=x_screen,
                y=y_screen,
                fill="toself",
                fillcolor="rgba(255, 99, 71, 0.3)",  # Light red/tomato
                line={"color": "red", "width": 2, "dash": "2px,2px"},
                mode="lines",
                showlegend=False,
                hoveron="fills+points",  # enable hover on the filled area
                name="Screen interval",  # avoid "trace n" fallback
                hovertemplate=(
                    f"{tube_name}<br>Top: NAP{row['screen_top']:+.2f} m<br>Bottom: "
                    f"NAP{row['screen_bot']:+.2f} m<extra></extra>"
                ),
            )
        )

        # Add tube label at the top
        fig.add_annotation(
            x=x_pos,
            y=row[ColumnNames.TUBE_TOP_POSITION],
            text=tube_name.split("-")[-1],  # Show only the tube number
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1,
            arrowcolor="black",
            ax=0,
            ay=-30,
            font={"size": 10, "color": "black"},
        )

    # Add legend entries for tube types
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            fill="toself",
            fillcolor="rgba(0, 0, 0, 0.3)",
            line={"color": "black", "width": 2},
            name="Tube casing",
            hoverinfo="skip",  # Skip hover for legend entry
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            fill="toself",
            fillcolor="rgba(255, 99, 71, 0.3)",
            line={"color": "red", "width": 2, "dash": "2px,2px"},
            name="Screen interval",
            hoverinfo="skip",  # Skip hover for legend entry
        )
    )

    # Update layout
    fig.update_layout(
        title=df.index[0].split("-")[0],
        title_x=0.5,  # Center align the title
        xaxis={
            # title='Tube Number',
            # tickmode='array',
            # tickvals=x_positions,
            # ticktext=[name.split('-')[-1] for name in tube_names],  # Show only tubeno
            "range": [-0.5, len(df_sorted) - 0.5],
            "showticklabels": False,  # Hide x-axis tick labels
        },
        yaxis={
            "title": "Elevation (m NAP)",
            # autorange=True
            "range": [min_elevation - 5, max_elevation + 2],
        },
        hovermode="closest",
        height=600,
        width=400,
        showlegend=True,
        legend={
            "orientation": "v",  # Changed to vertical
            "yanchor": "bottom",
            "y": 0.025,  # Changed from 1.02 to 0.02
            "xanchor": "left",
            "x": 0.025,  # Changed from 0.5 to 0.02
        },
        template="plotly_white",
        plot_bgcolor="rgba(240, 248, 255, 0.3)",  # Light blue background
    )

    return fig


# Example usage with the provided data
# if __name__ == "__main__":
# Data from the CSV
data = {
    ColumnNames.TUBE_TOP_POSITION: [5.38, 5.34, 5.28, 5.29, 5.23],
    ColumnNames.GROUND_LEVEL_POSITION: [4.45, 4.45, 4.45, 4.45, 4.45],
    ColumnNames.SCREEN_TOP: [0.92, -7.5, -19.8, -34.79, -48.9],
    ColumnNames.SCREEN_BOT: [-0.08, -8.5, -20.8, -35.79, -49.9],
}
df_example = pd.DataFrame(
    data,
    index=[
        "GMW000000057214-001",
        "GMW000000057214-002",
        "GMW000000057214-003",
        "GMW000000057214-004",
        "GMW000000057214-005",
    ],
)

fig = plot_well_cross_section(df_example)
fig.show()
# %%
