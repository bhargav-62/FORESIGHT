import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="FORESIGHT | Demand & Inventory Intelligence",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# PROJECT PATHS
# ============================================================

# dashboard.py is located at:
# D:\FORESIGHT\app\dashboard.py
#
# Therefore:
# APP_DIR    = D:\FORESIGHT\app
# PROJECT_DIR = D:\FORESIGHT

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent

PREDICTION_FILE = (
    PROJECT_DIR
    / "data"
    / "predictions"
    / "foresight_predictions.csv"
)

SKU_MASTER_FILE = (
    PROJECT_DIR
    / "data"
    / "sku_master.csv"
)


# ============================================================
# HELPER: SAFE NUMERIC COLUMN
# ============================================================

def safe_numeric(df, column, default=0.0):
    """
    Safely return a numeric Series.

    If the requested column does not exist,
    a default-valued Series is returned.
    """

    if column not in df.columns:
        return pd.Series(
            default,
            index=df.index,
            dtype=float
        )

    return pd.to_numeric(
        df[column],
        errors="coerce"
    ).fillna(default)


# ============================================================
# HELPER: INDIAN RUPEE FORMAT
# ============================================================

def format_inr(value):
    """
    Format values using Indian currency notation.
    """

    if value is None or pd.isna(value):
        return "₹ —"

    value = float(value)

    if value >= 10_000_000:
        return f"₹{value / 10_000_000:.2f} Cr"

    if value >= 100_000:
        return f"₹{value / 100_000:.2f} L"

    if value >= 1_000:
        return f"₹{value / 1_000:.1f} K"

    return f"₹{value:,.0f}"


# ============================================================
# HELPER: LATEST RECORD FOR EACH SKU
# ============================================================

def get_latest_snapshot(df):
    """
    Keep exactly one record per Product_ID.

    The latest available Date is used.
    This prevents the KPI from counting the same SKU
    multiple times across forecast dates.
    """

    if df.empty:
        return df.copy()

    if "Product_ID" not in df.columns:
        return df.copy()

    if "Date" not in df.columns:

        return (
            df
            .drop_duplicates(
                subset=["Product_ID"],
                keep="last"
            )
            .reset_index(drop=True)
        )

    valid_dates = df["Date"].dropna()

    if valid_dates.empty:

        return (
            df
            .drop_duplicates(
                subset=["Product_ID"],
                keep="last"
            )
            .reset_index(drop=True)
        )

    latest_date = valid_dates.max()

    latest_df = (
        df[
            df["Date"] == latest_date
        ]
        .copy()
    )

    latest_df = (
        latest_df
        .sort_values("Product_ID")
        .drop_duplicates(
            subset=["Product_ID"],
            keep="last"
        )
        .reset_index(drop=True)
    )

    return latest_df


# ============================================================
# BUSINESS IMPACT CALCULATIONS
# ============================================================

def calculate_business_impact(df):
    """
    Calculate all inventory and business-impact metrics.

    No artificial unit_cost is created.

    Since the supplied SKU master contains list_price but
    does not contain unit_cost, list_price is used as the
    available rupee valuation basis.
    """

    result = df.copy()

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    if "list_price" in result.columns:

        result["list_price"] = pd.to_numeric(
            result["list_price"],
            errors="coerce"
        )

    elif "Price" in result.columns:

        result["list_price"] = pd.to_numeric(
            result["Price"],
            errors="coerce"
        )

    else:

        result["list_price"] = 0.0

    result["list_price"] = (
        result["list_price"]
        .fillna(0)
    )


    # --------------------------------------------------------
    # INVENTORY UNITS
    # --------------------------------------------------------

    if "Avg_Stock" in result.columns:

        result["Inventory_Units"] = (
            safe_numeric(
                result,
                "Avg_Stock"
            )
        )

    elif "Current_Stock" in result.columns:

        result["Inventory_Units"] = (
            safe_numeric(
                result,
                "Current_Stock"
            )
        )

    else:

        result["Inventory_Units"] = 0.0


    # --------------------------------------------------------
    # PREDICTED DEMAND
    # --------------------------------------------------------

    predicted_demand = (
        safe_numeric(
            result,
            "Predicted_Demand"
        )
    )


    # --------------------------------------------------------
    # LEAD TIME DEMAND
    # --------------------------------------------------------

    if "Lead_Time_Demand" in result.columns:

        lead_time_demand = (
            safe_numeric(
                result,
                "Lead_Time_Demand"
            )
        )

    else:

        lead_time_days = (
            safe_numeric(
                result,
                "Avg_Lead_Time"
            )
        )

        lead_time_demand = (
            predicted_demand
            *
            lead_time_days
            /
            7.0
        )


    result["Calculated_Lead_Time_Demand"] = (
        lead_time_demand
    )


    # --------------------------------------------------------
    # STOCKOUT UNITS AT RISK
    # --------------------------------------------------------

    result["Stockout_Units_At_Risk"] = (
        lead_time_demand
        -
        result["Inventory_Units"]
    ).clip(
        lower=0
    )


    # --------------------------------------------------------
    # SALES AT RISK
    # --------------------------------------------------------

    result["Sales_At_Risk_INR"] = (
        result["Stockout_Units_At_Risk"]
        *
        result["list_price"]
    )


    # --------------------------------------------------------
    # OVERSTOCK THRESHOLD
    # --------------------------------------------------------

    if "Overstock_Threshold" in result.columns:

        overstock_threshold = (
            safe_numeric(
                result,
                "Overstock_Threshold"
            )
        )

    else:

        # Operational threshold:
        # 1.5 × predicted weekly demand
        overstock_threshold = (
            predicted_demand
            *
            1.5
        )


    result["Calculated_Overstock_Threshold"] = (
        overstock_threshold
    )


    # --------------------------------------------------------
    # OVERSTOCK UNITS
    # --------------------------------------------------------

    result["Overstock_Units"] = (
        result["Inventory_Units"]
        -
        overstock_threshold
    ).clip(
        lower=0
    )


    # --------------------------------------------------------
    # OVERSTOCK VALUE
    # --------------------------------------------------------

    result["Overstock_Value_INR"] = (
        result["Overstock_Units"]
        *
        result["list_price"]
    )


    # --------------------------------------------------------
    # CAPITAL LOCKED
    #
    # IMPORTANT:
    #
    # unit_cost is unavailable in the supplied data.
    #
    # Therefore we use:
    #
    # Inventory Units × actual list_price
    #
    # This prevents an artificial unit_cost.
    # --------------------------------------------------------

    result["Capital_Locked_INR"] = (
        result["Inventory_Units"]
        *
        result["list_price"]
    )


    # --------------------------------------------------------
    # STOCKOUT RISK
    # --------------------------------------------------------

    result["Stockout_Risk"] = (
        safe_numeric(
            result,
            "Predicted_Stockout_Risk"
        )
        .round()
        .astype(int)
    )


    # --------------------------------------------------------
    # OVERSTOCK RISK
    # --------------------------------------------------------

    result["Overstock_Risk"] = (
        safe_numeric(
            result,
            "Predicted_Overstock_Risk"
        )
        .round()
        .astype(int)
    )


    # --------------------------------------------------------
    # INVENTORY ACTION
    # --------------------------------------------------------

    result["Inventory_Action"] = np.select(

        [
            (
                (result["Stockout_Risk"] == 1)
                &
                (result["Overstock_Risk"] == 0)
            ),

            (
                (result["Stockout_Risk"] == 0)
                &
                (result["Overstock_Risk"] == 1)
            ),

            (
                (result["Stockout_Risk"] == 1)
                &
                (result["Overstock_Risk"] == 1)
            )
        ],

        [
            "REORDER NOW",
            "MARKDOWN / CLEAR",
            "WATCH / VOLATILE"
        ],

        default="HEALTHY"
    )


    return result


# ============================================================
# CHECK PREDICTION FILE
# ============================================================

if not PREDICTION_FILE.exists():

    st.error(
        "❌ Prediction file not found."
    )

    st.code(
        str(PREDICTION_FILE)
    )

    st.info(
        "Expected file location: "
        "D:\\FORESIGHT\\data\\predictions\\"
        "foresight_predictions.csv"
    )

    st.stop()


# ============================================================
# LOAD PREDICTION DATA
# ============================================================

try:

    df = pd.read_csv(
        PREDICTION_FILE
    )

except Exception as error:

    st.error(
        "❌ Unable to read prediction CSV."
    )

    st.exception(error)

    st.stop()


# ============================================================
# CHECK EMPTY
# ============================================================

if df.empty:

    st.error(
        "❌ Prediction file is empty."
    )

    st.stop()


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

df.columns = [
    str(column).strip()
    for column in df.columns
]


# ============================================================
# PRODUCT ID
# ============================================================

if "Product_ID" not in df.columns:

    possible_columns = [
        "Product ID",
        "product_id",
        "sku_id",
        "SKU_ID",
        "SKU"
    ]

    found_column = None

    for column in possible_columns:

        if column in df.columns:

            found_column = column
            break


    if found_column is None:

        st.error(
            "❌ Product_ID column is missing "
            "from prediction data."
        )

        st.stop()


    df["Product_ID"] = (
        df[found_column]
    )


df["Product_ID"] = (
    df["Product_ID"]
    .astype(str)
    .str.strip()
)


# ============================================================
# CATEGORY
# ============================================================

if "Category" not in df.columns:

    if "category" in df.columns:

        df["Category"] = (
            df["category"]
        )

    else:

        df["Category"] = "Unknown"


df["Category"] = (
    df["Category"]
    .fillna("Unknown")
    .astype(str)
    .str.strip()
)


# ============================================================
# DATE
# ============================================================

if "Date" in df.columns:

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )


# ============================================================
# NUMERIC COLUMNS
# ============================================================

numeric_columns = [
    "Weekly_Demand",
    "Predicted_Demand",
    "Avg_Stock",
    "Avg_Lead_Time",
    "Lead_Time_Demand",
    "Predicted_Stockout_Risk",
    "Predicted_Overstock_Risk",
    "Overstock_Threshold",
    "Reorder_Point",
    "Recommended_Order_Qty",
    "Price",
    "list_price",
    "unit_cost",
    "Current_Stock",
    "Sales_Quantity",
    "Revenue",
    "Discount",
    "On_Promotion"
]


for column in numeric_columns:

    if column in df.columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )


# ============================================================
# LOAD SKU MASTER
# ============================================================

if SKU_MASTER_FILE.exists():

    try:

        sku_master = pd.read_csv(
            SKU_MASTER_FILE
        )

        sku_master.columns = [
            str(column).strip()
            for column in sku_master.columns
        ]


        if "sku_id" in sku_master.columns:

            sku_master["sku_id"] = (
                sku_master["sku_id"]
                .astype(str)
                .str.strip()
            )


            # -----------------------------------------------
            # LIST PRICE
            # -----------------------------------------------

            if "list_price" in sku_master.columns:

                sku_master["list_price"] = (
                    pd.to_numeric(
                        sku_master["list_price"],
                        errors="coerce"
                    )
                )


            # -----------------------------------------------
            # MASTER COLUMNS
            # -----------------------------------------------

            master_columns = [
                "sku_id"
            ]


            if "list_price" in sku_master.columns:

                master_columns.append(
                    "list_price"
                )


            # -----------------------------------------------
            # REMOVE DUPLICATES
            # -----------------------------------------------

            master = (
                sku_master[
                    master_columns
                ]
                .drop_duplicates(
                    subset=["sku_id"]
                )
            )


            # -----------------------------------------------
            # MERGE
            # -----------------------------------------------

            df = df.merge(
                master,
                left_on="Product_ID",
                right_on="sku_id",
                how="left",
                suffixes=(
                    "",
                    "_master"
                )
            )


            df.drop(
                columns=[
                    "sku_id"
                ],
                inplace=True,
                errors="ignore"
            )


            # -----------------------------------------------
            # USE MASTER LIST PRICE
            # -----------------------------------------------

            if "list_price_master" in df.columns:

                if "list_price" in df.columns:

                    df["list_price"] = (
                        df["list_price"]
                        .fillna(
                            df["list_price_master"]
                        )
                    )

                else:

                    df["list_price"] = (
                        df["list_price_master"]
                    )


                df.drop(
                    columns=[
                        "list_price_master"
                    ],
                    inplace=True,
                    errors="ignore"
                )


    except Exception:

        # If SKU master cannot be read,
        # fall back to Price from prediction data.
        pass


# ============================================================
# FINAL PRICE FALLBACK
# ============================================================

if "list_price" not in df.columns:

    if "Price" in df.columns:

        df["list_price"] = pd.to_numeric(
            df["Price"],
            errors="coerce"
        )

    else:

        df["list_price"] = 0.0


else:

    if "Price" in df.columns:

        df["list_price"] = (
            pd.to_numeric(
                df["list_price"],
                errors="coerce"
            )
            .fillna(
                pd.to_numeric(
                    df["Price"],
                    errors="coerce"
                )
            )
        )

    else:

        df["list_price"] = (
            pd.to_numeric(
                df["list_price"],
                errors="coerce"
            )
        )


df["list_price"] = (
    df["list_price"]
    .fillna(0)
)


# ============================================================
# SORT DATA
# ============================================================

if "Date" in df.columns:

    df = (
        df
        .sort_values(
            [
                "Product_ID",
                "Date"
            ]
        )
        .reset_index(drop=True)
    )


# ============================================================
# SEASONAL-NAIVE BASELINE
# ============================================================

if (
    "Weekly_Demand" in df.columns
    and
    "Date" in df.columns
):

    df["Baseline_Demand"] = (
        df
        .groupby(
            "Product_ID"
        )[
            "Weekly_Demand"
        ]
        .shift(1)
    )

else:

    df["Baseline_Demand"] = np.nan


# ============================================================
# FORECAST INTERVAL
# ============================================================

if (
    "Weekly_Demand" in df.columns
    and
    "Predicted_Demand" in df.columns
):

    residuals = (
        df["Weekly_Demand"]
        -
        df["Predicted_Demand"]
    ).dropna()


    if len(residuals) > 1:

        residual_std = float(
            residuals.std()
        )

    else:

        residual_std = 0.0

else:

    residual_std = 0.0


df["Forecast_Lower_80"] = (
    safe_numeric(
        df,
        "Predicted_Demand"
    )
    -
    (
        1.2816
        *
        residual_std
    )
).clip(
    lower=0
)


df["Forecast_Upper_80"] = (
    safe_numeric(
        df,
        "Predicted_Demand"
    )
    +
    (
        1.2816
        *
        residual_std
    )
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "🎨 Appearance"
)

st.sidebar.divider()

st.sidebar.subheader(
    "🔎 Filters"
)


# ============================================================
# CATEGORY FILTER
# ============================================================

categories = sorted(
    df["Category"]
    .dropna()
    .unique()
    .tolist()
)


selected_category = st.sidebar.selectbox(
    "Category",
    [
        "All Categories"
    ]
    +
    categories
)


if selected_category == "All Categories":

    filtered = df.copy()

else:

    filtered = df[
        df["Category"]
        ==
        selected_category
    ].copy()


# ============================================================
# PRODUCT FILTER
# ============================================================

products = sorted(
    filtered["Product_ID"]
    .dropna()
    .unique()
    .tolist()
)


selected_product = st.sidebar.selectbox(
    "Product",
    [
        "All Products"
    ]
    +
    products
)


if selected_product == "All Products":

    filtered = filtered.copy()

else:

    filtered = filtered[
        filtered["Product_ID"]
        ==
        selected_product
    ].copy()


# ============================================================
# BUSINESS IMPACT AFTER FILTER
# ============================================================

filtered = calculate_business_impact(
    filtered
)


# ============================================================
# LATEST UNIQUE SKU SNAPSHOT
# ============================================================

latest_filtered = get_latest_snapshot(
    filtered
)


# ============================================================
# BUSINESS IMPACT AGAIN ON LATEST DATA
# ============================================================

latest_filtered = calculate_business_impact(
    latest_filtered
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "📦 FORESIGHT"
)

st.caption(
    "AI-Powered Demand Forecasting & Inventory Intelligence Platform"
)


st.success(
    "Prediction data loaded successfully • "
    f"{len(df):,} prediction records • "
    f"Showing {len(filtered):,} filtered records"
)


# ============================================================
# KPI SECTION
# ============================================================

st.header(
    "📊 Key Performance Indicators"
)


# ------------------------------------------------------------
# PRODUCTS
# ------------------------------------------------------------

products_count = (
    filtered[
        "Product_ID"
    ]
    .nunique()
)


# ------------------------------------------------------------
# PREDICTED DEMAND
# ------------------------------------------------------------

predicted_demand_total = (
    safe_numeric(
        filtered,
        "Predicted_Demand"
    )
    .sum()
)


# ------------------------------------------------------------
# STOCKOUT RISK
# ------------------------------------------------------------

stockout_risk_count = int(
    (
        latest_filtered[
            "Stockout_Risk"
        ]
        ==
        1
    )
    .sum()
)


# ------------------------------------------------------------
# AVERAGE STOCK
# ------------------------------------------------------------

average_stock = (
    latest_filtered[
        "Inventory_Units"
    ]
    .mean()
)


if pd.isna(average_stock):

    average_stock = 0.0


# ------------------------------------------------------------
# SALES AT RISK
# ------------------------------------------------------------

sales_at_risk = float(
    latest_filtered[
        "Sales_At_Risk_INR"
    ]
    .sum()
)


# ------------------------------------------------------------
# CAPITAL LOCKED
# ------------------------------------------------------------

capital_locked = float(
    latest_filtered[
        "Capital_Locked_INR"
    ]
    .sum()
)


# ============================================================
# KPI DISPLAY
# ============================================================

k1, k2, k3, k4, k5, k6 = st.columns(6)


with k1:

    st.metric(
        "📦 Products",
        f"{products_count:,}"
    )


with k2:

    st.metric(
        "📈 Predicted Demand",
        f"{predicted_demand_total:,.0f}"
    )


with k3:

    st.metric(
        "🚨 Stockout Risk",
        f"{stockout_risk_count:,}",
        help=(
            "Number of unique SKUs at stockout risk "
            "in the latest available forecast snapshot."
        )
    )


with k4:

    st.metric(
        "📦 Average Stock",
        f"{average_stock:,.1f}"
    )


with k5:

    st.metric(
        "💰 Sales at Risk",
        format_inr(
            sales_at_risk
        ),
        help=(
            "Stockout units at risk × actual SKU list price."
        )
    )


with k6:

    st.metric(
        "💵 Capital Locked",
        format_inr(
            capital_locked
        ),
        help=(
            "Current inventory units × actual SKU list price."
        )
    )


# ============================================================
# BUSINESS IMPACT EXPLANATION
# ============================================================

st.info(
    "💡 **Business Impact:** "
    "The supplied data contains actual SKU list prices "
    "but does not contain unit cost. Therefore FORESIGHT "
    "uses the actual list price for inventory valuation "
    "and does not create an artificial unit cost."
)


# ============================================================
# DEMAND FORECAST
# ============================================================

st.header(
    "📈 Demand Forecast"
)


if (
    "Date" in filtered.columns
    and
    "Predicted_Demand" in filtered.columns
):

    forecast_columns = [
        "Date",
        "Predicted_Demand",
        "Forecast_Lower_80",
        "Forecast_Upper_80"
    ]


    if "Weekly_Demand" in filtered.columns:

        forecast_columns.append(
            "Weekly_Demand"
        )


    if "Baseline_Demand" in filtered.columns:

        forecast_columns.append(
            "Baseline_Demand"
        )


    forecast = (
        filtered[
            forecast_columns
        ]
        .dropna(
            subset=["Date"]
        )
        .groupby(
            "Date",
            as_index=False
        )
        .sum()
        .sort_values(
            "Date"
        )
    )


    forecast_fig = go.Figure()


    # --------------------------------------------------------
    # ACTUAL DEMAND
    # --------------------------------------------------------

    if "Weekly_Demand" in forecast.columns:

        forecast_fig.add_trace(
            go.Scatter(
                x=forecast["Date"],
                y=forecast["Weekly_Demand"],
                mode="lines+markers",
                name="Actual Demand",
                line=dict(
                    width=3
                )
            )
        )


    # --------------------------------------------------------
    # BASELINE
    # --------------------------------------------------------

    if "Baseline_Demand" in forecast.columns:

        valid_baseline = (
            forecast[
                "Baseline_Demand"
            ]
            .notna()
        )


        if valid_baseline.any():

            forecast_fig.add_trace(
                go.Scatter(
                    x=forecast["Date"],
                    y=forecast["Baseline_Demand"],
                    mode="lines+markers",
                    name="Seasonal-Naive Baseline",
                    line=dict(
                        dash="dash",
                        width=2
                    )
                )
            )


    # --------------------------------------------------------
    # UPPER FORECAST INTERVAL
    # --------------------------------------------------------

    forecast_fig.add_trace(
        go.Scatter(
            x=forecast["Date"],
            y=forecast["Forecast_Upper_80"],
            mode="lines",
            line=dict(
                width=0
            ),
            showlegend=False,
            hoverinfo="skip"
        )
    )


    # --------------------------------------------------------
    # LOWER FORECAST INTERVAL
    # --------------------------------------------------------

    forecast_fig.add_trace(
        go.Scatter(
            x=forecast["Date"],
            y=forecast["Forecast_Lower_80"],
            mode="lines",
            fill="tonexty",
            name="80% Forecast Interval",
            line=dict(
                width=0
            ),
            hoverinfo="skip"
        )
    )


    # --------------------------------------------------------
    # PREDICTED DEMAND
    # --------------------------------------------------------

    forecast_fig.add_trace(
        go.Scatter(
            x=forecast["Date"],
            y=forecast["Predicted_Demand"],
            mode="lines+markers",
            name="Predicted Demand",
            line=dict(
                width=3
            )
        )
    )


    forecast_fig.update_layout(
        height=480,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Demand"
    )


    st.plotly_chart(
        forecast_fig,
        width="stretch"
    )


else:

    st.warning(
        "Forecast chart requires Date and Predicted_Demand."
    )


# ============================================================
# INVENTORY RISK ANALYSIS
# ============================================================

st.header(
    "⚠️ Inventory Risk Analysis"
)


risk_left, risk_right = st.columns(2)


# ============================================================
# STOCKOUT RISK CHART
# ============================================================

with risk_left:

    high_stockout = int(
        (
            latest_filtered[
                "Stockout_Risk"
            ]
            ==
            1
        )
        .sum()
    )


    normal_stockout = int(
        (
            latest_filtered[
                "Stockout_Risk"
            ]
            ==
            0
        )
        .sum()
    )


    stockout_data = pd.DataFrame(
        {
            "Risk": [
                "High Risk",
                "Normal"
            ],
            "SKUs": [
                high_stockout,
                normal_stockout
            ]
        }
    )


    stockout_fig = px.bar(
        stockout_data,
        x="Risk",
        y="SKUs",
        text="SKUs",
        title="Stockout Risk Distribution"
    )


    stockout_fig.update_traces(
        textposition="outside"
    )


    stockout_fig.update_layout(
        height=400,
        yaxis_title="Unique SKUs"
    )


    st.plotly_chart(
        stockout_fig,
        width="stretch"
    )


# ============================================================
# OVERSTOCK RISK CHART
# ============================================================

with risk_right:

    high_overstock = int(
        (
            latest_filtered[
                "Overstock_Risk"
            ]
            ==
            1
        )
        .sum()
    )


    normal_overstock = int(
        (
            latest_filtered[
                "Overstock_Risk"
            ]
            ==
            0
        )
        .sum()
    )


    overstock_data = pd.DataFrame(
        {
            "Risk": [
                "High Risk",
                "Normal"
            ],
            "SKUs": [
                high_overstock,
                normal_overstock
            ]
        }
    )


    overstock_fig = px.bar(
        overstock_data,
        x="Risk",
        y="SKUs",
        text="SKUs",
        title="Overstock Risk Distribution"
    )


    overstock_fig.update_traces(
        textposition="outside"
    )


    overstock_fig.update_layout(
        height=400,
        yaxis_title="Unique SKUs"
    )


    st.plotly_chart(
        overstock_fig,
        width="stretch"
    )


# ============================================================
# DEMAND VS INVENTORY
# ============================================================

st.header(
    "📦 Demand vs Inventory"
)


if (
    "Predicted_Demand" in latest_filtered.columns
    and
    "Inventory_Units" in latest_filtered.columns
):

    demand_inventory_fig = px.scatter(
        latest_filtered,
        x="Predicted_Demand",
        y="Inventory_Units",
        hover_name="Product_ID",
        title="Predicted Demand vs Inventory"
    )


    demand_inventory_fig.update_traces(
        marker=dict(
            size=10
        )
    )


    demand_inventory_fig.update_layout(
        height=450,
        xaxis_title="Predicted Demand",
        yaxis_title="Inventory Units"
    )


    st.plotly_chart(
        demand_inventory_fig,
        width="stretch"
    )


# ============================================================
# DECISION GRID
# ============================================================

st.header(
    "🎯 Stockout vs Overstock Decision Grid"
)


grid = latest_filtered.copy()


if not grid.empty:

    decision_fig = px.scatter(
        grid,
        x="Stockout_Risk",
        y="Overstock_Risk",
        color="Inventory_Action",
        hover_name="Product_ID",
        title="SKU Decision Map"
    )


    decision_fig.update_traces(
        marker=dict(
            size=11
        )
    )


    decision_fig.update_xaxes(
        tickmode="array",
        tickvals=[
            0,
            1
        ],
        ticktext=[
            "Low Stockout",
            "High Stockout"
        ],
        range=[
            -0.15,
            1.15
        ]
    )


    decision_fig.update_yaxes(
        tickmode="array",
        tickvals=[
            0,
            1
        ],
        ticktext=[
            "Low Overstock",
            "High Overstock"
        ],
        range=[
            -0.15,
            1.15
        ]
    )


    decision_fig.update_layout(
        height=480,
        xaxis_title="Stockout Risk",
        yaxis_title="Overstock Risk"
    )


    st.plotly_chart(
        decision_fig,
        width="stretch"
    )


st.info(
    "🛒 **REORDER NOW** → High stockout risk + Low overstock risk\n\n"
    "🏷️ **MARKDOWN / CLEAR** → Low stockout risk + High overstock risk\n\n"
    "⚠️ **WATCH / VOLATILE** → High stockout risk + High overstock risk\n\n"
    "✅ **HEALTHY** → Low stockout risk + Low overstock risk"
)


# ============================================================
# INVENTORY RECOMMENDATIONS
# ============================================================

st.header(
    "🤖 Inventory Recommendations"
)


recommendations = latest_filtered.copy()


reorder_count = int(
    (
        recommendations[
            "Inventory_Action"
        ]
        ==
        "REORDER NOW"
    )
    .sum()
)


markdown_count = int(
    (
        recommendations[
            "Inventory_Action"
        ]
        ==
        "MARKDOWN / CLEAR"
    )
    .sum()
)


watch_count = int(
    (
        recommendations[
            "Inventory_Action"
        ]
        ==
        "WATCH / VOLATILE"
    )
    .sum()
)


healthy_count = int(
    (
        recommendations[
            "Inventory_Action"
        ]
        ==
        "HEALTHY"
    )
    .sum()
)


rec1, rec2, rec3, rec4 = st.columns(4)


with rec1:

    st.metric(
        "🛒 Reorder Now",
        f"{reorder_count:,}"
    )


with rec2:

    st.metric(
        "🏷️ Markdown / Clear",
        f"{markdown_count:,}"
    )


with rec3:

    st.metric(
        "👀 Watch / Volatile",
        f"{watch_count:,}"
    )


with rec4:

    st.metric(
        "✅ Healthy",
        f"{healthy_count:,}"
    )


# ============================================================
# RECOMMENDED ORDER TABLE
# ============================================================

st.subheader(
    "🔄 Recommended Order Quantity"
)


order_columns = [
    "Product_ID",
    "Category",
    "Date",
    "Predicted_Demand",
    "Inventory_Units",
    "Reorder_Point",
    "Recommended_Order_Qty",
    "Inventory_Action"
]


order_columns = [
    column
    for column in order_columns
    if column in recommendations.columns
]


if order_columns:

    order_table = (
        recommendations[
            order_columns
        ]
        .copy()
    )


    if "Recommended_Order_Qty" in order_table.columns:

        order_table = (
            order_table
            .sort_values(
                "Recommended_Order_Qty",
                ascending=False
            )
        )


    order_table = (
        order_table
        .head(25)
        .rename(
            columns={
                "Product_ID":
                    "Product ID",

                "Predicted_Demand":
                    "Predicted Demand",

                "Inventory_Units":
                    "Inventory Units",

                "Reorder_Point":
                    "Reorder Point",

                "Recommended_Order_Qty":
                    "Recommended Order Qty",

                "Inventory_Action":
                    "Inventory Action"
            }
        )
    )


    st.dataframe(
        order_table,
        width="stretch",
        height=430
    )


# ============================================================
# DEMAND BY CATEGORY
# ============================================================

st.header(
    "🏷️ Demand by Category"
)


if "Predicted_Demand" in filtered.columns:

    category_data = (
        filtered
        .groupby(
            "Category",
            as_index=False
        )[
            "Predicted_Demand"
        ]
        .sum()
        .sort_values(
            "Predicted_Demand",
            ascending=False
        )
    )


    category_fig = px.bar(
        category_data,
        x="Category",
        y="Predicted_Demand",
        text="Predicted_Demand",
        title="Predicted Demand by Category"
    )


    category_fig.update_traces(
        texttemplate="%{text:.0f}",
        textposition="outside"
    )


    category_fig.update_layout(
        height=400
    )


    st.plotly_chart(
        category_fig,
        width="stretch"
    )


# ============================================================
# SALES & PROMOTION INSIGHTS
# ============================================================

st.header(
    "💰 Sales & Promotion Insights"
)


if "Sales_Quantity" in filtered.columns:

    total_units = (
        safe_numeric(
            filtered,
            "Sales_Quantity"
        )
        .sum()
    )

else:

    total_units = (
        safe_numeric(
            filtered,
            "Weekly_Demand"
        )
        .sum()
    )


if "Revenue" in filtered.columns:

    total_revenue = (
        safe_numeric(
            filtered,
            "Revenue"
        )
        .sum()
    )

else:

    total_revenue = 0.0


average_price = (
    safe_numeric(
        filtered,
        "list_price"
    )
    .mean()
)


average_discount = (
    safe_numeric(
        filtered,
        "Discount"
    )
    .mean()
)


sales1, sales2, sales3, sales4 = st.columns(4)


with sales1:

    st.metric(
        "📦 Total Units Sold",
        f"{total_units:,.0f}"
    )


with sales2:

    st.metric(
        "💰 Total Revenue",
        format_inr(
            total_revenue
        )
    )


with sales3:

    st.metric(
        "🏷️ Average Price",
        format_inr(
            average_price
        )
    )


with sales4:

    st.metric(
        "🏷️ Average Discount",
        f"{average_discount:.1f}%"
    )


# ============================================================
# PROMOTION ANALYSIS
# ============================================================

if (
    "On_Promotion" in filtered.columns
    and
    "Weekly_Demand" in filtered.columns
):

    promotion_data = (
        filtered
        .groupby(
            "On_Promotion"
        )[
            "Weekly_Demand"
        ]
        .mean()
        .rename(
            index={
                0: "No Promotion",
                1: "Promotion"
            }
        )
        .reset_index()
    )


    promotion_data.columns = [
        "Promotion",
        "Average Demand"
    ]


    promotion_fig = px.bar(
        promotion_data,
        x="Promotion",
        y="Average Demand",
        text="Average Demand",
        title="Average Demand: Promotion vs No Promotion"
    )


    promotion_fig.update_traces(
        texttemplate="%{text:.1f}",
        textposition="outside"
    )


    promotion_fig.update_layout(
        height=400
    )


    st.plotly_chart(
        promotion_fig,
        width="stretch"
    )


# ============================================================
# MODEL PERFORMANCE
# ============================================================

st.header(
    "🎯 Model Performance"
)


if (
    "Weekly_Demand" in filtered.columns
    and
    "Predicted_Demand" in filtered.columns
):

    evaluation = (
        filtered[
            [
                "Weekly_Demand",
                "Predicted_Demand"
            ]
        ]
        .dropna()
    )


    if not evaluation.empty:

        actual = (
            evaluation[
                "Weekly_Demand"
            ]
            .astype(float)
        )


        predicted = (
            evaluation[
                "Predicted_Demand"
            ]
            .astype(float)
        )


        error = (
            actual
            -
            predicted
        )


        absolute_error = (
            error.abs()
        )


        # ----------------------------------------------------
        # MAE
        # ----------------------------------------------------

        mae = (
            absolute_error
            .mean()
        )


        # ----------------------------------------------------
        # RMSE
        # ----------------------------------------------------

        rmse = np.sqrt(
            (
                error ** 2
            )
            .mean()
        )


        # ----------------------------------------------------
        # MAPE
        # ----------------------------------------------------

        nonzero_actual = (
            actual != 0
        )


        if nonzero_actual.any():

            mape = (
                (
                    absolute_error[
                        nonzero_actual
                    ]
                    /
                    actual[
                        nonzero_actual
                    ].abs()
                )
                .mean()
                *
                100
            )

        else:

            mape = np.nan


        # ----------------------------------------------------
        # WAPE
        # ----------------------------------------------------

        total_actual = (
            actual.abs()
            .sum()
        )


        if total_actual > 0:

            wape = (
                absolute_error.sum()
                /
                total_actual
                *
                100
            )

        else:

            wape = np.nan


        # ----------------------------------------------------
        # BIAS
        # ----------------------------------------------------

        bias = (
            error
            .mean()
        )


        model1, model2, model3, model4, model5 = (
            st.columns(5)
        )


        with model1:

            st.metric(
                "MAE",
                f"{mae:,.2f}"
            )


        with model2:

            st.metric(
                "RMSE",
                f"{rmse:,.2f}"
            )


        with model3:

            st.metric(
                "MAPE",
                (
                    f"{mape:.2f}%"
                    if not pd.isna(mape)
                    else
                    "—"
                )
            )


        with model4:

            st.metric(
                "WAPE",
                (
                    f"{wape:.2f}%"
                    if not pd.isna(wape)
                    else
                    "—"
                )
            )


        with model5:

            st.metric(
                "BIAS",
                f"{bias:,.2f}"
            )


# ============================================================
# PREDICTION RESULTS
# ============================================================

st.header(
    "📋 Prediction Results"
)


display_columns = [
    "Product_ID",
    "Category",
    "Date",
    "Weekly_Demand",
    "Predicted_Demand",
    "Avg_Stock",
    "Avg_Lead_Time",
    "Lead_Time_Demand",
    "Predicted_Stockout_Risk",
    "Overstock_Threshold",
    "Predicted_Overstock_Risk",
    "Reorder_Point",
    "Recommended_Order_Qty"
]


display_columns = [
    column
    for column in display_columns
    if column in filtered.columns
]


if display_columns:

    display_data = (
        filtered[
            display_columns
        ]
        .copy()
    )


    display_data = (
        display_data
        .head(100)
        .rename(
            columns={
                "Product_ID":
                    "Product ID",

                "Weekly_Demand":
                    "Actual Demand",

                "Predicted_Demand":
                    "Predicted Demand",

                "Avg_Stock":
                    "Average Stock",

                "Avg_Lead_Time":
                    "Lead Time",

                "Lead_Time_Demand":
                    "Lead Time Demand",

                "Predicted_Stockout_Risk":
                    "Stockout Risk",

                "Overstock_Threshold":
                    "Overstock Threshold",

                "Predicted_Overstock_Risk":
                    "Overstock Risk",

                "Reorder_Point":
                    "Reorder Point",

                "Recommended_Order_Qty":
                    "Recommended Order Qty"
            }
        )
    )


    st.dataframe(
        display_data,
        width="stretch",
        height=500
    )


# ============================================================
# BUSINESS IMPACT
# ============================================================

st.header(
    "💼 Business Impact"
)


impact_left, impact_right = st.columns(2)


with impact_left:

    st.subheader(
        "💰 Sales at Risk"
    )


    st.metric(
        "Potential Revenue Exposure",
        format_inr(
            sales_at_risk
        )
    )


    st.caption(
        "Stockout units at risk × actual SKU list price."
    )


with impact_right:

    st.subheader(
        "💵 Capital Locked"
    )


    st.metric(
        "Current Inventory Value",
        format_inr(
            capital_locked
        )
    )


    st.caption(
        "Current inventory units × actual SKU list price."
    )


# ============================================================
# EXPORT
# ============================================================

st.header(
    "💾 Export Results"
)


export_csv = (
    filtered
    .to_csv(
        index=False
    )
    .encode(
        "utf-8"
    )
)


st.download_button(
    label="⬇️ Download Filtered Prediction Results",
    data=export_csv,
    file_name="foresight_filtered_predictions.csv",
    mime="text/csv"
)


# ============================================================
# FOOTER
# ============================================================

st.divider()


st.caption(
    "📦 FORESIGHT • "
    "AI-Powered Demand Forecasting & Inventory Intelligence"
)


st.caption(
    "Demand Forecasting • "
    "Risk Detection • "
    "Smart Replenishment • "
    "Business Impact"
)