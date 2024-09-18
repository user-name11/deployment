import streamlit as st
import pandas as pd
import geopandas as gpd
import leafmap.foliumap as leafmap
from streamlit_folium import st_folium
import folium
import h3




st.set_page_config(layout="wide")

def rides_h3():
    st.title('Rides')
    
    #upload necessary files for analysis
    st.sidebar.title("Upload Files")
    rides = st.sidebar.file_uploader("Upload the Rides CSV file:", type="csv")
    seaches = st.sidebar.file_uploader("Upload the Searches CSV file:", type="csv")
    deployment_spots = st.sidebar.file_uploader("Upload the deployment spots downloaded from Admin", type="GeoJson")

    if rides and searches and deployment_spots:
        rides_df = pd.read_csv(rides)
        searches_df = pd.read_csv(searches)
        dpzs = gpd.read_file(deployment_spots)

