import json
import psycopg2
from google import genai

# --- CONFIGURATION ---
# Replace with your actual credentials if they differ
API_KEY = "AIzaSyBO1jQ_IcKyBok58GaJLEDSlNu8J3umD9g"
DB_PASS = "AdvikaGurav_06"
client = genai.Client(api_key=API_KEY)

def get_connection():
    """Establishes connection to local PostgreSQL/AlloyDB."""
    return psycopg2.connect(
        host="127.0.0.1", 
        port="5432", 
        database="postgres", 
        user="postgres", 
        password=DB_PASS
    )

def save_to_alloydb(title, company, lat, lng):
    """Saves the extracted job location to the database."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        # PostGIS POINT format: POINT(longitude latitude)
        point = f'POINT({lng} {lat})'
        query = "INSERT INTO jobs_map (title, company, location) VALUES (%s, %s, ST_GeomFromText(%s, 4326));"
        cur.execute(query, (title, company, point))
        conn.commit()
        print(f"✅ Successfully Mapped & Saved: {title} at {company}")
    except Exception as e:
        print(f"❌ Database Error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def gemini_job_agent(raw_text):
    """Uses Gemini 2.0 to turn messy text into structured GPS data."""
    print(f"🤖 Agent is analyzing: {raw_text[:50]}...")
    
    prompt = f"""
    Act as a professional Job Data Extractor for Belagavi, Karnataka.
    Extract the following from this job post and return it ONLY as a clean JSON object:
    'title', 'company', 'latitude', 'longitude'.
    
    If specific coordinates aren't in the text, estimate the exact latitude and longitude 
    based on the mentioned area or landmark in Belagavi.
    
    Job Post: {raw_text}
    
    Return format example: {{"title": "Role", "company": "Name", "latitude": 15.8, "longitude": 74.5}}
    """
    
    try:
        # Using the updated 2.0 Flash model
        response = client.models.generate_content(model="gemini-2.0-flash-lite", contents=prompt)
        
        # Clean the response to ensure only JSON remains
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_json)
        
        print("🎯 Analysis Complete.")
        print(json.dumps(data, indent=2))
        return data

    except Exception as e:
        print(f"❌ AI Extraction Error: {e}")
        return None

if __name__ == "__main__":
    # 1. Simulate a messy job post you might find on a local board
    sample_post = "Urgent: Hiring a Web Developer at Angadi College, Savadatti Road, Belagavi. Apply now!"
    
    # 2. Let the Agent process it
    extracted_data = gemini_job_agent(sample_post)
    
    # 3. If extraction worked, save it to your map database
    if extracted_data:
        save_to_alloydb(
            extracted_data['title'], 
            extracted_data['company'], 
            extracted_data['latitude'], 
            extracted_data['longitude']
        )