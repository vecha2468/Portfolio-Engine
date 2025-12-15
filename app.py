# app.py

import streamlit as st
import pandas as pd

from portfolio_logic import (
    STRATEGY_TICKERS,
    build_portfolio,
    load_history,
    save_history,
)

# ---------------- Streamlit Page Config ---------------- #

st.set_page_config(
    page_title="Stock Portfolio Suggestion Engine",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Stock Portfolio Suggestion Engine")
st.write(
    """
This app suggests a stock/ETF portfolio based on your selected **investment strategies** 
and **investment amount**. Prices are fetched live from the internet using yfinance.
"""
)

# ---------------- Sidebar Inputs ---------------- #

st.sidebar.header("User Input")

amount = st.sidebar.number_input(
    "Investment Amount (USD)",
    min_value=5000,
    value=5000,
    step=500,
    help="Minimum allowed is $5000 as per project requirements.",
)

strategy_options = list(STRATEGY_TICKERS.keys())
strategies = st.sidebar.multiselect(
    "Select 1–2 Strategies",
    strategy_options,
    max_selections=2
)
# enforce max 2 strategies manually (older Streamlit versions don't support max_selections)
if len(strategies) > 2:
    st.sidebar.error("Please select at most 2 strategies.")
    strategies = strategies[:2]

generate_btn = st.sidebar.button("🚀 Generate Portfolio")

# ---------------- Main Content ---------------- #

if not generate_btn:
    st.info("👈 Set your amount and strategies in the sidebar, then click **Generate Portfolio**.")
else:
    if len(strategies) == 0:
        st.error("Please select at least one strategy.")
    else:
        try:
            portfolio_df, total_value, leftover_cash, latest_prices = build_portfolio(
                total_amount=amount,
                strategies=strategies
            )
        except Exception as e:
            st.error(f"Error while building portfolio: {e}")
        else:
            # ----- Top Metrics ----- #
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Investment Amount", f"${amount:,.2f}")
            with col2:
                st.metric("Total Invested Value", f"${total_value:,.2f}")
            with col3:
                st.metric("Uninvested Cash", f"${leftover_cash:,.2f}")

            # ----- Portfolio Table ----- #
            st.subheader("📊 Suggested Portfolio Allocation")

            if portfolio_df.empty:
                st.warning("No portfolio could be built (missing prices). Try again later.")
            else:
                # ensure proper ordering of columns
                portfolio_df = portfolio_df[["Strategy", "Ticker", "Price", "Shares", "Cost"]]
                st.dataframe(
                    portfolio_df,
                    use_container_width=True,
                )

                # ----- Optional: show per-strategy totals ----- #
                st.markdown("**Per-Strategy Investment Breakdown**")
                strat_summary = (
                    portfolio_df.groupby("Strategy", dropna=True)["Cost"]
                    .sum()
                    .reset_index()
                )
                strat_summary.rename(columns={"Cost": "Total Cost"}, inplace=True)
                st.dataframe(strat_summary, use_container_width=True)

                # ----- Optional: show a simple allocation pie chart ----- #
                if not strat_summary.empty and strat_summary["Total Cost"].sum() > 0:
                    try:
                        pie_df = strat_summary.set_index("Strategy")
                        st.bar_chart(pie_df["Total Cost"])
                    except Exception:
                        pass

            # ----- History Section ----- #
            st.subheader("📅 5-Day Portfolio Value Trend")

            # save today's value and load updated history
            history = save_history(total_value=total_value)
            history_df = pd.DataFrame(history)

            if history_df.empty:
                st.info("No history yet.")
            else:
                # convert date column to datetime for better plotting
                history_df["date"] = pd.to_datetime(history_df["date"])

                # Show as table
                st.write("Recent Values:")
                st.dataframe(history_df, use_container_width=True)

                # Line chart of value over time
                history_df = history_df.set_index("date").sort_index()
                st.line_chart(history_df["value"])
