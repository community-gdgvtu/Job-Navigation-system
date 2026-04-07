import streamlit as st
import pandas as pd
import pydeck as pdk
from google import genai
import json
import psycopg2

# --- CONFIGURATION ---
# Warning: Hardcoding API keys is unsafe for production.
API_KEY = "AIzaSyBO1jQ_IcKyBok58GaJLEDSlNu8J3umD9g"
client = genai.Client(api_key=API_KEY)
DB_PASS = "AdvikaGurav_06"

st.set_page_config(page_title="Real-Time Belagavi Job Hunter", layout="wide")

# --- DATABASE FUNCTION ---
def save_to_db(title, company, lat, lng):
    """Attempts to save to Postgres/AlloyDB. Fails gracefully if DB is offline."""
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
        return False, f"Database not connected (Map will still work). Error: {e}"
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
        Example: [{{ "company": "Company Name", "lat": 15.85, "lng": 74.50 }}]
        """
        
        try:
            # 1. Get Data from Gemini
            response = client.models.generate_content(model="gemini-2.0-flash-lite", contents=prompt)
            clean_json = response.text.replace('```json', '').replace('```', '').strip()
            job_data = json.loads(clean_json)
            df = pd.DataFrame(job_data)
            df['display_text'] = "📍 " + df['company']

            # 2. Render the Map
            view_state = pdk.ViewState(
                latitude=df['lat'].mean(),
                longitude=df['lng'].mean(),
                zoom=13,
                pitch=0
            )

            layer = pdk.Layer(
                "TextLayer",
                df,
                get_position=["lng", "lat"],
                get_text="display_text",
                get_size=20,
                get_color=[0, 102, 204, 255], 
                get_alignment_baseline="'bottom'",
            )

            st.pydeck_chart(pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                map_style="light" 
            ))
            
            st.success(f"Successfully mapped {len(df)} locations!")
            
            # 3. Attempt to Save to Database & Show Status
            st.write("### Database Sync Status")
            for index, row in df.iterrows():
                success, msg = save_to_db(target_job, row['company'], row['lat'], row['lng'])
                if success:
                    st.toast(msg, icon="✅") # Small popups for success
                else:
                    st.warning(msg) # Warns user if DB is offline, but keeps app running
                    break # Stop trying if the database is clearly offline

            st.table(df[['company', 'lat', 'lng']])

        except Exception as e:
            st.error(f"Agent encountered an error: {e}")

else:
    st.info("Waiting for input...")