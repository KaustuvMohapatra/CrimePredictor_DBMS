# Filename: dashboard.py (UI ENHANCED VERSION)

import streamlit as st
import pandas as pd
import psycopg2
import folium
import geopandas as gpd
from streamlit_folium import st_folium
import plotly.express as px
import json

# --- Page Config (UI ENHANCEMENT: Set early for better loading experience) ---
st.set_page_config(page_title="Crime Analytics Dashboard", page_icon="🗺️", layout="wide")

# --- CONFIGURATION ---
DB_NAME = "crime_analytics"
DB_USER = "postgres"
DB_PASS = st.secrets["db_password"] # UI ENHANCEMENT: Load password from secrets for deployment
DB_HOST = "localhost"
DB_PORT = "5432"

# Define geographic regions for filtering
REGIONS = {
    "All India": {'box': [68.0, 8.0, 97.5, 37.0]},
    "North India": {'box': [72.0, 28.0, 85.0, 37.0]},
    "South India": {'box': [74.0, 8.0, 82.0, 18.0]},
    "West India": {'box': [68.0, 16.0, 78.0, 25.0]},
    "East India": {'box': [80.0, 20.0, 92.0, 28.0]},
    "Central India": {'box': [74.0, 21.0, 84.0, 26.0]}
}

# --- Database Connection & Caching ---
@st.cache_resource
def get_connection():
    # UI ENHANCEMENT: Added robust error handling for connection
    try:
        return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
    except psycopg2.OperationalError as e:
        st.error(f"🚨 Database Connection Error: Could not connect to the database. Please check your credentials and ensure the database is running. Details: {e}")
        st.stop()
conn = get_connection()

@st.cache_data(ttl=600)
def load_data(query):
    return pd.read_sql_query(query, conn)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://i.imgur.com/S3bL4qG.png", width=100)
    st.title("Analysis Control Panel")
    selected_region_name = st.selectbox("Select a Region to Analyze", list(REGIONS.keys()))
    
    st.markdown("---")
    
    try:
        all_crime_types_options = load_data('SELECT DISTINCT crime_type FROM crimes ORDER BY crime_type;')['crime_type'].tolist()
        selected_crime_types = st.multiselect("Filter Map by Crime Type", options=all_crime_types_options, default=[])
    except Exception as e:
        st.error(f"Could not load crime types: {e}")
        selected_crime_types = []

# --- Dynamic Values based on Sidebar ---
region_box = REGIONS[selected_region_name]['box']
map_center = [(region_box[1] + region_box[3]) / 2, (region_box[0] + region_box[2]) / 2]
map_zoom = 5 if selected_region_name == "All India" else 6

# --- Build Dynamic SQL WHERE Clause ---
sql_zone_region_filter = ""
if selected_region_name != "All India":
    sql_zone_region_filter = f"AND ST_Intersects(z.boundary, ST_MakeEnvelope({region_box[0]}, {region_box[1]}, {region_box[2]}, {region_box[3]}, 4326))"

sql_crime_type_filter = ""
if selected_crime_types:
    crime_filter_str = "','".join(selected_crime_types)
    sql_crime_type_filter = f"AND c.crime_type IN ('{crime_filter_str}')"

# --- MAIN DASHBOARD ---
st.title(f"🗺️ Regional Crime Analysis: {selected_region_name}")

# --- Data Loading with Spinner ---
@st.cache_data(ttl=600)
def get_choropleth_data(region_filter, crime_filter):
    query = f"""
        SELECT
            z.name AS "District", ST_AsGeoJSON(z.boundary) as boundary, COUNT(c.crime_id) AS "Crime Count"
        FROM zones z JOIN crimes c ON z.zone_id = c.zone_id
        WHERE 1=1 {region_filter} {crime_filter}
        GROUP BY z.zone_id, z.name, z.boundary ORDER BY "Crime Count" DESC;
    """
    return load_data(query)

with st.spinner('Crunching the numbers and drawing the map...'):
    choropleth_df = get_choropleth_data(sql_zone_region_filter, sql_crime_type_filter)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📍 Crime Hotspots by District")
    m = folium.Map(location=map_center, zoom_start=map_zoom, tiles="CartoDB positron", scrollWheelZoom=False)
    if not choropleth_df.empty:
        features = [{"type": "Feature", "geometry": json.loads(row["boundary"]), "properties": {"District": row["District"], "Crime Count": row["Crime Count"]}} for _, row in choropleth_df.iterrows()]
        gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
        
        choropleth = folium.Choropleth(
            geo_data=gdf, name='Crime Rate', data=gdf, columns=['District', 'Crime Count'],
            key_on='feature.properties.District', fill_color='YlOrRd', fill_opacity=0.8,
            line_opacity=0.2, legend_name='Total Reported Crimes by District'
        ).add_to(m)

        # UI ENHANCEMENT: Add a clean, informative tooltip on hover
        tooltip = folium.GeoJsonTooltip(
            fields=["District", "Crime Count"],
            aliases=["District:", "Crime Count:"],
            style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"),
            sticky=True
        )
        choropleth.geojson.add_child(tooltip)

    st_folium(m, use_container_width=True, height=500)

with col2:
    st.subheader("🏆 Top 10 Crime Hotspots")
    st.markdown(f"Highest crime districts within **{selected_region_name}**.")
    if not choropleth_df.empty:
        # UI ENHANCEMENT: Use st.metric for the #1 hotspot
        top_district_name = choropleth_df['District'].iloc[0].split(',')[0]
        top_district_count = choropleth_df['Crime Count'].iloc[0]
        st.metric(label=f"🥇 #1 Hotspot: {top_district_name}", value=f"{top_district_count:,} Reports")
        
        # Display the rest of the list
        top_zones_df = choropleth_df[['District', 'Crime Count']].head(10).reset_index(drop=True)
        st.dataframe(top_zones_df, use_container_width=True, hide_index=True)
    else:
        st.warning("No crime data available for this region or filter.")

# --- STATISTICAL BREAKDOWN SECTION ---
st.markdown("---")
st.subheader(f"📊 Statistical Breakdown for {selected_region_name}")

sql_point_region_filter = ""
if selected_region_name != "All India":
    sql_point_region_filter = f"AND ST_Contains(ST_MakeEnvelope({region_box[0]}, {region_box[1]}, {region_box[2]}, {region_box[3]}, 4326), location)"

# UI ENHANCEMENT: Use a container with a border for better visual grouping
with st.container(border=True):
    col3, col4 = st.columns(2)
    with col3:
        crime_dist_query = f'SELECT crime_type, COUNT(*) as count FROM crimes WHERE location IS NOT NULL {sql_point_region_filter} GROUP BY crime_type;'
        crime_dist_df = load_data(crime_dist_query)
        if not crime_dist_df.empty:
            # UI ENHANCEMENT: Use theme="streamlit" to match dark/light mode
            fig1 = px.bar(crime_dist_df.sort_values('count', ascending=False).head(10), 
                          x='count', y='crime_type', orientation='h', title=f"Top 10 Crime Types",
                          labels={'count': 'Total Reports', 'crime_type': ''}, template="streamlit")
            fig1.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No data for Crime Distribution.")

    with col4:
        hourly_query = f"SELECT EXTRACT(HOUR FROM timestamp) as hour, COUNT(*) as count FROM crimes WHERE location IS NOT NULL {sql_point_region_filter} GROUP BY hour ORDER BY hour;"
        hourly_df = load_data(hourly_query)
        if not hourly_df.empty:
            fig2 = px.line(hourly_df, x='hour', y='count', title=f"Hourly Crime Peaks",
                           labels={'hour': 'Hour of Day (24H)', 'count': 'Number of Crimes'}, markers=True, template="streamlit")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No data for Hourly Trends.")