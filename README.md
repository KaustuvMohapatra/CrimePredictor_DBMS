#  Crime Analytics and Prediction Dashboard

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)
![PostGIS](https://img.shields.io/badge/PostGIS-3.3-lightgrey.svg)

A comprehensive web application for the analysis, visualization, and prediction of crime patterns across India, built with Streamlit and a powerful PostgreSQL/PostGIS backend.

**[Live Demo Link Here]** <!-- Add your Streamlit Cloud URL here once deployed -->

![Dashboard Screenshot]<img width="2333" height="1318" alt="image" src="https://github.com/user-attachments/assets/aa485415-e5c2-4f81-b95d-9ef4c9f8ead2" />
 <!-- Add a screenshot named 'dashboard_screenshot.png' to your repo -->

---

### ► Key Features

*   **Interactive Choropleth Map:** Districts are colored by crime density for a clear view of hotspots.
*   **Dynamic Filtering:** Analyze data for all of India or specific regions (North, South, East, West, Central).
*   **Statistical Breakdowns:** View dynamic charts for crime distribution by type and hourly trends.
*   **Geospatially Accurate:** Uses real-world administrative boundaries from the GADM dataset.
*   **Predictive Analytics:** Trains a model to predict future crime likelihoods based on historical data.

---

### ► Tech Stack

*   **Frontend:** Streamlit
*   **Backend & Database:** Python, PostgreSQL, PostGIS
*   **Data Manipulation:** Pandas, GeoPandas
*   **Mapping:** Folium
*   **Plotting:** Plotly Express

---

### ► Setup and Running Locally

1.  **Database Setup:**
    *   Install PostgreSQL & PostGIS.
    *   Create a database (e.g., `crime_analytics`) and run the necessary `CREATE TABLE` commands.

2.  **Clone & Install:**
    ```bash
    git clone https://github.com/KaustuvMohapatra/CrimePredictor_DBMS.git
    cd CrimePredictor_DBMS
    python -m venv cr
    .\cr\Scripts\Activate.ps1
    pip install -r requirements.txt
    ```

3.  **Configure Secrets:**
    *   Create a folder: `.streamlit`
    *   Inside it, create a file: `secrets.toml`
    *   Add your DB password: `db_password = "YourPassword"`

4.  **Run the Data Pipeline:**
    *   *This only needs to be done once to populate your database.*
    ```bash
    # 1. Load the real district boundaries
    python load_real_zones.py

    # 2. Generate and insert crime data
    python data_generator_real_zones.py

    # 3. Train the ML model
    python train_and_predict.py
    ```

5.  **Launch the App:**
    ```bash
    streamlit run dashboard.py
    ```

---

### ► Project File Structure

*   `dashboard.py`: The main Streamlit application UI.
*   `load_real_zones.py`: One-time script to load district shapefiles into the database.
*   `data_generator_real_zones.py`: Generates and inserts mock crime data into the real zones.
*   `train_and_predict.py`: Trains the predictive ML model.
*   `requirements.txt`: Required Python libraries.
*   `.gitignore`: Specifies files for Git to ignore (e.g., virtual environment, secrets).
