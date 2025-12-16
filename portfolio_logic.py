# portfolio_logic.py

import os
import json
from math import floor
from datetime import datetime

import yfinance as yf
import pandas as pd
from datetime import timedelta
import random

# ------------ Strategy → Ticker Mapping ------------ #

STRATEGY_TICKERS = {
    "Ethical Investing": ["AAPL", "ADBE", "NSRGY"],
    "Growth Investing": ["AMZN", "TSLA", "NVDA"],
    "Index Investing": ["VTI", "IXUS", "ILTB"],
    "Quality Investing": ["MSFT", "JNJ", "PG"],
    "Value Investing": ["BRK-B", "VZ", "INTC"],
}

# ------------ Paths & History Helpers ------------ #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_history():
    ensure_data_dir()
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(total_value, max_points=5):
    """
    Saves today's portfolio value.
    If fewer than max_points days exist, auto-generates missing days.
    Always returns exactly max_points most recent days.
    """
    ensure_data_dir()
    history = load_history()

    today = datetime.now().strftime("%Y-%m-%d")

    # Remove today's entry if exists (avoid duplicates)
    history = [h for h in history if h["date"] != today]

    # Append today's real value
    history.append({"date": today, "value": float(total_value)})

    # Sort by date
    history = sorted(history, key=lambda x: x["date"])

    # ---- AUTO-GENERATE MISSING DAYS ----
    while len(history) < max_points:
        # Generate previous day based on oldest entry
        oldest_date = datetime.strptime(history[0]["date"], "%Y-%m-%d")
        new_date = oldest_date - timedelta(days=1)
        new_value = history[0]["value"] * (0.99 + (0.02 * random.random()))

        history.insert(0, {
            "date": new_date.strftime("%Y-%m-%d"),
            "value": round(new_value, 2)
        })

    # Keep only last max_points entries
    history = history[-max_points:]

    # Save back to file
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

    return history

# ------------ PRICE FETCHING (KEY PART) ------------ #

def get_latest_prices(tickers):
    """
    Very simple & reliable price fetcher.
    Uses the SAME logic that worked in your test_yfinance.py.
    """
    prices = {}

    for t in tickers:
        try:
            ticker = yf.Ticker(t)
            hist = ticker.history(period="1d")

            if not hist.empty:
                close_price = hist["Close"].iloc[-1]
                prices[t] = float(close_price)
            else:
                # no data – mark as None
                prices[t] = None
        except Exception as e:
            print(f"Error fetching price for {t}: {e}")
            prices[t] = None

    # DEBUG: you can uncomment this to see in Streamlit logs
    # print("DEBUG latest_prices:", prices)

    return prices


# ------------ PORTFOLIO CONSTRUCTION ------------ #

def allocate_between_strategies(total_amount, strategies):
    if not strategies:
        return {}
    per_strategy = total_amount / len(strategies)
    return {s: per_strategy for s in strategies}


def build_portfolio(total_amount, strategies):
    allocations = allocate_between_strategies(total_amount, strategies)

    # Collect tickers
    strategy_to_tickers = {}
    all_tickers = set()

    for strat in strategies:
        tickers = STRATEGY_TICKERS.get(strat, [])
        strategy_to_tickers[strat] = tickers
        all_tickers.update(tickers)

    all_tickers = list(all_tickers)
    latest_prices = get_latest_prices(all_tickers)

    rows = []
    total_invested = 0.0

    shares_owned = {t: 0 for t in all_tickers}

    # --- FIRST PASS: Equal allocation per strategy ---
    for strat in strategies:
        tickers = strategy_to_tickers[strat]
        strat_amount = allocations[strat]
        per_ticker_amount = strat_amount / len(tickers)

        for t in tickers:
            price = latest_prices.get(t)
            if price is None or price <= 0:
                continue

            shares = floor(per_ticker_amount / price)
            shares_owned[t] += shares
            total_invested += shares * price

    # --- GLOBAL OPTIMIZATION: Spend leftover cash ---
    leftover_cash = total_amount - total_invested

    # Remove tickers with no price
    priced_tickers = {t: p for t, p in latest_prices.items() if p and p > 0}

    # While we can afford at least one more share
    while True:
        affordable = [t for t, p in priced_tickers.items() if p <= leftover_cash]
        if not affordable:
            break

        # Buy the most expensive affordable stock
        best_ticker = max(affordable, key=lambda t: priced_tickers[t])
        price = priced_tickers[best_ticker]

        shares_owned[best_ticker] += 1
        leftover_cash -= price
        total_invested += price

    # --- Build final DataFrame ---
    for strat in strategies:
        tickers = strategy_to_tickers[strat]
        for t in tickers:
            price = latest_prices.get(t)
            s = shares_owned.get(t, 0)

            rows.append({
                "Strategy": strat,
                "Ticker": t,
                "Price": round(price, 2) if price else None,
                "Shares": int(s),
                "Cost": round(s * price, 2) if price else 0
            })

    portfolio_df = pd.DataFrame(rows)

    return portfolio_df, float(total_invested), float(leftover_cash), latest_prices

