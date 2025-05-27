import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
import dash
import pulp as pl  # Optimization library
import dash_bootstrap_components as dbc  # For collapse components
from dash import Dash, html, dcc, Input, Output, State
from pygments.styles.dracula import background
from shapely.geometry import shape  # For computing centroids

# === Load GeoJSON ===
try:
    with open("MP Districts Website Map final.geojson", "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
except Exception as e:
    raise FileNotFoundError(f"Error loading GeoJSON file: {e}")

# === Load MP State Outline GeoJSON ===
try:
    with open("MP state outline.geojson", "r", encoding="utf-8") as f:
        state_outline_geojson = json.load(f)
except Exception as e:
    raise FileNotFoundError(f"Error loading MP State Outline GeoJSON file: {e}")

districts_geo = geojson_data
district_names = [f["properties"]["Dist_Name"] for f in geojson_data["features"]]
print(district_names)

# === Load Excel Data ===
try:
    df = pd.read_excel("District data.xlsx", sheet_name="Dist Wise Pivot  (2)", header=2)
except Exception as e:
    raise FileNotFoundError(f"Error loading Excel file: {e}")

df.columns = [str(col).strip() for col in df.columns]
df = df.rename(columns={df.columns[0]: "District"})
df = df[df["District"].notna() & df["District"].str.strip().ne("")]

def safe(val):
    return float(val) if pd.notna(val) else 0.0

# === Helper for empty figures ===
def empty_figure(title):
    fig = go.Figure()
    fig.update_layout(
        title={"text": title, "x": 0.5, "font": {"size": 20, "color": "white", "family": "Arial"}},
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", font_color="white",
        xaxis={"visible": False}, yaxis={"visible": False},
        margin={"r": 0, "t": 40, "l": 0, "b": 0}
    )
    return fig

# === Create Dash App with Bootstrap external stylesheet ===
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "MP Waste Dashboard"

# Create choropleth map with color by waste generated
map_fig = px.choropleth_map(
    df,
    geojson=districts_geo,
    locations="District",
    featureidkey="properties.Dist_Name",
    map_style="carto-positron",
    color_continuous_scale="bluered",
    range_color=(700, 700),
    center={"lat": 24, "lon": 78.5},
    zoom=6,
    opacity=0.7
)

map_fig.update_traces(
    marker_line_width=0.5,             # White border width
    marker_line_color="black",         # White border always
    hovertemplate="%{location}",
    selected=dict(marker=dict(opacity=1)),   # Fully visible when selected
    unselected=dict(marker=dict(opacity=0.3))  # Slightly faded when unselected
)

# --- Compute centroids and add permanent text labels ---
lats = []
lons = []
labels = []
for feature in geojson_data["features"]:
    geom = shape(feature["geometry"])
    centroid = geom.centroid
    lats.append(centroid.y)
    lons.append(centroid.x)
    labels.append(feature["properties"]["Dist_Name"])
print(len(lats), len(lons), len(labels))

text_trace = go.Scattermap(
    lat=lats,
    lon=lons,
    mode='text',
    text=labels,
    hoverinfo="skip",  # So that these labels don't capture clicks
    textposition="middle center",
    textfont={"size": 14, "color": "black"},
    showlegend=False
)

new_data = [text_trace] + list(map_fig.data)
map_fig = go.Figure(data=new_data, layout=map_fig.layout)

map_fig.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    clickmode="event+select",
    dragmode=False,
)

# --- Layout ---
# Below the map, we place a persistent district card (updated by a callback) and
# three toggle buttons. Each toggle button controls a collapsible section.
app.layout = dbc.Container(
    [
        html.H2(
            "Madhya Pradesh District Waste Dashboard",
            style={
                "textAlign": "center",
                "color": "white",
                "fontSize": "28px",
                "fontWeight": "bold"
            }
        ),
        # Place the map and district card/buttons side by side using a flex container.
        html.Div(
            [
                # Map container – 90%
                html.Div(
                    dcc.Graph(
                        id="district-map",
                        figure=map_fig,
                        config={"scrollZoom": False, "displayModeBar": False},
                        style={"height": "610px", "width": "100%"}
                    ),
                    style={"width": "80%"}
                ),
                # District card and toggle buttons – 10%
                html.Div(
                    [
                        # Toggle Buttons
                        dbc.Button(
                            "Population Forecast",
                            id="toggle-pop",
                            color="primary",
                            n_clicks=0,
                            style={"width": "90%", "marginBottom": "10px", "marginLeft": '20px'}
                        ),
                        dbc.Button(
                            "Waste Characteristics",
                            id="toggle-waste-char",
                            color="warning",
                            n_clicks=0,
                            style={"width": "90%", "marginBottom": "10px", "marginLeft": '20px'}
                        ),
                        dbc.Button(
                            "Waste Composition",
                            id="toggle-waste-comp",
                            color="info",
                            n_clicks=0,
                            style={"width": "90%", "marginLeft": '20px'}
                        ),
                        # District Card at the bottom
                        html.Div(
                            id="district-card",
                            style={"marginTop": "360px", "marginLeft": '20px'}
                        ),
                    ],
                    style={
                        "width": "20%",
                        "display": "flex",
                        "flexDirection": "column",
                        "justifyContent": "flex-start"
                    }
                )
            ],
            style={
                "display": "flex",
                "flexDirection": "row",
                "alignItems": "flex-start",
                "marginTop": "40px"
            }
        ),
        # Collapsible sections for each topic below the flex container
        dbc.Row(
            [
                dbc.Collapse(
                    html.Div(id="pop-section-content"),
                    id="collapse-pop",
                    is_open=False
                )
            ],
            style={"marginTop": "20px"}
        ),
        dbc.Row(
            [
                dbc.Collapse(
                    html.Div(id="waste-char-section-content"),
                    id="collapse-waste-char",
                    is_open=False
                )
            ],
            style={"marginTop": "20px"}
        ),
        dbc.Row(
            [
                dbc.Collapse(
                    html.Div(id="waste-comp-section-content"),
                    id="collapse-waste-comp",
                    is_open=False
                )
            ],
            style={"marginTop": "20px"}
        )
    ],
    fluid=True,
    style={"backgroundColor": "#1e1e1e", "padding": "20px", "fontFamily": "Arial"}
)

# --- Dashboard Update Callback ---
# This callback updates the district card and the content for each of the three sections
@app.callback(
    [Output("district-card", "children"),
     Output("pop-section-content", "children"),
     Output("waste-char-section-content", "children"),
     Output("waste-comp-section-content", "children")],
    Input("district-map", "clickData")
)
def update_dashboard(clickData):
    if not clickData or "points" not in clickData:
        # If no district has been clicked yet, show placeholder messages.
        placeholder = html.Div("Click a district on the map", style={"color": "white", "textAlign": "center"})
        return placeholder, placeholder, placeholder, placeholder

    district_name = clickData["points"][0]["location"]
    match_row = df[df["District"].str.lower().str.strip() == district_name.lower().strip()]
    if match_row.empty:
        no_data = html.Div("No data for selected district", style={"color": "white", "textAlign": "center"})
        return no_data, no_data, no_data, no_data

    row = match_row.iloc[0]
    # Extract values
    census_pop = safe(row.get("Sum of Census 2011 Population", 0))
    sw_gen = safe(row.get("Sum of SW_Generation (TPD)", 0))
    sw_proc = safe(row.get("Sum of SW_Processed_ (TPD)", 0))
    sw_gap = safe(row.get("Sum of SW Collection Gap (in TPD)", 0))
    processed_percent = (sw_proc / sw_gen * 100) if sw_gen > 0 else 0
    if processed_percent > 100:
        processed_percent = 100
    sewage_gen = safe(row.get("Sum of Sewage Generation (in MLD)", 0))
    growth_rate = safe(row.get("Average of Decadal Grouth Rate in % (During 2001-2011)"))

    # --------------------------
    # District Card (always visible)
    district_card = html.Div([
        html.H4("District"),
        html.P(district_name, style={"fontSize": "22px", "fontWeight": "bold"})
    ], style={"padding": "10px", "border": "1px solid #444", "borderRadius": "10px",
              "backgroundColor": "#2c2c2c", "color": "white", "textAlign": "center", "marginBottom": "10px"})

    # --- Population Forecast Section (Updated) ---

    # KPI Card for Census 2011 Population
    census_card = html.Div(
        [
            html.H4("Census 2011 Population", style={"fontSize": "16px", "fontWeight": "normal", "marginTop": "0"}),
            html.P(f"{int(census_pop):,}", style={"fontSize": "24px", "fontWeight": "bold", "margin": "0"})
        ],
        style={
            "padding": "15px",
            "borderRadius": "10px",
            "backgroundColor": "#2c2c2c",
            "color": "white",
            "marginTop": "50px",
            "textAlign": "center",
            "marginBottom": "20px"
        }
    )

    # Population Forecast Calculation (same as before)
    pop_2025 = safe(row.get("Sum of Projected Population by 2025", 0))
    if census_pop > 0:
        CAGR = (pop_2025 / census_pop) ** (1 / (2025 - 2011)) - 1
    else:
        CAGR = 0
    years = list(range(2025, 2031))
    pop_forecast_values = [pop_2025 * ((1 + CAGR) ** (year - 2025)) for year in years]

    # Population Forecast Line Chart
    pop_forecast_fig = go.Figure()
    pop_forecast_fig.add_trace(
        go.Scatter(
            x=[str(year) for year in years],
            y=[round(val, 2) for val in pop_forecast_values],
            mode='lines+markers',
            line=dict(color="red", width=3),
            marker=dict(color="blue", size=15)
        )
    )
    pop_forecast_fig.update_layout(
        title={
            "text": "Population Forecast (2025-2030)",
            "x": 0.5,
            "font": {"size": 30, "color": "white", "family": "Arial"}
        },
        yaxis_title="Population",
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.2)",
            zerolinecolor="rgba(255,255,255,0.4)"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.2)",
            zerolinecolor="rgba(255,255,255,0.4)"
        ),
        plot_bgcolor="rgba(30,30,30,0.6)",
        paper_bgcolor="rgba(30,30,30,0.8)",
        font_color="white"
    )

    # Create separate KPI cards for the forecasted population for each year
    population_kpi_cards = html.Div(
        [
            html.Div(
                [
                    html.H4(str(year), style={"fontSize": "16px", "fontWeight": "normal", "margin": "0"}),
                    html.P(f"{round(val):,}", style={"fontSize": "24px", "fontWeight": "bold", "margin": "0"})
                ],
                style={
                    "padding": "15px",
                    "borderRadius": "10px",
                    "backgroundColor": "#2c2c2c",
                    "color": "white",
                    "textAlign": "center",
                    "margin": "5px",
                    "flex": "1 1 15%"
                }
            )
            for year, val in zip(years, pop_forecast_values)
        ],
        style={
            "display": "flex",
            "justifyContent": "space-around",
            "flexWrap": "wrap",
            "width": "100%",
            "marginTop": "20px"
        }
    )

    # Combine all components into the final population section
    pop_section = html.Div([
        census_card,  # The census KPI card on top
        dcc.Graph(figure=pop_forecast_fig),  # The population forecast line chart
        population_kpi_cards  # The row of KPI cards for each forecast year
    ])

    # --------------------------
    # Waste Composition Section (Section 2)
    # Example: Compute current waste metrics
    sw_gen = safe(row.get("Sum of SW_Generation (TPD)", 0))
    sw_proc = safe(row.get("Sum of SW_Processed_ (TPD)", 0))
    sw_gap = safe(row.get("Sum of SW Collection Gap (in TPD)", 0))

    # ----------------------------------------------------------------
    # 1. Create bar chart (bar_fig) for current waste metrics
    bar_fig = go.Figure()
    bar_fig.add_trace(
        go.Bar(
            name=f"Generated: {sw_gen:.2f} TPD",
            x=["Generated"],
            y=[round(sw_gen, 2)],
            marker_color="blue"
        )
    )
    bar_fig.add_trace(
        go.Bar(
            name=f"Processed: {sw_proc:.2f} TPD",
            x=["Processed"],
            y=[round(sw_proc, 2)],
            marker_color="green"
        )
    )
    bar_fig.add_trace(
        go.Bar(
            name=f"Gap: {sw_gap:.2f} TPD",
            x=["Gap"],
            y=[round(sw_gap, 2)],
            marker_color="red"
        )
    )
    bar_fig.update_layout(
        barmode="group",
        title={"text": "Current Waste Metrics (TPD)", "x": 0.5},
        plot_bgcolor="#1e1e1e",
        paper_bgcolor="#1e1e1e",
        font_color="white",
        margin={"r": 0, "t": 40, "l": 0, "b": 0}
    )

    # ----------------------------------------------------------------
    # 2. Create pie chart (pie_fig) for Processed vs Gap comparison
    proc_pie = min(sw_proc, sw_gen)
    gap_pie = sw_gen - proc_pie
    pie_fig = px.pie(
        names=["Processed", "Gap"],
        values=[proc_pie, gap_pie],
        hole=0.3,
        color_discrete_map={"Processed": "green", "Gap": "red"}
    )
    pie_fig.update_layout(
        title={"text": "Processed vs Gap (TPD)", "x": 0.5},
        plot_bgcolor="#1e1e1e",
        paper_bgcolor="#1e1e1e",
        font_color="white",
        margin={"r": 0, "t": 40, "l": 0, "b": 0}
    )

    # ----------------------------------------------------------------
    # 3. KPI Cards for % Waste Processed and Decadal Waste Growth Rate
    waste_kpi_card_1 = html.Div(
        [
            html.H4("% Waste Processed", style={"fontSize": "16px", "fontWeight": "normal", "margin": "0"}),
            html.P(f"{processed_percent:.1f}%", style={"fontSize": "24px", "fontWeight": "bold", "margin": "0"})
        ],
        style={
            "padding": "15px",
            "borderRadius": "10px",
            "backgroundColor": "#2c2c2c",
            "color": "white",
            "textAlign": "center",
            "margin": "5px",
            "flex": "1 1 40%"
        }
    )

    waste_char_kpi_cards = html.Div(
        [waste_kpi_card_1],
        style={"display": "flex", "justifyContent": "center", "marginBottom": "20px"}
    )

    # ----------------------------------------------------------------
    # 4. Place the charts side by side
    charts_container = html.Div(
        [
            html.Div(dcc.Graph(figure=bar_fig), style={"flex": "1", "margin": "10px"}),
            html.Div(dcc.Graph(figure=pie_fig), style={"flex": "1", "margin": "10px"})
        ],
        style={
            "display": "flex",
            "flexDirection": "row",
            "justifyContent": "space-around",
            "width": "100%"
        }
    )

    # ----------------------------------------------------------------
    # 5. Heading for Vehicle Requirement
    vehicle_heading = html.H4(
        "Vehicle Requirement to Process Generated Waste",
        style={"color": "white", "textAlign": "center", "marginTop": "20px"}
    )

    # ----------------------------------------------------------------
    # 6. Build vehicle KPI cards (assume vehicle_cards is defined, for example:)

    # --------------------------------------------------------
    # VEHICLE OPTIMIZATION MODEL
    # --------------------------------------------------------
    # Set the daily waste gap as the required capacity (in tonnes)
    W = sw_gen  # waste gap (tonnes)

    # Vehicle capacities (in tonnes)
    cap_bulk = 20  # Bulk truck capacity
    cap_lcv = 3.8  # Mini LCV capacity
    cap_tri = 0.5  # Tri-cycle trolley capacity

    # Cost parameters (per day cost for each vehicle; ADD YOUR VALUES HERE)
    cost_bulk = 2354 # e.g., cost per day for one bulk truck [ADD YOUR COST]
    cost_lcv = 1926 # e.g., cost per day for one mini LCV truck [ADD YOUR COST]
    cost_tri = 913  # e.g., cost per day for one tri-cycle trolley [ADD YOUR COST]

    # Create MILP optimization model
    problem = pl.LpProblem("Vehicle_Optimization", pl.LpMinimize)

    # Decision variables (number of vehicles, integers)
    x = pl.LpVariable('bulk_trucks', lowBound=0, cat='Integer')
    y = pl.LpVariable('lcv_trucks', lowBound=0, cat='Integer')
    z = pl.LpVariable('tricycle_trolleys', lowBound=0, cat='Integer')

    # Objective: Minimize total daily cost of vehicles
    problem += cost_bulk * x + cost_lcv * y + cost_tri * z, "Total_Daily_Cost"

    # Constraint: The total capacity must cover the waste gap
    problem += cap_bulk * x + cap_lcv * y + cap_tri * z >= W, "Capacity_Constraint"

    # You can add additional constraints here (e.g., workforce, trip frequency, etc.)

    # Solve the MILP optimization problem
    problem.solve()

    # Retrieve the optimal number of vehicles
    bulk_opt = int(pl.value(x))
    lcv_opt = int(pl.value(y))
    tri_opt = int(pl.value(z))
    vehicle_cards = html.Div(
        [
            html.Div(
                [
                    html.H4("New Bulk Trucks Required (20T)", style={"fontSize": "16px", "margin": "0"}),
                    html.P(f"{int(bulk_opt):,}", style={"fontSize": "24px", "fontWeight": "bold", "margin": "0"})
                ],
                style={
                    "padding": "10px",
                    "border": "1px solid #444",
                    "borderRadius": "10px",
                    "flex": "1 1 30%",
                    "backgroundColor": "#2c2c2c",
                    "color": "white",
                    "textAlign": "center",
                    "margin": "5px"
                }
            ),
            html.Div(
                [
                    html.H4("New LCV Mini Trucks Required (3.8T)", style={"fontSize": "16px", "margin": "0"}),
                    html.P(f"{int(lcv_opt):,}", style={"fontSize": "24px", "fontWeight": "bold", "margin": "0"})
                ],
                style={
                    "padding": "10px",
                    "border": "1px solid #444",
                    "borderRadius": "10px",
                    "flex": "1 1 30%",
                    "backgroundColor": "#2c2c2c",
                    "color": "white",
                    "textAlign": "center",
                    "margin": "5px"
                }
            ),
            html.Div(
                [
                    html.H4("New Tri-cycle Trolleys Required (0.5T)", style={"fontSize": "16px", "margin": "0"}),
                    html.P(f"{int(tri_opt):,}", style={"fontSize": "24px", "fontWeight": "bold", "margin": "0"})
                ],
                style={
                    "padding": "10px",
                    "border": "1px solid #444",
                    "borderRadius": "10px",
                    "flex": "1 1 30%",
                    "backgroundColor": "#2c2c2c",
                    "color": "white",
                    "textAlign": "center",
                    "margin": "5px"
                }
            )
        ],
        style={"display": "flex", "justifyContent": "space-around", "width": "100%", "marginTop": "10px"}
    )

    # ----------------------------------------------------------------
    # 7. Combine the Waste Characteristics section
    waste_char_section = html.Div(
        [
            waste_char_kpi_cards,  # KPI cards: % Waste Processed and Growth Rate
            charts_container,  # Side-by-side bar and pie charts
            vehicle_heading,  # Heading for Vehicle Requirement
            vehicle_cards  # Vehicle KPI cards
        ],
        style={"marginTop": "20px"}
    )

    # ----------------------------------------------------------------
    # Waste Composition Section (Section 3)
    pw = safe(row.get("Sum of Estimated PW Generation in TPD", 0))
    cd = safe(row.get("Sum of C&D Waste Generation in TPD - 2025", 0))
    ew = safe(row.get("Sum of e-waste Generation (TPA)", 0)) / 365

    waste_kpis = [
        ("Total Solid Waste Generated", f"{sw_gen:.2f} TPD", "blue"),
        ("Plastic Waste", f"{pw:.2f} TPD", "green"),
        ("C&D Waste", f"{cd:.2f} TPD", "orange"),
        ("E-waste", f"{ew:.2f} TPD", "red"),
        ("Sewage Waste", f"{sewage_gen:.2f} MLD", "brown")
    ]

    waste_kpi_cards = html.Div(
        [
            html.Div(
                [
                    html.H4(title, style={"fontSize": "16px", "fontWeight": "normal"}),  # Smaller heading
                    html.P(value, style={"fontSize": "24px", "fontWeight": "bold"})  # Larger value
                ],

                style={
                    "padding": "15px",
                    "borderRadius": "10px",
                    "flex": "1 1 22%",
                    "backgroundColor": color,
                    "color": "white",
                    "textAlign": "center",
                    "margin": "5px"
                }
            )
            for title, value, color in waste_kpis
        ],
        style={
            "display": "flex",
            "justifyContent": "space-around",
            "width": "100%",
            "marginTop": "20px"
        }
    )

    waste_comp_section = waste_kpi_cards

    # Then make sure your callback returns all four sections like so:
    return district_card, pop_section, waste_char_section, waste_comp_section

# --- Callbacks to toggle each collapsible section ---
@app.callback(
    [Output("collapse-pop", "is_open"),
     Output("collapse-waste-char", "is_open"),
     Output("collapse-waste-comp", "is_open")],
    [Input("toggle-pop", "n_clicks"),
     Input("toggle-waste-char", "n_clicks"),
     Input("toggle-waste-comp", "n_clicks")],
    [State("collapse-pop", "is_open"),
     State("collapse-waste-char", "is_open"),
     State("collapse-waste-comp", "is_open")]
)
def toggle_sections(n_pop, n_waste_char, n_waste_comp, is_open_pop, is_open_waste_char, is_open_waste_comp):
    ctx = dash.callback_context

    # If no button has been clicked, keep all sections closed.
    if not ctx.triggered:
        return False, False, False

    # Get the ID of the button that triggered the callback
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Set only the section corresponding to the clicked button to open
    return (
        True if button_id == "toggle-pop" else False,
        True if button_id == "toggle-waste-char" else False,
        True if button_id == "toggle-waste-comp" else False,
    )

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)