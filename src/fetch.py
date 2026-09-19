import yfinance as yf
import pandas as pd
import requests

import os
from dotenv import load_dotenv
from fredapi import Fred

load_dotenv()  # reads .env file into environment variables
fred = Fred(api_key=os.getenv("FRED_API_KEY"))

# Index tickers: ^GSPC = S&P 500, ^IXIC = Nasdaq Composite (closest to "NDX" behavior via yfinance)
INDEX_TICKERS = {"SPX": "^GSPC", "NDX": "^IXIC"}

def get_index_data(period="6mo"):
    """
    Pull daily close prices for SPX and NDX over a given period.
    period accepts yfinance shorthand: '1mo','3mo','6mo','ytd','1y','5y','max'
    Returns a DataFrame with columns ['SPX', 'NDX'], indexed by date.
    """
    data = {}
    for label, ticker in INDEX_TICKERS.items():
        hist = yf.Ticker(ticker).history(period=period)
        data[label] = hist["Close"]
    return pd.DataFrame(data)


def get_prior_day_change(df):
    """
    Given a DataFrame of index closes, return a dict of {label: pct_change}
    for the most recent full trading day.
    """
    changes = {}
    for col in df.columns:
        pct = df[col].pct_change().iloc[-1] * 100
        changes[col] = pct
    return changes

# Standard SPDR sector ETFs, proxy for S&P 500 GICS sectors
SECTOR_TICKERS = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Materials": "XLB",
    "Communication Services": "XLC",
}

def get_sector_data(period="6mo"):
    """
    Pull daily close prices for all S&P sector ETFs over a given period.
    Returns a DataFrame with one column per sector, indexed by date.
    """
    data = {}
    for label, ticker in SECTOR_TICKERS.items():
        hist = yf.Ticker(ticker).history(period=period)
        data[label] = hist["Close"]
    return pd.DataFrame(data)


def get_sector_period_performance(period="6mo"):
    """
    Return % performance of each sector over the given period
    (first close to last close in that window).
    """
    df = get_sector_data(period=period).dropna(how="all")  # drop incomplete trailing row
    perf = (df.iloc[-1] / df.iloc[0] - 1) * 100
    return perf.sort_values(ascending=False)


def get_sector_prior_day_change():
    """
    % change for each sector over the most recent completed trading day.
    """
    df = get_sector_data(period="5d").dropna(how="all")  # drop incomplete trailing row
    changes = df.pct_change().iloc[-1] * 100
    return changes.sort_values(ascending=False)

def get_spx_prior_day_change():
    """
    Returns (date, pct_change) for the S&P 500's most recent completed trading day.
    """
    df = get_index_data(period="5d").dropna(how="all")
    pct = df["SPX"].pct_change().iloc[-1] * 100
    date = df.index[-1]
    return date, pct

def get_rsp_spy_ratio(period="6mo"):
    """
    RSP (equal-weight S&P 500) / SPY (cap-weight S&P 500) ratio over a period.
    Falling ratio = mega-caps carrying the index, average stock lagging.
    Rising ratio = broad participation across the index.
    """
    raw = yf.download(["RSP", "SPY"], period=period, auto_adjust=True, group_by="column", progress=False)
    closes = raw["Close"]
    return closes["RSP"] / closes["SPY"]


import io

def get_sp500_tickers():
    """
    Scrape current S&P 500 constituents from Wikipedia.
    Returns a list of yfinance-compatible ticker strings.
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    table = pd.read_html(io.StringIO(response.text))[0]
    tickers = table["Symbol"].str.replace(".", "-", regex=False).tolist()
    return tickers


def get_breadth_data():
    """
    Pull ~300 days of history for all S&P 500 constituents and compute:
      - prior-day % returns for every stock (advance/decline distribution)
      - % of stocks below their 50-day moving average
      - % of stocks below their 200-day moving average
    """
    tickers = get_sp500_tickers()
    raw = yf.download(tickers, period="300d", auto_adjust=True, group_by="column", threads=True)
    closes = raw["Close"]

    # Drop the last row if it's mostly empty (today's still-forming bar),
    # rather than only when it's fully empty - a handful of stray tickers
    # can populate early and fool a strict all-NaN check
    if closes.iloc[-1].notna().mean() < 0.9:
        closes = closes.iloc[:-1]

    daily_returns = closes.pct_change().iloc[-1] * 100
    daily_returns = daily_returns.dropna()

    ma50 = closes.rolling(50).mean().iloc[-1]
    ma200 = closes.rolling(200).mean().iloc[-1]
    last_close = closes.iloc[-1]

    pct_below_50 = (last_close < ma50).sum() / last_close.notna().sum() * 100
    pct_below_200 = (last_close < ma200).sum() / last_close.notna().sum() * 100

    return daily_returns, pct_below_50, pct_below_200

FRED_YIELD_SERIES = {
    "2Y": "DGS2",
    "10Y": "DGS10",
    "30Y": "DGS30",
}

def get_yield_data(period="6mo"):
    """
    Pull daily Treasury yields (2Y, 10Y, 30Y) via the FRED API.
    Returns a DataFrame with one column per maturity.
    """
    data = {}
    for label, series_id in FRED_YIELD_SERIES.items():
        data[label] = fred.get_series(series_id)

    yields = pd.DataFrame(data)
    yields = yields.dropna(how="all")

    period_map = {
        "1mo": pd.DateOffset(months=1),
        "3mo": pd.DateOffset(months=3),
        "6mo": pd.DateOffset(months=6),
        "1y": pd.DateOffset(years=1),
        "5y": pd.DateOffset(years=5),
    }

    if period == "ytd":
        start = pd.Timestamp(year=pd.Timestamp.today().year, month=1, day=1)
    else:
        start = yields.index.max() - period_map[period]

    return yields.loc[yields.index >= start]

def get_latest_yields():
    """
    Returns a dict of {maturity: (date, latest_yield)} using the most recent
    available value for each Treasury series.
    """
    latest = {}
    for label, series_id in FRED_YIELD_SERIES.items():
        series = fred.get_series(series_id).dropna()
        latest[label] = (series.index[-1], series.iloc[-1])
    return latest

VOL_TICKERS = {
    "VIX": "^VIX",
    "VIX3M": "^VIX3M",
    "VIX EQ": "^VXEWZ",
}

def get_vol_data(period="6mo", include=None):
    """
    Pull VIX and optionally a comparison vol series over a period.
    include: None, "VIX3M", or "VIX EQ" - controls which second series to fetch.
    Returns a DataFrame with 'VIX' always present, plus the selected series if any.
    """
    tickers_to_pull = ["^VIX"]
    labels = {"^VIX": "VIX"}

    if include is not None:
        ticker = VOL_TICKERS[include]
        tickers_to_pull.append(ticker)
        labels[ticker] = include

    raw = yf.download(tickers_to_pull, period=period, auto_adjust=True,
                       group_by="column", progress=False)

    closes = raw["Close"].rename(columns=labels)
    return closes

GEO_TICKERS = {
    "Dollar": "DX-Y.NYB",  # US Dollar Index
    "Gold": "GC=F",        # Gold futures
    "Oil": "CL=F",         # WTI Crude futures
}

def get_geo_data(period="6mo"):
    """
    Pull Dollar Index, Gold, and Oil futures over a period.
    Returns a dict of {label: Series}, since these are on very different scales
    and typically shown as separate plots rather than one combined chart.
    """
    raw = yf.download(list(GEO_TICKERS.values()), period=period, auto_adjust=True,
                       group_by="column", progress=False)
    closes = raw["Close"]

    label_map = {v: k for k, v in GEO_TICKERS.items()}
    closes = closes.rename(columns=label_map)
    return closes

REGIME_TICKERS = {
    "SPY": "SPY",
    "TLT": "TLT",
    "Gold": "GC=F",
    "Oil": "CL=F",
    "DXY": "DX-Y.NYB",
    "VIX": "^VIX",
}

def get_regime_correlation(period="6mo"):
    """
    Pull daily prices for 6 cross-asset proxies, compute daily returns,
    and return their pairwise correlation matrix over the given period.
    """
    raw = yf.download(list(REGIME_TICKERS.values()), period=period, auto_adjust=True,
                       group_by="column", progress=False)
    closes = raw["Close"]

    label_map = {v: k for k, v in REGIME_TICKERS.items()}
    closes = closes.rename(columns=label_map)

    returns = closes.pct_change().dropna()
    corr_matrix = returns.corr()
    return corr_matrix