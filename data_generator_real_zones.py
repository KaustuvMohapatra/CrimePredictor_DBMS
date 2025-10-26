# Filename: data_generator_real_zones.py (FINAL & CORRECTED)

import psycopg2
import psycopg2.extras
from faker import Faker
import random
import json
from datetime import timezone

# --- CONFIGURATION ---
DB_NAME = "crime_analytics"
DB_USER = "postgres"
DB_PASS = "Kaustuv@2005"  # Your password
DB_HOST = "localhost"
DB_PORT = "5432"
CRIME_COUNT = 250_000
SUSPECT_COUNT = 5_000

# --- Database Connection ---
try:
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
    cur = conn.cursor()
    print("✅ Database connection successful.")
except Exception as e:
    print(f"❌ Could not connect to the database. Error: {e}")
    exit()

try:
    fake = Faker('en_IN')

    # --- 1. Clear Old Transactional Data ---
    print("🗑️  Wiping old crime and suspect data...")
    cur.execute("TRUNCATE TABLE crimes, suspects, reports, crime_suspects, predictive_risks RESTART IDENTITY CASCADE;")
    conn.commit()

    # --- 2. Fetch the REAL Zones from the Database ---
    print("🗺️  Fetching real zones from the database...")
    cur.execute("SELECT zone_id, type FROM zones")
    zones_db = cur.fetchall()
    if not zones_db:
        raise Exception("No zones found in the database. Please run 'load_real_zones.py' first.")
    print(f"   -> Found {len(zones_db)} real districts to populate.")

    # --- 3. Generate Suspects ---
    print(f"👤 Generating {SUSPECT_COUNT} suspects...")
    suspects_to_insert = []
    for _ in range(SUSPECT_COUNT):
        suspects_to_insert.append((
            fake.name(),
            fake.date_of_birth(minimum_age=18, maximum_age=70),
            json.dumps({'tags': random.sample(['repeat offender', 'gang affiliation', 'petty theft'], k=random.randint(1, 2))})
        ))
    psycopg2.extras.execute_values(cur, "INSERT INTO suspects (name, date_of_birth, tags) VALUES %s", suspects_to_insert)
    conn.commit()
    print(f"   -> Inserted {SUSPECT_COUNT} suspects.")

    # --- 4. Define Crime Patterns ---
    # This is the single, correct, expanded map of crime patterns.
    pattern_map = {
        'Urban': {
            'Theft': 0.25,
            'Assault': 0.15,
            'Cybercrime': 0.15,
            'Robbery': 0.10,
            'Vandalism': 0.10,
            'Drug Offense': 0.10,
            'Fraud': 0.10,
            'Burglary': 0.05
        },
        'Suburban': {
            'Burglary': 0.30,
            'Theft': 0.30,
            'Domestic Dispute': 0.20,
            'Vandalism': 0.15,
            'Assault': 0.05
        },
        'Rural': {
            'Theft': 0.40,
            'Domestic Dispute': 0.25,
            'Smuggling': 0.15,
            'Assault': 0.10,
            'Vandalism': 0.10
        },
        'Industrial': {
            'Theft': 0.50,
            'Smuggling': 0.20,
            'Vandalism': 0.15,
            'Assault': 0.10,
            'Fraud': 0.05
        }
    }

    # --- 5. Generate Crimes (without location first) ---
    print(f"🚨 Generating {CRIME_COUNT} crimes across all districts...")
    # THE FIX: The redundant, simple pattern_map has been REMOVED from here.
    crimes_to_insert = []
    for i in range(CRIME_COUNT):
        zone_id, zone_type = random.choice(zones_db)
        if zone_type not in pattern_map: zone_type = 'Urban'
        crime_type = random.choices(list(pattern_map[zone_type].keys()), weights=list(pattern_map[zone_type].values()), k=1)[0]
        timestamp = fake.date_time_between(start_date='-2y', end_date='now', tzinfo=timezone.utc)
        crimes_to_insert.append((crime_type, f'Case of {crime_type}', timestamp, zone_id))

    # --- 6. Bulk Insert Logic ---
    print("   -> Temporarily relaxing database constraints for bulk insert...")
    cur.execute("ALTER TABLE crimes ALTER COLUMN location DROP NOT NULL;")
    conn.commit()

    print("   -> Inserting crime records (this may take a while)...")
    sql_insert_query = "INSERT INTO crimes (crime_type, description, timestamp, zone_id) VALUES (%s, %s, %s, %s)"
    cur.executemany(sql_insert_query, crimes_to_insert)
    conn.commit()

    # --- 7. Set Crime Locations ---
    print("   -> Setting random locations for crimes within their zone boundaries...")
    cur.execute("""
        UPDATE crimes c SET location = (
            SELECT ST_PointOnSurface(z.boundary) FROM zones z WHERE z.zone_id = c.zone_id
        ) WHERE c.location IS NULL;
    """)
    conn.commit()
    print(f"   -> All {CRIME_COUNT} crime locations have been set.")

except Exception as e:
    print(f"❌ An error occurred during data generation: {e}")
    conn.rollback()

finally:
    # --- 8. ALWAYS re-enforce the constraint ---
    print("   -> Re-enforcing database constraints...")
    cur.execute("ALTER TABLE crimes ALTER COLUMN location SET NOT NULL;")
    conn.commit()
    print("   -> Database constraints restored.")

    # --- 9. Clean up connection ---
    if conn:
        cur.close()
        conn.close()
        print("✅ Data generation complete and connection closed.")