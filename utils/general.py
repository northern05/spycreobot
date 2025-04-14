import io
import json
import ast
import re
from datetime import datetime, timedelta
import uuid
import requests
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from scipy.interpolate import make_interp_spline


def generate_session_id() -> str:
    return uuid.uuid4().hex


def check_users_retwitt():
    response = requests.post(url="https://api.agent.zpoken.dev/api/v1/general/check_retwitts")
    if response.status_code == 200:
        return {"ok": True}
    else:
        return {"ok": False}


def sell_tokens():
    response = requests.post(url="http://127.0.0.1:6010/api/v1/general/sell_tokens")
    if response.status_code == 200:
        return {"ok": True}
    else:
        return {"ok": False}


def log_agent_balance():
    response = requests.post(url="https://api.agent.zpoken.dev/api/v1/general/log_agent_balance")
    if response.status_code == 200:
        return {"ok": True}
    else:
        return {"ok": False}


def create_crypto_sentiment_chart(historical_prices, sentiment_data: dict = None):
    """
    Creates an interactive Plotly chart comparing historical crypto prices with ELFA sentiment analysis data.

    Parameters:
    - historical_prices (list of dict): [{"date": "2025-03-10", "price": 2000}, ...]
    - sentiment_data (dict): ELFA sentiment response with metrics.

    Returns:
    - A Plotly figure.
    """
    # Convert historical prices to DataFrame
    seven_days_ago = datetime.now() - timedelta(days=7)
    price_df = pd.DataFrame(historical_prices)
    price_df["date"] = pd.to_datetime(price_df["date"])
    price_df = price_df[price_df["date"] >= seven_days_ago]

    # Sort data by date
    price_df = price_df.sort_values("date")

    # Convert dates to numerical values
    x_numeric = np.arange(len(price_df))
    y_smooth = make_interp_spline(x_numeric, price_df["price"], k=3)(x_numeric)

    # Create Figure
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=price_df["date"],
        y=y_smooth,
        mode="lines",
        name="Price (USD)",
        line=dict(color="orange", width=2),
        yaxis="y1"
    ))

    # Layout Settings
    fig.update_layout(
        title="Crypto Price",
        xaxis=dict(title="Date"),
        yaxis=dict(
            title=dict(text="Price (USD)", font=dict(color="orange")),
            side="left"
        ),
        template="plotly_dark",
        legend_title="Metrics"
    )

    # Convert figure to PNG
    img_bytes = io.BytesIO()
    fig.write_image(img_bytes, format="png")
    img_bytes.seek(0)
    return img_bytes


def parse_json_string(json_str):
    json_str = json_str.strip()
    if not json_str.endswith("}"):
        json_str += "}"
    json_str = json_str.replace("'", '"')

    try:
        # Try to load the JSON string after cleaning
        data = json.loads(json_str)
        if isinstance(data, dict):
            return data
        elif isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            return data[0]
        else:
            raise ValueError("JSON does not contain a single dictionary.")
    except json.JSONDecodeError as e:
        match = re.search(r'\{.*\}', json_str)  # Non-greedy match to capture the whole dict

        if match:
            json_string = match.group(0)
            try:
                data_dict = json.loads(json_string)
                return data_dict
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON format: {e}")
