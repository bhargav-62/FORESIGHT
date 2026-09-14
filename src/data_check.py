import pandas as pd

# Load the dataset
df = pd.read_csv("data/inventory_data.csv")

# Basic information
print("\n===== DATASET SHAPE =====")
print(df.shape)

print("\n===== COLUMN NAMES =====")
print(df.columns.tolist())

print("\n===== FIRST 5 ROWS =====")
print(df.head())

print("\n===== DATA TYPES =====")
print(df.dtypes)

print("\n===== MISSING VALUES =====")
print(df.isnull().sum())

print("\n===== DUPLICATE ROWS =====")
print(df.duplicated().sum())

print("\n===== UNIQUE PRODUCTS =====")
print(df["Product_ID"].nunique())

print("\n===== CATEGORIES =====")
print(df["Category"].unique())

print("\n===== DATE RANGE =====")
print("Start:", df["Date"].min())
print("End:", df["Date"].max())

print("\n===== BASIC STATISTICS =====")
print(df.describe())