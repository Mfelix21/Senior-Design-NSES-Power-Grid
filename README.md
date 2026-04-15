# NSES — National Smart Energy System

Houston Power Grid Monitoring, Fault Simulation & ML Forecasting Platform

Built with **Streamlit in Snowflake** by **PanthersWhoCode**

I was the front-end developer for this project, screenshots of the project are towards the bottom.
---

## Overview

NSES is a full-stack energy analytics application that monitors Houston's power grid infrastructure in real time, simulates disaster fault scenarios, and forecasts energy generation 24 months ahead using machine learning.

---

## Features

### Homepage
- Hero section with live grid statistics (avg/peak MWh)
- Animated CSS effects (grid pulse, scanline sweep, glowing border)
- Quick-action navigation buttons

### Dashboard
- **Interactive PyDeck map** of Houston's grid (6 power plants, 5 substations, transmission lines)
- **Fault simulation engine** — take plants offline, apply disaster scenarios (Hurricane, Ice Storm, Flood, etc.)
- **Load redistribution** — capacity automatically redistributed with overload/warning indicators
- **Baseline analysis** and **prediction charts**
- **CSV data import** with automatic model retraining pipeline

### Reports
- Summary statistics (avg, peak, min generation, YoY growth)
- Historical vs predicted generation overlay
- 24-month future forecast
- Per-plant generation comparison
- Model performance metrics (MAE, R²)
- CSV download buttons

### Authentication
- Custom login system with SHA-256 hashed passwords
- Role-based user management

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit, HTML/CSS, PyDeck |
| Backend | Snowflake (Snowpark) |
| ML Model | Random Forest (Snowflake Model Registry) |
| Visualization | Matplotlib, Streamlit native charts |
| Authentication | SHA-256 + Snowflake table |
| Data Storage | Snowflake tables |

---

## Snowflake Dependencies

### Database: `PWC_DB.PUBLIC`

| Object | Type | Purpose |
|---|---|---|
| `HOUSTON_BASELINE` | Table | Historical monthly generation data |
| `A_POWER_PLANTS` — `F_POWER_PLANT` | Tables | Individual plant generation data |
| `HOUSTON_BASELINE_FEATURES` | Table | Engineered ML features (lags, year, month) |
| `HOUSTON_PREDICTIONS` | Table | Model predictions on historical data |
| `HOUSTON_FUTURE_FORECAST` | Table | 24-month forward forecast |
| `HOUSTON_FUTURE_DATES` | Table | Date scaffold for future predictions |
| `HOUSTON_ANOMALY_SIMULATION_RESULTS` | Table | Historical disruption events |
| `APP_USERS` | Table | Login credentials (username, hash, role) |
| `HOUSTON_RF_MWH` | ML Model | Random Forest regression model |


## Screenshots

<img width="1201" height="761" alt="image" src="https://github.com/user-attachments/assets/b140e913-e51c-4f2f-bd1e-82080dd29f4f" />

<img width="1613" height="759" alt="image" src="https://github.com/user-attachments/assets/21a3fd86-9390-4064-b2c5-e15de8c66263" />

<img width="1442" height="827" alt="image" src="https://github.com/user-attachments/assets/52f4ee95-d0eb-4749-95eb-f7b7033b2278" />

<img width="1614" height="829" alt="image" src="https://github.com/user-attachments/assets/6a663000-f53b-4e05-a1ab-e9162987b165" />

---



