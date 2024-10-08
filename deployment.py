import streamlit as st
import pandas as pd
import geopandas as gpd
from keplergl import KeplerGl
import h3
import json
from shapely import wkt

# Function to convert CSV with WKT geometry back to GeoDataFrame
def csv_to_geojson(csv_file):
    dpz_csv = pd.read_csv(csv_file)
    
    # Assuming the geometry column is in WKT format, convert it back to geometries
    dpz_csv['geometry'] = dpz_csv['geometry'].apply(wkt.loads)
    
    # Convert back to a GeoDataFrame
    dpzs_gdf = gpd.GeoDataFrame(dpz_csv, geometry='geometry', crs="EPSG:4326")
    
    return dpzs_gdf

# Function to get the bounding box of all the data and calculate the center
def calculate_center(*gdfs):
    combined_bounds = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs).total_bounds
    minx, miny, maxx, maxy = combined_bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2
    return center_lat, center_lon

# Main function for the Streamlit app
def rides_h3():
    st.set_page_config(layout="wide")

    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", ["Hexagon and Searches Visualization", "CSV to GeoJSON Conversion"])

    if page == "Hexagon and Searches Visualization":
        st.title('Hexagon and Searches Visualization')

        # Upload necessary files for analysis
        st.sidebar.title("Upload Files")
        rides_file = st.sidebar.file_uploader("Upload the Rides CSV file:", type="csv")
        searches_file = st.sidebar.file_uploader("Upload the Searches CSV file:", type="csv")
        deployment_spots_file = st.sidebar.file_uploader("Upload the deployment spots downloaded from Admin", type="geojson")
        boundary_file = st.sidebar.file_uploader("Upload the Boundary GeoJSON file (Optional)", type="geojson")

        # Add a resolution selector for H3 hexagons
        resolution = st.sidebar.slider("Select H3 Resolution", min_value=5, max_value=10, value=8)

        if rides_file and searches_file and deployment_spots_file:
            # Read the uploaded rides CSV file
            rides_df = pd.read_csv(rides_file)

            # Read the uploaded searches CSV file
            searches_df = pd.read_csv(searches_file)

            # Split 'Location' column into separate latitude and longitude columns
            searches_df[['latitude', 'longitude']] = searches_df['Location'].str.split(',', expand=True)
            
            # Convert latitude and longitude columns to numeric
            searches_df['latitude'] = pd.to_numeric(searches_df['latitude'])
            searches_df['longitude'] = pd.to_numeric(searches_df['longitude'])

            # Read the uploaded deployment spots GeoJSON file
            dpzs = gpd.read_file(deployment_spots_file)

            # If boundary file is uploaded, read it
            if boundary_file:
                boundary_gdf = gpd.read_file(boundary_file)
            else:
                boundary_gdf = None

            # Rename columns for consistency
            rides_df.rename(columns={'Pickup Lat': 'Pickup_Lat', 'Pickup Lng': 'Pickup_Lng'}, inplace=True)

            # Create rides GeoDataFrame
            rides_gdf = gpd.GeoDataFrame(
                rides_df, geometry=gpd.points_from_xy(rides_df.Pickup_Lng, rides_df.Pickup_Lat), crs="EPSG:4326"
            )

            # Create searches GeoDataFrame (no H3 hex conversion, just points)
            searches_gdf = gpd.GeoDataFrame(
                searches_df, geometry=gpd.points_from_xy(searches_df.longitude, searches_df.latitude), crs="EPSG:4326"
            )

            # Hexagonal binning for rides data using H3
            rides_gdf['h3'] = rides_gdf.apply(lambda row: h3.geo_to_h3(row.geometry.y, row.geometry.x, resolution=resolution), axis=1)

            # Group rides by hexagon and count rides per hexagon
            rides_per_hex = rides_gdf.groupby('h3').size().reset_index(name='ride_count')

            # Convert H3 hexagons to GeoDataFrame for visualization
            rides_per_hex_gdf = gpd.GeoDataFrame(rides_per_hex, geometry=gpd.points_from_xy(
                rides_per_hex.h3.apply(lambda h: h3.h3_to_geo(h)[1]), 
                rides_per_hex.h3.apply(lambda h: h3.h3_to_geo(h)[0])), crs="EPSG:4326")

            # Calculate the center of the data for the map
            if boundary_gdf is not None:
                center_lat, center_lon = calculate_center(boundary_gdf)
            else:
                center_lat, center_lon = calculate_center(rides_per_hex_gdf, searches_gdf, dpzs)

            # Initialize Kepler.gl map with a larger height and centered on the data
            kepler_map = KeplerGl(height=1000)  # Adjusted height for a larger map

            # Add the hexagon data (rides) to Kepler.gl
            kepler_map.add_data(rides_per_hex_gdf, "Hexagon Data (Rides)")

            # Add the searches data as points to Kepler.gl
            kepler_map.add_data(searches_gdf, "Searches Data")

            # Add the deployment polygons (dpzs) to Kepler.gl
            kepler_map.add_data(dpzs, "Deployment Zones")

            # Set initial map view based on the calculated center
            kepler_map.config = {
                "version": "v1",
                "config": {
                    "mapState": {
                        "latitude": center_lat,
                        "longitude": center_lon,
                        "zoom": 11  # Adjust the zoom level as needed
                    }
                }
            }

            # Render the Kepler.gl map in Streamlit
            kepler_map_html = kepler_map._repr_html_()
            st.components.v1.html(kepler_map_html, height=800)  # Larger map view

    elif page == "CSV to GeoJSON Conversion":
        st.title("CSV to GeoJSON Conversion")

        # Upload a CSV file to convert to GeoJSON
        dpzs_csv_file = st.file_uploader("Upload Modified Deployment Zones CSV", type="csv")

        if dpzs_csv_file:
            dpzs_gdf = pd.read_csv(dpzs_csv_file)
            # Convert the 'geometry' column from WKT to GeoDataFrame
            dpzs_gdf['geometry'] = dpzs_gdf['geometry'].apply(wkt.loads)
            dpzs_geojson = gpd.GeoDataFrame(dpzs_gdf, geometry='geometry', crs="EPSG:4326").to_json()

            st.success("CSV converted back to GeoJSON successfully.")

            # Provide a download button for the new GeoJSON
            st.download_button(
                label="Download GeoJSON",
                data=dpzs_geojson,
                file_name="deployment_zones.geojson",
                mime="application/json"
            )

        # Provide download button for original DPZ GeoJSON file as CSV
        deployment_spots_file = st.file_uploader("Upload Original Deployment Spots GeoJSON", type="geojson")
        if deployment_spots_file:
            dpzs = gpd.read_file(deployment_spots_file)
            dpzs_csv = dpzs.to_csv(index=False)

            st.download_button(
                label="Download Deployment Zones as CSV",
                data=dpzs_csv,
                file_name="deployment_zones.csv",
                mime="text/csv"
            )

# Run the Streamlit app
rides_h3()