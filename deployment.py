import streamlit as st
import pandas as pd
import geopandas as gpd
from keplergl import KeplerGl
import h3
print(h3.__version__) 
import json
from shapely import wkt
from shapely import Polygon


polygon_cluster_h3_config = {
    "version": "v1",
    "config": {
        "visState": {
            "layers": [
                {
                    "id": "polygon-layer-id",
                    "type": "geojson",
                    "config": {
                        "dataId": "Deployment Zones",  # The dataId should match the actual dataset ID
                        "label": "Polygons",
                        "isVisible": True,
                        "visConfig": {
                            "opacity": 0.5,
                            "strokeOpacity": 1,
                            "thickness": 4,  # Stroke width set to 4
                            "strokeColor": [128, 0, 128]  # Purple stroke color in RGB format
                        }
                    }
                },
                {
                    "id": "cluster-layer-id",
                    "type": "point",
                    "config": {
                        "dataId": "Lost Rides Data",  # Corrected dataId for lost rides
                        "label": "Clusters",
                        "isVisible": True,
                        "columns": {
                            "radius": "Rides lost "  # Dynamic radius based on 'Rides lost' column
                        },
                        "visConfig": {
                            "radius": 30,  # Default radius
                            "opacity": 0.8,
                            "fixedRadius": False,
                            "cluster": True,
                            "clusterRadius": 50,
                            "colorRange": {
                                "colors": ["#E1F5FE", "#039BE5", "#0277BD"]
                            }
                        }
                    }
                },
                {
                    "id": "h3-layer-id",
                    "type": "hexagonId",
                    "config": {
                        "dataId": "Rides hex bin",  # Corrected dataId for hex bin
                        "label": "H3 Hexagons",
                        "isVisible": True,
                        "columns": {
                            "hex_id": "hex_id"  # Corrected column for H3 hexagons
                        },
                        "visConfig": {
                            "opacity": 0.7,
                            "colorRange": {
                                "colors": [
                                    "#0000FF",  # Blue
                                    "#0033FF",
                                    "#0066FF",
                                    "#0099FF",
                                    "#00CCFF",
                                    "#00FFFF",
                                    "#FFCCCC",
                                    "#FF9999",
                                    "#FF6666",
                                    "#FF3333",
                                    "#FF0000"   # Dark Red
                                ]
                            }
                        }
                    }
                }
            ]
        },
        "mapState": {
            "bearing": 0,
            "dragRotate": True,
            "latitude": 52.38989885855858,
            "longitude": 10.283403028497844,
            "pitch": 0,
            "zoom": 11,
            "isSplit": False
        },
        "mapStyle": {
            "styleType": "dark",
            "topLayerGroups": {},
            "visibleLayerGroups": {
                "label": True,
                "road": True,
                "border": False,
                "building": True,
                "water": True,
                "land": True,
                "3d building": False
            },
            "mapStyles": {}
        }
    }
}


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
        rides_file = st.sidebar.file_uploader("Upload the Rides CSV file from looker https://bolt.cloud.looker.com/looks/3523:", type="csv")
        lost_rides = st.sidebar.file_uploader("Upload the Rides lost CSV file from looker https://bolt.cloud.looker.com/dashboards/163:", type="csv")
        deployment_spots_file = st.sidebar.file_uploader("Upload the deployment spots downloaded from Admin", type="geojson")
        boundary_file = st.sidebar.file_uploader("Upload the Boundary GeoJSON file (Optional)", type="geojson")

        # Add a resolution selector for H3 hexagons
        resolution = st.sidebar.slider("Select H3 Resolution", min_value=5, max_value=10, value=8)

        # Add a filter button for vehicle type
        vehicle_filter = st.sidebar.radio("Filter by Vehicle Type", ["All", "scooters", "E-bikes"])

        if rides_file and lost_rides and deployment_spots_file:
            # Read the uploaded rides CSV file
            rides_df = pd.read_csv(rides_file)

            # Apply vehicle filter if not "All"
            if vehicle_filter != "All":
                rides_df = rides_df[rides_df['Vehicle Type Scooter or Bike'] == vehicle_filter]

            # Read the uploaded searches CSV file
            lost_rides_df = pd.read_csv(lost_rides, usecols=lambda column: column not in ['Unnamed: 0'])
            lost_rides_df = lost_rides_df.iloc[:-1]
            #lost_rides_df['Rides lost '] = lost_rides_df['Rides lost '].str.replace(',', '').astype(int)
            lost_rides_df= lost_rides_df[lost_rides_df['Rides lost '] !=0]
 
            # Split 'Location' column into separate latitude and longitude columns
            lost_rides_df[['latitude', 'longitude']] = lost_rides_df['Search Location 3 Digits'].str.split(',', expand=True)
            
            # Convert latitude and longitude columns to numeric
            lost_rides_df['latitude'] = pd.to_numeric(lost_rides_df['latitude'])
            lost_rides_df['longitude'] = pd.to_numeric(lost_rides_df['longitude'])
            
            


            # Read the uploaded deployment spots GeoJSON file
            dpzs = gpd.read_file(deployment_spots_file)
            dpz_hi = dpzs[dpzs['deployment_priority'] == 'high']
            dpz_mid = dpzs[dpzs['deployment_priority'] == 'medium']
            dpz_low = dpzs[dpzs['deployment_priority'] == 'low']
            

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

            # Hexagonal binning for rides data using H3
            rides_gdf['h3'] = rides_gdf.apply(lambda row: h3.geo_to_h3(row.geometry.y, row.geometry.x, resolution=resolution), axis=1)

            #remove cols from rides_gdf to prevent extra layer creation
            rides_gdf.drop(columns=['Pickup_Lat','Pickup_Lng','geometry'])

            # Group rides by hexagon and count rides per hexagon
            rides_per_hex = rides_gdf.groupby('h3').size().reset_index(name='ride_count')

            # Prepare DataFrame with H3 indices for 'hexagonId' layer
            rides_per_hex_gdf = rides_per_hex.rename(columns={'h3': 'hex_id'})

            # Ensure 'hex_id' is a string
            rides_per_hex_gdf['hex_id'] = rides_per_hex_gdf['hex_id'].astype(str)

            # Remove geometry column if it exists
            if 'geometry' in rides_per_hex_gdf.columns:
                rides_per_hex_gdf = rides_per_hex_gdf.drop(columns=['geometry'])

            # Convert H3 hexagons to GeoDataFrame for visualization
            rides_per_hex_gdf = gpd.GeoDataFrame(
            rides_per_hex,
            geometry=rides_per_hex['h3'].apply(lambda x: Polygon(h3.h3_to_geo_boundary(x, geo_json=True))),
            crs="EPSG:4326")
            rides_hex = rides_per_hex_gdf.drop(columns=['geometry'])


            # Calculate the center of the data for the map
            if boundary_gdf is not None:
                center_lat, center_lon = calculate_center(boundary_gdf)
            else:
                center_lat, center_lon = calculate_center(rides_per_hex_gdf, dpzs)

               # Update the mapState in the configuration
            polygon_cluster_h3_config['config']['mapState']['latitude'] = center_lat
            polygon_cluster_h3_config['config']['mapState']['longitude'] = center_lon
            
            #flow control
            lost_rides_df.drop(columns=['Search Location 3 Digits'], inplace=True)
            lost_rides_df.to_csv('lost.csv')
            rides_hex.to_csv('rides.csv')

            # Initialize Kepler.gl map without configuration
            kepler_map = KeplerGl(height=1000, data_to_layer=False)

            # Add the data to Kepler.gl
            kepler_map.add_data(rides_hex, "Rides binned")
            kepler_map.add_data(lost_rides_df, "Lost Rides")
            kepler_map.add_data(dpz_hi, "High Prio Deployment Zones")
            kepler_map.add_data(dpz_mid, "Mid Prio Deployment Zones")
            kepler_map.add_data(dpz_low, "Low Prio Deployment Zones")

            # Set the configuration after adding data
            kepler_map.config = polygon_cluster_h3_config


            # Render the Kepler.gl map in Streamlit
            kepler_map_html = kepler_map._repr_html_()
            st.components.v1.html(kepler_map_html, height=800)  # Larger map view
            print(json.dumps(kepler_map.config, indent=2))
            print(rides_per_hex_gdf)


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



