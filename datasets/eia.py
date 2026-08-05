import os
import requests
import pandas as pd
import time

# Download EIA Electricity data for all States

API_KEY = os.environ['EIA_API_KEY']

BASE_URL = "https://api.eia.gov/v2/electricity/state-electricity-profiles/capability/data/"

PAGE_SIZE = 5000


all_rows = []
offset = 0

while True:

    params = {
        "api_key": API_KEY,
        "frequency": "annual",
        "data[0]": "capability",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": offset,
        "length": PAGE_SIZE,
    }

    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()

    data = response.json()["response"]["data"]

    if not data:
        break

    all_rows.extend(data)

    print(f"Downloaded {len(all_rows):,} rows...")

    offset += PAGE_SIZE
    time.sleep(0.1)

print(f"\nFinished downloading {len(all_rows):,} rows.")


eia_data = pd.DataFrame(all_rows)

# Convert data types
eia_data["period"] = pd.to_numeric(eia_data["period"], errors="coerce")
eia_data["capability"] = pd.to_numeric(eia_data["capability"], errors="coerce")

# Keep only 2024 data
latest_year = eia_data["period"].max()

eia_data_2024 = eia_data[eia_data["period"] == latest_year].copy()

print(f"Latest year: {latest_year}")
print(f"Rows for latest year: {len(eia_data_2024):,}")

# Sum capactiy by state
electricity_state_totals = (
    eia_data_2024
    .groupby(["stateId", "stateDescription"], as_index=False)["capability"]
    .sum()
    .sort_values("stateDescription")
)

print(electricity_state_totals.head())

# Save file
eia_data_2024.to_csv(
    f"eia_capability_by_technology_{latest_year}.csv",
    index=False
)

electricity_state_totals.to_csv(
    f"eia_state_total_capability_{latest_year}.csv",
    index=False
)

print("\nSaved:")
print(f"  - eia_capability_by_technology_{latest_year}.csv")
print(f"  - eia_state_total_capability_{latest_year}.csv")

