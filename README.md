# 🚀 Real-Time Belagavi Job Hunter

An AI-powered, real-time spatial mapping application that hunts for jobs in Belagavi using Google's Gemini API and visualizes them on an interactive Google Maps-style interface.

---

## ☁️ GCP Production Deployment Guide

⚠️ **IMPORTANT (READ FIRST): Use Existing Project**

Before starting, **DO NOT create a new GCP project**.

👉 Use the **same project** that was used for your **Day 0 / Day 1 setup**.  
This avoids billing issues, API permission problems, and configuration errors.

### ✅ Set Your Project in Cloud Shell

Run this command and replace `YOUR_PROJECT_ID` with your actual project ID:

```bash
gcloud config set project YOUR_PROJECT_ID
```

This project is designed to be deployed on a permanent **Google Compute Engine (VM)** running Ubuntu. This ensures your map and database stay online 24/7, unlike the temporary Cloud Shell environment.

---

### Step 1: Provision the Production Server
> 🖥️ **ENVIRONMENT:** Google Cloud Shell Terminal

Open your **Google Cloud Console** and activate the Cloud Shell (`>_` icon at the top right). Run the following commands to create the VM and open the firewall.

**1. Create the Virtual Machine:**
*(Deployed in the `asia-south1` region for the lowest latency to Belagavi)*
```bash
gcloud compute instances create job-hunter-prod \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --machine-type=e2-medium \
    --tags=http-server \
    --zone=asia-south1-a 
```

**2. Open Port 8080 for Streamlit:**
```bash
gcloud compute firewall-rules create allow-streamlit \
    --allow tcp:8080 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server
```

**3. SSH into your Production Server:**
```bash
gcloud compute ssh job-hunter-prod --zone=asia-south1-a
```

> ⚠️ **CRITICAL:** Once you run this command, your terminal prompt will change. You are now inside the permanent VM. All remaining steps must be run in this SSH terminal, NOT the Cloud Shell Editor.

---

### Step 2: Set Up the Spatial Database
> 🖥️ **ENVIRONMENT:** Production VM SSH Terminal

The application requires PostgreSQL and the PostGIS extension to store and map coordinates accurately.

**1. Install Database Dependencies:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib postgis git python3-venv python3-pip tmux nano -y
```

**2. Configure the Database User & Password:**
```bash
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'AdvikaGurav_06';"
```
*(Note: If you change the password here, remember it for Step 3).*

**3. Enable PostGIS & Create the Table:**
```bash
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS postgis;"

sudo -u postgres psql -c "
CREATE TABLE IF NOT EXISTS jobs_map (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    company VARCHAR(255),
    location GEOMETRY(Point, 4326)
);"
```

---

### Step 3: Clone & Configure the Application
> 🖥️ **ENVIRONMENT:** Production VM SSH Terminal

**1. Clone the Repository:**
```bash
# Replace with your actual GitHub repository URL
git clone [https://github.com/your-username/map-navigation.git](https://github.com/your-username/map-navigation.git)
cd map-navigation
```

**2. Set Up the Python Virtual Environment:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install Python Packages:**
```bash
pip install streamlit pandas pydeck google-genai psycopg2-binary
```

**4. Securely Set Your Gemini API Key:**
To keep your key safe and ensure it loads on boot, append it to your server's profile:
```bash
echo 'export GEMINI_API_KEY="YOUR_ACTUAL_API_KEY_HERE"' >> ~/.bashrc
source ~/.bashrc
```

**5. Update Database Credentials in Code:**
You must ensure the database password in your Python files matches the one you set in Step 2. Use the `nano` text editor to modify the files:
```bash
nano map_app.py
```
*Find the line `DB_PASS = "AdvikaGurav_06"` and change it if necessary. Press `Ctrl+O` then `Enter` to save, and `Ctrl+X` to exit.*

```bash
nano job_agent.py
```
*Repeat the same process to update `DB_PASS` in this file. Press `Ctrl+O` then `Enter` to save, and `Ctrl+X` to exit.*

---

### Step 4: Launch in Production Mode
> 🖥️ **ENVIRONMENT:** Production VM SSH Terminal

To ensure the application keeps running even after you close your browser, use a terminal multiplexer (`tmux`).

**1. Start a persistent background session:**
```bash
tmux new -s jobhunter
```

**2. Run the Streamlit Application:**
```bash
source venv/bin/activate
streamlit run map_app.py --server.port 8080 --server.address 0.0.0.0
```

**3. Detach and stop it Running:**
* Press **`Ctrl + C`** on your keyboard, let go, then press **`Ctrl + D`**.
* This safely detaches you from the session, stopping the app.
