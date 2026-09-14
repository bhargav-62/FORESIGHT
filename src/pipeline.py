import pandas as pd
from pathlib import Path

# -----------------------------
# 1. Define file paths
# -----------------------------
RAW_FILE = Path("data/inventory_data.csv")
PROCESSED_DIR = Path("data/processed")
OUTPUT_FILE = PROCESSED_DIR / "cleaned_data.csv"

# Create processed folder if it doesn't exist
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# 2. Load raw dataset
# -----------------------------
df = pd.read_csv(RAW_FILE)

print("Raw dataset shape:", df.shape)

# -----------------------------
# 3. Convert Date to datetime
# -----------------------------
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# -----------------------------
# 4. Remove duplicate rows
# -----------------------------
before = len(df)

df = df.drop_duplicates()

after = len(df)

print("Duplicates removed:", before - after)

# -----------------------------
# 5. Handle missing values
# -----------------------------
print("Missing values before cleaning:")
print(df.isnull().sum())

# Since validation showed no missing values,
# we keep the data unchanged here.

# -----------------------------
# 6. Sort data
# -----------------------------
df = df.sort_values(
    by=["Product_ID", "Date"]
).reset_index(drop=True)

# -----------------------------
# 7. Save processed dataset
# -----------------------------
df.to_csv(OUTPUT_FILE, index=False)

print("\nProcessed dataset saved successfully!")
print("File:", OUTPUT_FILE)
print("Final dataset shape:", df.shape)