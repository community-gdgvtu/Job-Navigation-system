import os
import streamlit as st
import pandas as pd
import pydeck as pdk
from google import genai
import json
import psycopg2

# --- CONFIGURATION ---
API_KEY = os.environ.get("GEMINI_API_KEY")
DB_PASS = "your_db_password_here"

if not API_KEY:
    st.error("❌ GEMINI_API_KEY environment variable not set. Please set it in your terminal.")
    st.stop()

client = genai.Client(api_key=API_KEY)
st.set_page_config(page_title="Real-Time Belagavi Job Hunter", layout="wide")

# --- DATABASE FUNCTION ---
def save_to_db(title, company, lat, lng):
    try:
        conn = psycopg2.connect(
            host="127.0.0.1", port="5432", database="postgres", 
            user="postgres", password=DB_PASS
        )
        cur = conn.cursor()
        point = f'POINT({lng} {lat})'
        query = "INSERT INTO jobs_map (title, company, location) VALUES (%s, %s, ST_GeomFromText(%s, 4326));"
        cur.execute(query, (title, company, point))
        conn.commit()
        return True, f"Saved {company} to database."
    except Exception as e:
        return False, f"Database not connected (Map will work). Error: {e}"
    finally:
        if 'conn' in locals() and conn: 
            conn.close()

# --- UI SECTION ---
st.title("🛰️ Real-Time Belagavi Job Hunter")
st.write("Enter what you're looking for and where. I'll find it, map it, and sync it.")

col1, col2 = st.columns(2)
with col1:
    target_job = st.text_input("What job are you looking for?", placeholder="e.g. Mechanical Engineer")
with col2:
    target_area = st.text_input("Where in Belagavi?", placeholder="e.g. Udyambag")

search_button = st.button("🔍 Hunt & Map Jobs Now", type="primary")

# --- INTERACTIVE AGENT LOGIC ---
if search_button and target_job and target_area:
    with st.spinner(f"Agent is scanning {target_area} for {target_job} roles..."):
        prompt = f"""
        Act as a real-time local business and job locator. 
        Find 3-5 actual companies or locations in the '{target_area}' area of Belagavi 
        that would likely have '{target_job}' roles. 
        Return ONLY a JSON list with: 'company', 'lat', 'lng'.
        Example: [{{"company": "Company Name", "lat": 15.85, "lng": 74.50}}]
        """
        
        try:
            # 1. Get Data from Gemini
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            clean_json = response.text.replace('```json', '').replace('```', '').strip()
            job_data = json.loads(clean_json)
            df = pd.DataFrame(job_data)

            st.success(f"Successfully mapped {len(df)} locations!")
            
            # Save to Database in the background (using toast popups to save UI space)
            for index, row in df.iterrows():
                success, msg = save_to_db(target_job, row['company'], row['lat'], row['lng'])
                if success:
                    st.toast(msg, icon="✅") 
                else:
                    st.toast(msg, icon="⚠️") 

            # --- SPLIT LAYOUT: Map (Left) & Job List (Right) ---
            map_col, list_col = st.columns([3, 1])

            with map_col:
                st.write("### 🗺️ Job Map")
                view_state = pdk.ViewState(
                    latitude=df['lat'].mean(),
                    longitude=df['lng'].mean(),
                    zoom=13.5,
                    pitch=0
                )

                # Google Maps-style red pin dots
                scatter_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df,
                    get_position=["lng", "lat"],
                    get_fill_color=[234, 67, 53, 200], # Google Red
                    get_radius=120,
                    pickable=True
                )

                # Clean text labels above the pins
                text_layer = pdk.Layer(
                    "TextLayer",
                    data=df,
                    get_position=["lng", "lat"],
                    get_text="company",
                    get_size=14,
                    get_color=[0, 0, 0, 255], 
                    get_alignment_baseline="'bottom'",
                    get_pixel_offset=[0, -15]
                )

                # Render the map with a standard road layout and hover tooltips
                st.pydeck_chart(pdk.Deck(
                    layers=[scatter_layer, text_layer],
                    initial_view_state=view_state,
                    map_style="road",
                    tooltip={"html": "<b>{company}</b>", "style": {"backgroundColor": "white", "color": "black", "padding": "10px", "borderRadius": "5px"}}
                ))

            with list_col:
                st.write("### 🏢 Available Roles")
                # Create a card-like display for each job in the side panel
                for index, row in df.iterrows():
                    st.info(f"**{row['company']}**\n\n📍 Lat: {round(row['lat'], 4)}\n\n📍 Lng: {round(row['lng'], 4)}")

        except Exception as e:
            st.error(f"Agent encountered an error: {e}")

else:
    st.info("Waiting for input...")