import streamlit as st
import pandas as pd
import geopandas as gpd
import leafmap.foliumap as leafmap
from streamlit_folium import st_folium
from shapely import wkt
import h3

# Function to convert CSV with WKT geometry back to GeoDataFrame
def csv_to_geojson(csv_file):
    dpz_csv = pd.read_csv(csv_file)
    
    # Assuming the geometry column is in WKT format, convert it back to geometries
    dpz_csv['geometry'] = dpz_csv['geometry'].apply(wkt.loads)
    
    # Convert back to a GeoDataFrame
    dpzs_gdf = gpd.GeoDataFrame(dpz_csv, geometry='geometry', crs="EPSG:4326")
    
    return dpzs_gdf

# Main function for the Streamlit app
def rides_h3():
    st.set_page_config(layout="wide")

    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", ["Hexagon Visualization", "CSV to GeoJSON Conversion"])

    if page == "Hexagon Visualization":
        st.title('Rides Hexagon Visualization')

        # Upload necessary files for analysis
        st.sidebar.title("Upload Files")
        rides = st.sidebar.file_uploader("Upload the Rides CSV file:", type="csv")
        searches = st.sidebar.file_uploader("Upload the Searches CSV file:", type="csv")
        deployment_spots = st.sidebar.file_uploader("Upload the deployment spots downloaded from Admin", type="geojson")
        boundary_file = st.sidebar.file_uploader("Upload Boundary GeoJSON (Optional):", type="geojson")

        # Add a resolution selector for H3 hexagons
        resolution = st.sidebar.slider("Select H3 Resolution", min_value=5, max_value=10, value=8)

        if rides and searches and deployment_spots:
            rides_df = pd.read_csv(rides)
            searches_df = pd.read_csv(searches)
            dpzs = gpd.read_file(deployment_spots)

            # Rename coordinate columns for consistency
            rides_df.rename(columns={'Pickup Lat': 'Pickup_Lat', 'Pickup Lng': 'Pickup_Lng'}, inplace=True)
            rides_df.rename(columns={'Dropoff Lat': 'Dropoff_Lat', 'Dropoff Lng': 'Dropoff_Lng'}, inplace=True)

            # Create rides GeoDataFrame
            rides_gdf = gpd.GeoDataFrame(
                rides_df, geometry=gpd.points_from_xy(rides_df.Pickup_Lng, rides_df.Pickup_Lat), crs="EPSG:4326"
            )

            # Filter for finished rides only
            pickup_gdf = rides_gdf[rides_gdf['State'] == 'finished']

            # Hexagonal binning using H3 with user-selected resolution
            rides_gdf['h3'] = rides_gdf.apply(lambda row: h3.geo_to_h3(row.geometry.y, row.geometry.x, resolution=resolution), axis=1)

            # Group by hexagon and count rides per hexagon
            rides_per_hex = rides_gdf.groupby('h3').size().reset_index(name='ride_count')

            # Create the map using Leafmap
            berlin_coordinates = [52.51, 13.39]
            m = leafmap.Map(center=berlin_coordinates, zoom=12)

            # Add deployment spots GeoJSON to the map
            m.add_gdf(dpzs, layer_name="Deployment Spots", style={'fillColor': '#ff7800', 'color': '#ff7800'})

            # Visualize hexagons using Leafmap H3 support
            hex_ids = rides_per_hex['h3'].tolist()
            m.add_h3_data(hex_ids, resolution=resolution, value=rides_per_hex['ride_count'].tolist(), layer_name="H3 Hexagons")

            # Display the map in Streamlit
            st_folium(m, width=700, height=500)

            # Download deployment zones as CSV
            dpzs_csv = dpzs.to_csv(index=False)
            st.download_button(
                label="Download Deployment Zones as CSV",
                data=dpzs_csv,
                file_name="deployment_zones.csv",
                mime="text/csv"
            )

    elif page == "CSV to GeoJSON Conversion":
        st.title("CSV to GeoJSON Conversion")

        # Upload a CSV file to convert to GeoJSON
        dpzs_csv_file = st.file_uploader("Upload Modified Deployment Zones CSV", type="csv")

        if dpzs_csv_file:
            dpzs_gdf = csv_to_geojson(dpzs_csv_file)
            dpzs_geojson = dpzs_gdf.to_json()
            st.success("CSV converted back to GeoJSON successfully.")

            # Provide a download button for the new GeoJSON
            st.download_button(
                label="Download GeoJSON",
                data=dpzs_geojson,
                file_name="deployment_zones.geojson",
                mime="application/json"
            )

# Run the Streamlit app
rides_h3()        

