# GeoAI South Asia Drought Monitoring & Risk Assessment Platform
# Part 1/3
# ==========================================================

# ==========================================================
# IMPORT LIBRARIES
# ==========================================================

import streamlit as st
import pandas as pd
import geopandas as gpd
import pydeck as pdk
import plotly.express as px
import numpy as np

from shapely.geometry import Polygon, MultiPolygon


# ==========================================================
# STREAMLIT CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="GeoAI South Asia Drought Monitoring Platform",
    page_icon="🌍",
    layout="wide"
)


# ==========================================================
# TITLE
# ==========================================================

st.title("🌍 TerraPulse")

st.markdown("""
**AI-based drought assessment platform for South Asia**

**Study Region:** South Asia
""")


# ==========================================================
# FILE PATHS
# ==========================================================

CSV_FILE = (
    "https://drive.google.com/uc?"
    "export=download&id=1v444HE4Pf9bnlA5g6GuW66a2Gf98ecNw"
)


GEOJSON_FILE = (
    "https://drive.google.com/uc?"
    "export=download&id=1snmcDuol7nstpzHxYlXYZ9zmrxwnoP1G"
)


# ==========================================================
# LOAD CSV DATA
# ==========================================================

@st.cache_data
def load_csv():

    try:
        df = pd.read_csv(CSV_FILE)

        df["DATE"] = pd.to_datetime(df["DATE"])

        return df

    except Exception as e:
        st.error(f"CSV loading error: {e}")
        st.stop()


# ==========================================================
# LOAD GEOJSON DATA
# ==========================================================

@st.cache_data
def load_geojson():

    try:

        gdf = gpd.read_file(GEOJSON_FILE)

        return gdf


    except Exception as e:

        st.error(f"GeoJSON loading error: {e}")

        st.stop()



# ==========================================================
# INITIALIZE DATA
# ==========================================================

df = load_csv()

hex_gdf = load_geojson()



# ==========================================================
# DATA VALIDATION
# ==========================================================

# Uncomment this temporarily if you need to check columns
# st.write(df.columns.tolist())


required_columns = [
    "hex_id",
    "DATE",
    "spi",
    "ndvi",
    "lst",
    "AI_Drought_Forecast",
    "Drought_Risk_Index",
    "Drought_Class"
]


missing_columns = [
    col
    for col in required_columns
    if col not in df.columns
]


if missing_columns:

    st.error(
        f"Missing columns in CSV: {missing_columns}"
    )

    st.stop()



# ==========================================================
# GEOJSON VALIDATION
# ==========================================================

if "hex_id" not in hex_gdf.columns:

    st.error(
        "GeoJSON does not contain 'hex_id' column"
    )

    st.stop()



# ==========================================================
# PREPARE DATA TYPES
# ==========================================================

df["hex_id"] = df["hex_id"].astype(str)

hex_gdf["hex_id"] = hex_gdf["hex_id"].astype(str)



# ==========================================================
# CHECK GEOMETRY
# ==========================================================

if hex_gdf.geometry.is_empty.any():

    st.warning(
        "Some geometries are empty. Please check GeoJSON."
    )


# ==========================================================
# FIX HEX_ID DATA TYPES
# ==========================================================

df["hex_id"] = (
    pd.to_numeric(
        df["hex_id"],
        errors="coerce"
    )
    .fillna(-1)
    .astype(int)
    .astype(str)
)


hex_gdf["hex_id"] = (
    pd.to_numeric(
        hex_gdf["hex_id"],
        errors="coerce"
    )
    .fillna(-1)
    .astype(int)
    .astype(str)
)


# ==========================================================
# GEOMETRY CONVERSION
# Polygon + MultiPolygon Support
# ==========================================================

def geometry_to_coordinates(geom):

    coordinates = []


    if isinstance(geom, Polygon):

        coordinates.append(

            [
                list(point)

                for point in geom.exterior.coords

            ]

        )


    elif isinstance(geom, MultiPolygon):

        for polygon in geom.geoms:

            coordinates.append(

                [
                    list(point)

                    for point in polygon.exterior.coords

                ]

            )


    return coordinates



hex_gdf["coordinates"] = (

    hex_gdf.geometry.apply(
        geometry_to_coordinates
    )

)



# ==========================================================
# MERGE CHECK
# ==========================================================

available_hex = set(
    hex_gdf["hex_id"]
)


available_data_hex = set(
    df["hex_id"]
)


common_hex = (

    available_hex

    & available_data_hex

)


if len(common_hex) == 0:

    st.error(
        "No matching hex_id found between GeoJSON and CSV"
    )

    st.stop()



# ==========================================================
# AVAILABLE DATES
# ==========================================================

dates = (

    df["DATE"]

    .sort_values()

    .unique()

)


# ==========================================================
# DROUGHT COLOUR FUNCTIONS
# ==========================================================


def drought_colour(value):

    colours = {

        "Normal": [34,139,34,180],

        "Moderate": [255,215,0,180],

        "Severe": [255,140,0,180],

        "Extreme": [220,20,60,180]

    }

    return colours.get(
        str(value),
        [128,128,128,150]
    )



def risk_colour(value):

    try:

        value = float(value)

    except:

        return [128,128,128,150]


    if value < 0.25:

        return [34,139,34,180]


    elif value < 0.50:

        return [255,215,0,180]


    elif value < 0.75:

        return [255,140,0,180]


    else:

        return [220,20,60,180]



# ==========================================================
# AVAILABLE DROUGHT CLASSES
# ==========================================================

available_classes = (

    df["Drought_Class"]

    .dropna()

    .unique()

    .tolist()

)



# ==========================================================
# SOUTH ASIA DEFAULT VIEW
# ==========================================================

south_asia_view = pdk.ViewState(

    latitude=20,

    longitude=78,

    zoom=4,

    pitch=0,

    bearing=0

)



# ==========================================================
# SIDEBAR CONTROLS
# ==========================================================

st.sidebar.header(
    "⚙️ Dashboard Controls"
)



selected_date = st.sidebar.selectbox(

    "📅 Select Date",

    dates,

    format_func=lambda x:

        pd.to_datetime(x).strftime("%Y-%m")

)



map_mode = st.sidebar.radio(

    "🗺 Map Display",

    [

        "Observed Drought",

        "AI Prediction",

        "Drought Risk Index"

    ]

)
# ==========================================================
# FILTER SELECTED DATE
# ==========================================================


date_df = df[
    df["DATE"] == pd.to_datetime(selected_date)
].copy()


# ==========================================================
# MERGE WITH HEX GEOMETRY
# ==========================================================


map_df = hex_gdf.merge(

    date_df,

    on="hex_id",

    how="inner"

)
if map_df.empty:

    st.warning(
        "No drought data available for this date."
    )

    st.stop()


# ==========================================================
# COLOUR ASSIGNMENT
# ==========================================================


if map_mode == "Observed Drought":

    map_df["color"] = (

        map_df["Drought_Class"]
        .apply(drought_colour)

    )


    tooltip_label = "Observed Drought"



elif map_mode == "AI Prediction":

    prediction_column = None


    if "AI_Drought_Forecast" in map_df.columns:

        prediction_column = "AI_Drought_Forecast"


    elif "Predicted_Drought" in map_df.columns:

        prediction_column = "Predicted_Drought"


    else:

        prediction_column = "Drought_Class"



    map_df["color"] = (

        map_df[prediction_column]
        .apply(drought_colour)

    )


    tooltip_label = "AI Prediction"



else:


    map_df["color"] = (

        map_df["Drought_Risk_Index"]
        .apply(risk_colour)

    )


    tooltip_label = "Risk Index"




# ==========================================================
# KPI CALCULATIONS
# ==========================================================


mean_spi = map_df["spi"].mean()

mean_ndvi = map_df["ndvi"].mean()

mean_lst = map_df["lst"].mean()

mean_risk = map_df["Drought_Risk_Index"].mean()



# ==========================================================
# KPI CARDS
# ==========================================================


st.subheader(
    f"📊 Climate Indicators - {pd.to_datetime(selected_date).strftime('%B %Y')}"
)



col1, col2, col3, col4 = st.columns(4)



with col1:

    st.metric(

        "🌧 Mean SPI",

        f"{mean_spi:.2f}"

    )



with col2:

    st.metric(

        "🌱 Mean NDVI",

        f"{mean_ndvi:.3f}"

    )



with col3:

    st.metric(

        "🌡 Mean LST",

        f"{mean_lst:.2f}"

    )



with col4:

    st.metric(

        "⚠ Mean Risk Index",

        f"{mean_risk:.2f}"

    )



# ==========================================================
# PYDECK MAP
# ==========================================================


st.subheader(
    f"🗺 South Asia {tooltip_label} Map"
)



layer = pdk.Layer(

    "PolygonLayer",

    data=map_df,

    get_polygon="coordinates",

    get_fill_color="color",

    get_line_color=[80,80,80],

    line_width_min_pixels=0.5,

    pickable=True,

    auto_highlight=True

)



tooltip = {

    "html":

    """
    <b>Hex ID:</b> {hex_id}<br/>
    <b>Date:</b> {DATE}<br/>
    <b>SPI:</b> {spi}<br/>
    <b>NDVI:</b> {ndvi}<br/>
    <b>LST:</b> {lst}<br/>
    <b>Drought Class:</b> {Drought_Class}<br/>
    <b>Risk Index:</b> {Drought_Risk_Index}
    """,

    "style":

    {

        "backgroundColor": "black",

        "color": "white"

    }

}



deck = pdk.Deck(

    layers=[layer],

    initial_view_state=south_asia_view,

    tooltip=tooltip

)



st.pydeck_chart(deck, height=650)



# ==========================================================
# LEGEND
# ==========================================================


st.subheader("📌 Drought Classification Legend")


legend_cols = st.columns(4)



legend_items = [

    ("🟩", "Normal"),

    ("🟨", "Moderate"),

    ("🟧", "Severe"),

    ("🟥", "Extreme")

]



for col, item in zip(
    legend_cols,
    legend_items
):

    with col:

        st.markdown(

            f"""
            {item[0]} **{item[1]}**
            """

        )

# ==========================================================
# TIME SERIES ANALYSIS
# ==========================================================


st.divider()

st.subheader("📈 Climate Trend Analysis")



# Select hexagon for trend analysis

selected_hex = st.selectbox(

    "Select Hexagon for Historical Trend",

    sorted(df["hex_id"].unique())

)



hex_history = df[

    df["hex_id"] == selected_hex

].sort_values("DATE")




# ==========================================================
# TREND CHARTS
# ==========================================================


col1, col2 = st.columns(2)



with col1:

    st.markdown(
        "### 🌧 SPI Trend"
    )

    st.line_chart(

        hex_history.set_index("DATE")["spi"]

    )



with col2:

    st.markdown(
        "### 🌱 NDVI Trend"
    )

    st.line_chart(

        hex_history.set_index("DATE")["ndvi"]

    )



col3, col4 = st.columns(2)



with col3:

    st.markdown(
        "### 🌡 Land Surface Temperature"
    )

    st.line_chart(

        hex_history.set_index("DATE")["lst"]

    )



with col4:

    st.markdown(
        "### ⚠ Drought Risk Index"
    )

    st.line_chart(

        hex_history.set_index("DATE")
        ["Drought_Risk_Index"]

    )




# ==========================================================
# AI FORECAST SECTION
# ==========================================================


st.divider()

st.subheader(
    "🤖 AI Drought Early Warning Prediction"
)



current_hex = map_df[

    map_df["hex_id"] == selected_hex

]



if len(current_hex) > 0:


    prediction_row = current_hex.iloc[0]



    col1, col2, col3, col4 = st.columns(4)



    with col1:

        st.metric(

            "AI Forecast",

            prediction_row["AI_Drought_Forecast"]

        )



    with col2:

        st.metric(

            "Risk Level",

            prediction_row["Drought_Class"]

        )



    with col3:

        st.metric(

            "Risk Index",

            round(

                prediction_row["Drought_Risk_Index"],

                3

            )

        )


with col4:

    if "Future_SPI" in prediction_row.index:

        st.metric(
            "SPI Forecast",
            round(
                prediction_row["Future_SPI"],
                2
            )
        )

    else:

        st.metric(
            "SPI Forecast",
            "N/A"
        )





# ==========================================================
# PROBABILITY DISTRIBUTION
# ==========================================================


st.markdown(
    "### Prediction Probability"
)



prob_columns = [

    "Normal_Probability",

    "Moderate_Probability",

    "Severe_Probability",

    "Extreme_Probability"

]



available_probs = []


if "prediction_row" in locals():

    available_probs = [

        c for c in prob_columns

        if c in prediction_row.index

    ]



if available_probs:


    probability_df = pd.DataFrame(

        {

            "Class":

            [

                c.replace("_Probability","")

                for c in available_probs

            ],

            "Probability":

            [

                prediction_row[c]

                for c in available_probs

            ]

        }

    )


    probability_df = probability_df.set_index(
        "Class"
    )


    st.bar_chart(
        probability_df
    )



# ==========================================================
# CURRENT REGION STATISTICS
# ==========================================================


st.divider()

st.subheader(
    "🌏 South Asia Current Situation"
)



risk_counts = (

    map_df["Drought_Class"]

    .value_counts()

)



col1, col2, col3, col4 = st.columns(4)



classes = [

    "Normal",

    "Moderate",

    "Severe",

    "Extreme"

]


for col, cls in zip(

    [

        col1,

        col2,

        col3,

        col4

    ],

    classes

):


    with col:

        st.metric(

            cls,

            int(

                risk_counts.get(

                    cls,

                    0

                )

            )

        )





# ==========================================================
# AI MODEL INFORMATION
# ==========================================================


st.divider()


with st.expander("ℹ About this system"):

    st.write(
    """
    GeoAI South Asia Drought Early Warning System.

    Combines:
    - SPI drought index
    - NDVI vegetation condition
    - Land Surface Temperature
    - Machine Learning prediction

    Model:
    Random Forest classifier

    Output:
    Monthly drought risk prediction.
    """
    )



# ==========================================================
# DATA TABLE
# ==========================================================


st.divider()

st.subheader(
    "📋 Current Month Data"
)


show_columns = [

    "hex_id",

    "spi",

    "ndvi",

    "lst",

    "Drought_Risk_Index",

    "Drought_Class",

    "AI_Drought_Forecast"

]


available_columns = [

    c for c in show_columns

    if c in map_df.columns

]


st.dataframe(

    map_df[available_columns]

    .reset_index(drop=True),

    use_container_width=True

)



# ==========================================================
# FOOTER
# ==========================================================


st.divider()


st.markdown(

"""

---

## 🌍 GeoAI South Asia Drought Monitoring System


Developed using:

- Python
- Streamlit
- PyDeck
- GeoPandas
- Remote Sensing
- Machine Learning


**Data Sources**

SPI | NDVI | LST | Satellite-derived environmental indicators


Designed as an AI-assisted drought early warning prototype.

"""

)
