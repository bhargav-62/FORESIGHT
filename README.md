# FORESIGHT — AI-Powered Demand Forecasting & Inventory Intelligence Platform

FORESIGHT is an AI-powered demand forecasting and inventory intelligence platform designed to help businesses predict future product demand and identify potential stockout and overstock risks.

The platform combines data analysis, machine learning, inventory intelligence, and an interactive Streamlit dashboard to provide actionable insights for inventory planning.

---

## 🚀 Project Overview

Inventory teams often face two major challenges:

- Stockouts, which can lead to lost sales and customer dissatisfaction.
- Overstock, which ties up business capital and increases inventory holding costs.

FORESIGHT addresses these challenges by analyzing historical sales, pricing, promotions, inventory levels, and supplier lead times to generate demand forecasts and inventory risk insights.

The platform provides:

- Weekly SKU-level demand forecasts
- Stockout risk identification
- Overstock risk identification
- Recommended inventory actions
- Sales-at-risk estimation
- Capital-locked estimation
- Interactive planning dashboard

---

## 🎯 Objectives

The main objectives of FORESIGHT are:

1. Forecast weekly demand for individual SKUs.
2. Identify products that may face stockout risk.
3. Identify potential overstock situations.
4. Recommend appropriate inventory actions.
5. Quantify potential business impact in Indian Rupees.
6. Provide an easy-to-use dashboard for operational decision-making.
7. Build a reproducible data science pipeline.

---

## 🏗️ Project Architecture

```text
                    ┌──────────────────────┐
                    │   Historical Data    │
                    │                      │
                    │ Sales / Inventory    │
                    │ Price / Promotion    │
                    │ Lead Time / Product  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Data Pipeline     │
                    │                      │
                    │ Cleaning             │
                    │ Validation           │
                    │ Feature Engineering  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Weekly Features    │
                    │                      │
                    │ Lag Features         │
                    │ Rolling Statistics   │
                    │ Promotion Features   │
                    │ Inventory Features   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Machine Learning     │
                    │ Model                │
                    │                      │
                    │ Random Forest        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Demand Forecast      │
                    │                      │
                    │ Predicted Demand     │
                    │ Lead-Time Demand     │
                    └──────────┬───────────┘
                               │
                               ▼
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
     ┌──────────────────┐             ┌──────────────────┐
     │ Stockout Risk    │             │ Overstock Risk   │
     │ Detection        │             │ Detection        │
     └────────┬─────────┘             └────────┬─────────┘
              │                                 │
              └────────────────┬────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │ Inventory Actions    │
                    │                      │
                    │ Reorder              │
                    │ Monitor              │
                    │ No Action            │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Streamlit Dashboard  │
                    │                      │
                    │ Forecast             │
                    │ Risk                 │
                    │ Inventory            │
                    │ Business Impact      │
                    └──────────────────────┘
