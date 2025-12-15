import yfinance as yf


def test_single_ticker(ticker):
    try:
        # Attempt to get the latest price
        yf_ticker = yf.Ticker(ticker)
        hist = yf_ticker.history(period="1d")

        if not hist.empty:
            price = hist["Close"].iloc[-1]
            print(f"{ticker} price (1-day): {price}")
        else:
            print(f"{ticker} history is empty.")

        # Fall back to info if 1-day is empty
        try:
            fast_info_price = yf_ticker.info["currentPrice"]
            print(f"{ticker} fast_info price: {fast_info_price}")
        except KeyError:
            print(f"{ticker} has no currentPrice in fast_info.")
    except Exception as e:
        print(f"Error for {ticker}: {e}")


# Test a list of tickers
tickers = ["AAPL", "TSLA", "BRK-B", "NSRGY"]
for ticker in tickers:
    test_single_ticker(ticker)
