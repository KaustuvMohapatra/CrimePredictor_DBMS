# Filename: train_and_predict.py
import streamlit as st
import pandas as pd
import psycopg2
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
import numpy as np
from datetime import date, timedelta

# --- IMPORTANT: CONFIGURE YOUR DATABASE CONNECTION HERE ---
DB_NAME = "crime_analytics"
DB_USER = "postgres"
DB_PASS = st.secrets["db_password"] # The password you set for your user
DB_HOST = "localhost"
DB_PORT = "5432"

# --- 1. Fetch Historical Data from the Database ---
print("🔌 Connecting to the database...")
try:
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )
    # This query extracts the key features for our model: where and when crimes happened.
    sql_query = """
    SELECT
        zone_id,
        EXTRACT(ISODOW FROM timestamp) AS day_of_week, -- 1=Monday, 7=Sunday
        EXTRACT(HOUR FROM timestamp) AS hour_of_day
    FROM crimes
    WHERE timestamp >= NOW() - INTERVAL '1 year'; -- Use last year's data for training
    """
    df_crimes = pd.read_sql_query(sql_query, conn)
    print(f"✅ Successfully fetched {len(df_crimes)} crime records for training.")
except Exception as e:
    print(f"❌ Database connection or query failed: {e}")
    exit()


# --- 2. Feature Engineering: Prepare the Data for the Model ---
# A model needs to learn from both "crime" and "no crime" events.
# We will create a full dataset representing every hour, of every day, for every zone.
print("🛠️  Performing feature engineering...")

# Get all unique zone IDs from the database
all_zones = sorted(df_crimes['zone_id'].unique())

# Create a master list of all possible time slots
master_list = []
for zone in all_zones:
    for day in range(1, 8):      # 1 to 7 for Monday to Sunday
        for hour in range(24):   # 0 to 23 for hours
            master_list.append([zone, day, hour])

df_master = pd.DataFrame(master_list, columns=['zone_id', 'day_of_week', 'hour_of_day'])

# Now, we count how many crimes occurred in each specific time slot
df_crime_counts = df_crimes.groupby(['zone_id', 'day_of_week', 'hour_of_day']).size().reset_index(name='crime_count')

# Merge the master list with the actual crime counts.
# Time slots with no crimes will have 'NaN', which we fill with 0.
df_full = pd.merge(df_master, df_crime_counts, on=['zone_id', 'day_of_week', 'hour_of_day'], how='left')
df_full['crime_count'].fillna(0, inplace=True)

# Our target variable 'y': 1 if a crime occurred, 0 otherwise.
df_full['is_crime'] = (df_full['crime_count'] > 0).astype(int)
print("   -> Training data prepared.")


# --- 3. Model Training ---
print("🧠 Training the prediction model...")

# Features (X): The inputs to the model (zone, day, hour)
# Target (y): What we want to predict (was there a crime?)
X = df_full[['zone_id', 'day_of_week', 'hour_of_day']]
y = df_full['is_crime']

# A machine learning model needs numerical input. We use OneHotEncoder to convert
# categorical features (like zone_id and day_of_week) into a numerical format.
encoder = OneHotEncoder(handle_unknown='ignore')
X_encoded = encoder.fit_transform(X)

# Split data into training and testing sets to evaluate the model
X_train, X_test, y_train, y_test = train_test_split(X_encoded, y, test_size=0.2, random_state=42, stratify=y)

# We use Logistic Regression, a simple and effective model for binary classification (crime/no crime).
# `class_weight='balanced'` helps the model learn from the minority class (crimes) more effectively.
model = LogisticRegression(class_weight='balanced', max_iter=1000)
model.fit(X_train, y_train)
accuracy = model.score(X_test, y_test)
print(f"   -> Model training complete. Accuracy: {accuracy:.2f}")


# --- 4. Generate and Store Predictions for the Future ---
print("🔮 Generating and storing future risk predictions...")
cur = conn.cursor()
# Clear any old predictions
cur.execute("TRUNCATE TABLE predictive_risks;")

# Generate predictions for the next 7 days
prediction_days = []
start_date = date.today()
for i in range(7):
    current_date = start_date + timedelta(days=i)
    day_of_week = current_date.isoweekday()

    for zone in all_zones:
        for hour in range(24):
            # Create the feature set for this specific time slot
            features_to_predict = [[zone, day_of_week, hour]]
            features_encoded = encoder.transform(features_to_predict)

            # Predict the probability of a crime. `predict_proba` returns [[P(no crime), P(crime)]]
            risk_score = model.predict_proba(features_encoded)[0][1]

            # We'll store risks in 4-hour time blocks (0, 4, 8, 12, 16, 20)
            time_block = (hour // 4) * 4

            # Insert into database. ON CONFLICT handles cases where we already have an entry
            # for that time block, and it averages the risk scores.
            sql_insert = """
                INSERT INTO predictive_risks (zone_id, prediction_date, time_block, risk_score)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (zone_id, prediction_date, time_block)
                DO UPDATE SET risk_score = (predictive_risks.risk_score + EXCLUDED.risk_score) / 2;
            """
            cur.execute(sql_insert, (int(zone), current_date, time_block, float(risk_score)))

conn.commit()
print("   -> Predictions for the next 7 days have been stored in the database.")


# --- 5. Clean up ---
cur.close()
conn.close()
print("✅ Prediction process complete. Connection closed.")