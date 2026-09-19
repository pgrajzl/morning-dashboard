import matplotlib.pyplot as plt
import matplotlib as mpl
from ipywidgets import interact, Dropdown

mpl.rcParams["font.family"] = "Times New Roman"

def plot_index_performance(fetch_module):
    """
    Interactive plot of SPX and NDX with a timeframe dropdown.
    Each index gets its own subplot, with a text box below showing
    the prior-day % change.
    """
    timeframes = ["1mo", "3mo", "6mo", "ytd", "1y", "5y"]

    def _plot(period):
        df = fetch_module.get_index_data(period=period)
        changes = fetch_module.get_prior_day_change(df)

        fig, axes = plt.subplots(2, 1, figsize=(9, 8))

        for ax, col in zip(axes, df.columns):
            ax.plot(df.index, df[col], color="#9b59b6", linewidth=1.5)
            ax.set_title(col, fontsize=13)
            ax.set_ylabel("Level")
            ax.grid(alpha=0.3)

            # Prior-day change box, placed just below the plot
            pct = changes[col]
            color = "#2ecc71" if pct >= 0 else "#e74c3c"
            ax.text(
                0.01, -0.18, f"Prior day: {pct:+.2f}%",
                transform=ax.transAxes, fontsize=11,
                color="white", backgroundcolor=color,
                bbox=dict(facecolor=color, edgecolor="none", boxstyle="round,pad=0.4")
            )

        fig.tight_layout()
        plt.show()

    interact(_plot, period=Dropdown(options=timeframes, value="6mo", description="Timeframe:"))

def plot_sector_performance(fetch_module):
    """
    Bar chart of sector performance over a selectable lookback window,
    plus a separate bar chart showing prior-day change per sector.
    """
    timeframe_map = {
        "1d": "5d",     # pulled wider, but performance calc below uses full period return
        "5d": "5d",
        "15d": "1mo",   # yfinance has no native 15d period, closest clean option is 1mo, sliced
        "1mo": "1mo",
        "3mo": "3mo",
        "6mo": "6mo",
        "1y": "1y",
    }

    def _plot(period_label):
        period = timeframe_map[period_label]
        perf = fetch_module.get_sector_period_performance(period=period)
        prior_day = fetch_module.get_sector_prior_day_change()
        spx_date, spx_change = fetch_module.get_spx_prior_day_change()

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 9))

        # --- Top: performance over selected window ---
        colors1 = ["#2ecc71" if v >= 0 else "#e74c3c" for v in perf.values]
        ax1.bar(perf.index, perf.values, color=colors1)
        ax1.set_title(f"Sector Performance ({period_label})", fontsize=13)
        ax1.set_ylabel("% Change")
        ax1.axhline(0, color="black", linewidth=0.8)
        ax1.tick_params(axis="x", rotation=45)
        ax1.grid(alpha=0.3, axis="y")

        # --- Bottom: prior full trading day change, with date and SPX context ---
        colors2 = ["#2ecc71" if v >= 0 else "#e74c3c" for v in prior_day.values]
        ax2.bar(prior_day.index, prior_day.values, color=colors2)
        date_str = spx_date.strftime("%b %d, %Y")
        ax2.set_title(
            f"Prior Trading Day Change — {date_str}  (SPX: {spx_change:+.2f}%)",
            fontsize=13
        )
        ax2.set_ylabel("% Change")
        ax2.axhline(0, color="black", linewidth=0.8)

        # Reference line at SPX's move, so sector bars are visually benchmarked against it
        ax2.axhline(spx_change, color="#2c3e50", linestyle="--", linewidth=1, alpha=0.7)

        ax2.tick_params(axis="x", rotation=45)
        ax2.grid(alpha=0.3, axis="y")

        fig.tight_layout()
        plt.show()

    interact(_plot, period_label=Dropdown(
        options=list(timeframe_map.keys()), value="6mo", description="Timeframe:"
    ))

def plot_rsp_spy_ratio(fetch_module):
    """
    Interactive RSP/SPY ratio plot over a selectable timeframe.
    """
    timeframes = ["1mo", "3mo", "6mo", "ytd", "1y", "5y"]

    def _plot(period):
        ratio = fetch_module.get_rsp_spy_ratio(period=period)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(ratio.index, ratio.values, color="#9b59b6", linewidth=1.5)
        ax.set_title("RSP / SPY Ratio (Equal-Weight vs Cap-Weight)", fontsize=13)
        ax.set_ylabel("Ratio")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        plt.show()

    interact(_plot, period=Dropdown(options=timeframes, value="6mo", description="Timeframe:"))


def plot_market_breadth(fetch_module):
    """
    Histogram of prior-day % returns across all S&P 500 stocks, with
    % below 50-day and 200-day moving averages shown below as simple stats.
    """
    daily_returns, pct_below_50, pct_below_200 = fetch_module.get_breadth_data()

    advancers = (daily_returns > 0).sum()
    decliners = (daily_returns < 0).sum()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(daily_returns.values, bins=40, color="#9b59b6", edgecolor="white", alpha=0.85)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_title(
        f"S&P 500 Daily Return Distribution — {advancers} Advancers / {decliners} Decliners",
        fontsize=13
    )
    ax.set_xlabel("Prior Day % Change")
    ax.set_ylabel("Number of Stocks")
    ax.grid(alpha=0.3)

    stats_text = (
        f"% of S&P 500 below 50-day MA:  {pct_below_50:.1f}%\n"
        f"% of S&P 500 below 200-day MA: {pct_below_200:.1f}%"
    )
    ax.text(
        0.01, -0.22, stats_text, transform=ax.transAxes,
        fontsize=11, va="top",
        bbox=dict(facecolor="#ecf0f1", edgecolor="#bdc3c7", boxstyle="round,pad=0.5")
    )

    fig.tight_layout()
    plt.show()

def plot_yields(fetch_module):
    """
    Interactive plot of 2Y, 10Y, and 30Y Treasury yields on the same axis,
    over a selectable timeframe, with current-level boxes below.
    """
    timeframes = ["1mo", "3mo", "6mo", "ytd", "1y", "5y"]
    colors = {"2Y": "#e74c3c", "10Y": "#9b59b6", "30Y": "#2c3e50"}

    def _plot(period):
        yields = fetch_module.get_yield_data(period=period)
        latest = fetch_module.get_latest_yields()

        fig, ax = plt.subplots(figsize=(10, 5))
        for maturity in yields.columns:
            ax.plot(yields.index, yields[maturity], label=maturity,
                     color=colors[maturity], linewidth=1.5)

        ax.set_title(f"Treasury Yields ({period})", fontsize=13)
        ax.set_ylabel("Yield (%)")
        ax.set_xlabel("Date")
        ax.legend(loc="best", frameon=False)
        ax.grid(alpha=0.3)

        # Reference date for the current-level boxes below
        latest_date = max(date for date, _ in latest.values())
        date_str = latest_date.strftime("%b %d, %Y")

        ax.text(
            0.5, -0.20, f"Current Yields — {date_str}",
            transform=ax.transAxes, fontsize=11, ha="center",
            style="italic", color="#2c3e50"
        )

        # Three side-by-side boxes showing current level per maturity
        box_positions = [0.17, 0.5, 0.83]
        for pos, maturity in zip(box_positions, ["2Y", "10Y", "30Y"]):
            _, value = latest[maturity]
            ax.text(
                pos, -0.32, f"{maturity}: {value:.2f}%",
                transform=ax.transAxes, fontsize=12, ha="center",
                bbox=dict(facecolor=colors[maturity], edgecolor="none",
                          boxstyle="round,pad=0.5", alpha=0.85),
                color="white"
            )

        fig.tight_layout()
        plt.show()

    interact(_plot, period=Dropdown(options=timeframes, value="6mo", description="Timeframe:"))

def plot_volatility(fetch_module):
    """
    Interactive VIX plot with a toggle to add VIX3M or VIX EQ, and a
    timeframe dropdown.
    """
    timeframes = ["1mo", "3mo", "6mo", "ytd", "1y", "5y"]
    overlay_options = ["None", "VIX3M", "VIX EQ"]
    colors = {"VIX": "#9b59b6", "VIX3M": "#2c3e50", "VIX EQ": "#e74c3c"}

    def _plot(period, overlay):
        include = None if overlay == "None" else overlay
        vol = fetch_module.get_vol_data(period=period, include=include)

        fig, ax = plt.subplots(figsize=(10, 5))
        for col in vol.columns:
            ax.plot(vol.index, vol[col], label=col, color=colors[col], linewidth=1.5)

        title = "VIX" if include is None else f"VIX vs {include}"
        ax.set_title(f"{title} ({period})", fontsize=13)
        ax.set_ylabel("Level")
        ax.set_xlabel("Date")
        ax.legend(loc="best", frameon=False)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        plt.show()

    interact(
        _plot,
        period=Dropdown(options=timeframes, value="6mo", description="Timeframe:"),
        overlay=Dropdown(options=overlay_options, value="None", description="Overlay:")
    )

def plot_geopolitics(fetch_module):
    """
    Three side-by-side plots: Dollar Index, Gold, and Oil, over a
    selectable timeframe.
    """
    timeframes = ["1mo", "3mo", "6mo", "ytd", "1y", "5y"]
    colors = {"Dollar": "#2c3e50", "Gold": "#f1c40f", "Oil": "#34495e"}

    def _plot(period):
        geo = fetch_module.get_geo_data(period=period)

        fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

        ticker_display = {"Dollar": "DXY", "Gold": "GC=F", "Oil": "WTI"}

        for ax, label in zip(axes, ["Dollar", "Gold", "Oil"]):
            ax.plot(geo.index, geo[label], color=colors[label], linewidth=1.5)
            ax.set_title(f"{label} ({ticker_display[label]})", fontsize=13)
            ax.set_ylabel("Level")
            ax.grid(alpha=0.3)
            ax.tick_params(axis="x", rotation=45)

        fig.suptitle(f"Geopolitics ({period})", fontsize=14)
        fig.tight_layout()
        plt.show()

    interact(_plot, period=Dropdown(options=timeframes, value="6mo", description="Timeframe:"))

def plot_regime_correlation(fetch_module):
    """
    Heatmap of pairwise daily-return correlations across 6 cross-asset
    proxies (SPY, TLT, Gold, Oil, DXY, VIX), over a selectable timeframe.
    """
    timeframes = ["1mo", "3mo", "6mo", "ytd", "1y", "5y"]

    def _plot(period):
        corr = fetch_module.get_regime_correlation(period=period)

        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)

        ax.set_xticks(range(len(corr.columns)))
        ax.set_yticks(range(len(corr.columns)))
        ax.set_xticklabels(corr.columns, rotation=45, ha="right")
        ax.set_yticklabels(corr.columns)

        # Annotate each cell with its correlation value
        for i in range(len(corr.columns)):
            for j in range(len(corr.columns)):
                val = corr.values[i, j]
                text_color = "white" if abs(val) > 0.5 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        color=text_color, fontsize=9)

        ax.set_title(f"Cross-Asset Correlation ({period})", fontsize=13)
        fig.colorbar(im, ax=ax, label="Correlation")
        fig.tight_layout()
        plt.show()

    interact(_plot, period=Dropdown(options=timeframes, value="6mo", description="Timeframe:"))

def plot_macro(fetch_module):
    """
    Interactive plot of a selected macro series, with dropdowns for
    both the metric and the timeframe.
    """
    metrics = list(fetch_module.MACRO_SERIES.keys())
    timeframes = ["1y", "3y", "5y", "10y", "max"]

    def _plot(metric, period):
        series = fetch_module.get_macro_series(metric, period=period)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(series.index, series.values, color="#9b59b6", linewidth=1.5)
        ax.set_title(f"{metric} ({period})", fontsize=13)
        ax.set_ylabel(metric)
        ax.set_xlabel("Date")
        ax.grid(alpha=0.3)

        latest_date = series.index[-1].strftime("%b %Y")
        latest_val = series.iloc[-1]
        ax.text(
            0.01, -0.15, f"Latest ({latest_date}): {latest_val:.2f}",
            transform=ax.transAxes, fontsize=11, color="#2c3e50"
        )

        fig.tight_layout()
        plt.show()

    interact(
        _plot,
        metric=Dropdown(options=metrics, value="Unemployment Rate", description="Metric:"),
        period=Dropdown(options=timeframes, value="5y", description="Timeframe:")
    )