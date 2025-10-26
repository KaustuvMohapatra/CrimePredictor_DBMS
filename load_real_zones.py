# Filename: load_real_zones.py (CORRECTED CRS TYPO)

import psycopg2
import psycopg2.extras
import geopandas as gpd

# --- CONFIGURATION ---
DB_NAME = "crime_analytics"
DB_USER = "postgres"
DB_PASS = "Kaustuv@2005"  # Your password
DB_HOST = "localhost"
DB_PORT = "5432"

SHAPEFILE_PATH = "./gadm41_IND_2.shp"

try:
    # --- Database Connection ---
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
    cur = conn.cursor()
    print("✅ Database connection successful.")

    # --- 1. Wipe Old Zones Data ---
    print("🗑️  Wiping old zones data...")
    cur.execute("TRUNCATE TABLE zones RESTART IDENTITY CASCADE;")
    conn.commit()

    # --- 2. Alter column type to handle MultiPolygons ---
    try:
        print("🔧 Checking and updating boundary column type in 'zones' table...")
        alter_query = "ALTER TABLE zones ALTER COLUMN boundary TYPE geometry(Geometry, 4326);"
        cur.execute(alter_query)
        conn.commit()
        print("   -> Column 'boundary' is now set to a flexible GEOMETRY type.")
    except Exception as e:
        conn.rollback()
        print(f"   -> Could not alter table, it might be the correct type already. Error: {e}")

    # --- 3. Load the Real District Data from Shapefile ---
    print(f"🗺️  Loading real district boundaries from {SHAPEFILE_PATH}...")
    try:
        gdf = gpd.read_file(SHAPEFILE_PATH)
        # FIX: Changed underscore to a colon. This is the required format.
        gdf = gdf.to_crs("EPSG:4326")
        print(f"   -> Loaded {len(gdf)} initial shapes.")
    except Exception as e:
        print(f"❌ Could not read shapefile. Check path and related files (.shx, .dbf). Error: {e}")
        exit()

    # --- 4. Clean the data by merging duplicate district names ---
    print("✨ Cleaning data: Merging geometries for duplicate district names...")
    original_count = len(gdf)
    gdf = gdf.dissolve(by=['NAME_1', 'NAME_2']).reset_index()
    merged_count = len(gdf)
    print(f"   -> Merged {original_count - merged_count} duplicate entries. Final district count: {merged_count}.")

    # --- 5. Prepare and Insert Data into the Database ---
    zones_to_insert = []
    for index, row in gdf.iterrows():
        district_name = row['NAME_2']
        state_name = row['NAME_1']
        full_name = f"{district_name}, {state_name}"
        geometry_wkt = row['geometry'].wkt
        zone_type = "Urban"
        zones_to_insert.append((full_name, zone_type, f"SRID=4326;{geometry_wkt}"))

    print("   -> Inserting new zones into the database (this might take a moment)...")
    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO zones (name, type, boundary) VALUES %s",
        zones_to_insert
    )
    conn.commit()
    print(f"✅ Successfully inserted {len(zones_to_insert)} real zones.")

except Exception as e:
    print(f"❌ An error occurred: {e}")

finally:
    # --- 6. Clean up ---
    if 'conn' in locals() and conn is not None:
        cur.close()
        conn.close()
        print("🔌 Database connection closed.")