import pandas as pd

# Load dataset
df = pd.read_csv("data/inventory_data.csv")

print("========== DATA VALIDATION ==========")

# Convert Date temporarily for validation
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# 1. Check invalid dates
print("\n1. Invalid Dates:")
print(df["Date"].isna().sum())

# 2. Check negative values
numeric_columns = [
    "Price",
    "Discount",
    "On_Promotion",
    "Weekend",
    "Month",
    "DayOfWeek",
    "Current_Stock",
    "Sales_Quantity",
    "Revenue",
    "Supplier_Lead_Time",
    "Stockout_Risk",
    "Yesterday_Sales",
    "Avg_Sales_7Days"
]

print("\n2. Negative Values:")
for column in numeric_columns:
    negative_count = (df[column] < 0).sum()
    print(f"{column}: {negative_count}")

# 3. Check Product IDs
print("\n3. Product Information:")
print("Unique products:", df["Product_ID"].nunique())
print("Products with missing ID:", df["Product_ID"].isna().sum())

# 4. Check categories
print("\n4. Categories:")
print(df["Category"].value_counts())

# 5. Check date range
print("\n5. Date Range:")
print("Start:", df["Date"].min())
print("End:", df["Date"].max())

# 6. Check records per product
print("\n6. Records per Product:")
records_per_product = df.groupby("Product_ID").size()
print(records_per_product.describe())

# 7. Check records per date
print("\n7. Records per Date:")
records_per_date = df.groupby("Date").size()
print(records_per_date.describe())

# 8. Check Discount range
print("\n8. Discount Range:")
print("Minimum:", df["Discount"].min())
print("Maximum:", df["Discount"].max())

# 9. Check supplier lead time
print("\n9. Supplier Lead Time:")
print("Minimum:", df["Supplier_Lead_Time"].min())
print("Maximum:", df["Supplier_Lead_Time"].max())

# 10. Check binary columns
print("\n10. Binary Columns:")
for column in ["On_Promotion", "Weekend", "Stockout_Risk"]:
    print(column, "=>", sorted(df[column].unique()))

# 11. Check whether Revenue is consistent
calculated_revenue = (
    df["Sales_Quantity"]
    * df["Price"]
    * (1 - df["Discount"] / 100)
)

revenue_difference = (
    df["Revenue"] - calculated_revenue
).abs()

print("\n11. Revenue Consistency:")
print("Maximum revenue difference:", revenue_difference.max())
print("Rows with difference > 1:", (revenue_difference > 1).sum())

# 12. Check promotion vs discount
print("\n12. Promotion / Discount Check:")
print(
    pd.crosstab(
        df["On_Promotion"],
        df["Discount"] > 0
    )
)

print("\n========== VALIDATION COMPLETE ==========")