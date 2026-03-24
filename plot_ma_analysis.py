#!/usr/bin/env python3
"""
Swap Implied Rate Moving Average Breakout Analysis
===================================================
Combines output_historical_*.xlsx and output_master_*.xlsx for each tenor,
computes 60-day and 200-day moving averages on Implied_SGD_Rate_Pct, and
produces charts showing whether the latest data points represent a breakout.

Output:
  output_combined_1m/3m/6m.xlsx       — merged time series
  swap_implied_ma_analysis.png         — 3-panel chart (all tenors)
  swap_implied_ma_1m/3m/6m.png        — individual charts per tenor

Usage:
    python3 plot_ma_analysis.py
"""

import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TENORS = ['1m', '3m', '6m']
TENOR_LABELS = {'1m': '1M', '3m': '3M', '6m': '6M'}

# ---------------------------------------------------------------------------
# Step 1 — Combine historical + master files
# ---------------------------------------------------------------------------

def combine_files(tenor):
    """
    Load and merge output_historical_{tenor}.xlsx and output_master_{tenor}.xlsx.
    Deduplicates on Trade_Date, preferring master values on overlap.
    Returns a sorted DataFrame.
    """
    hist_path   = os.path.join(BASE_DIR, f'output_historical_{tenor}.xlsx')
    master_path = os.path.join(BASE_DIR, f'output_master_{tenor}.xlsx')

    hist   = pd.read_excel(hist_path,   sheet_name='Results')
    master = pd.read_excel(master_path, sheet_name='Results')

    hist['Trade_Date']   = pd.to_datetime(hist['Trade_Date'])
    master['Trade_Date'] = pd.to_datetime(master['Trade_Date'])

    # Tag source so we can prefer master on duplicates
    hist['_src']   = 'historical'
    master['_src'] = 'master'

    combined = pd.concat([hist, master], ignore_index=True)

    # Sort so master rows come last, then drop duplicates keeping last (= master)
    combined = combined.sort_values(['Trade_Date', '_src'])
    combined = combined.drop_duplicates(subset=['Trade_Date'], keep='last')
    combined = combined.drop(columns=['_src'])
    combined = combined.sort_values('Trade_Date').reset_index(drop=True)

    return combined


def save_combined(df, tenor):
    out_path = os.path.join(BASE_DIR, f'output_combined_{tenor}.xlsx')
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Results', index=False)
    return out_path


# ---------------------------------------------------------------------------
# Step 2 — Compute moving averages
# ---------------------------------------------------------------------------

def add_moving_averages(df):
    rate = df['Implied_SGD_Rate_Pct']
    df = df.copy()
    df['MA60'] = rate.rolling(window=60, min_periods=1).mean()
    return df


# ---------------------------------------------------------------------------
# Step 3 — Plot a single tenor subplot
# ---------------------------------------------------------------------------

def plot_tenor(ax, df, tenor_label, zoom_start=None):
    """
    Draw rate series, MA60, and annotate the last 2 points onto ax.
    zoom_start: pd.Timestamp to restrict visible x/y range, or None for full history.
    """
    dates = df['Trade_Date']
    rate  = df['Implied_SGD_Rate_Pct']
    ma60  = df['MA60']

    # Full rate series (thin, light)
    ax.plot(dates, rate, color='#aaaaaa', linewidth=0.8, label='Implied SGD Rate', zorder=1)

    # 60-day MA (computed on full history regardless of zoom)
    ax.plot(dates, ma60, color='#1f77b4', linewidth=1.8, label='60-day MA', zorder=2)

    # Dashed horizontal reference line at latest MA60 value
    latest_ma60 = ma60.dropna().iloc[-1]
    ax.axhline(latest_ma60, color='#1f77b4', linestyle='--', linewidth=0.9, alpha=0.6)

    # Last 2 data points
    last2 = df.dropna(subset=['Implied_SGD_Rate_Pct']).tail(2)
    ax.scatter(last2['Trade_Date'], last2['Implied_SGD_Rate_Pct'],
               color='red', s=60, zorder=5, label='Recent (last 2 pts)')

    for _, row in last2.iterrows():
        label_str = f"{row['Trade_Date'].strftime('%b %d')}\n{row['Implied_SGD_Rate_Pct']:.3f}%"
        ax.annotate(
            label_str,
            xy=(row['Trade_Date'], row['Implied_SGD_Rate_Pct']),
            xytext=(8, 6), textcoords='offset points',
            fontsize=8, color='red',
            arrowprops=dict(arrowstyle='->', color='red', lw=0.8)
        )

    # X / Y limits
    x_start = zoom_start if zoom_start is not None else dates.min() - pd.Timedelta(days=5)
    ax.set_xlim(x_start, dates.max() + pd.Timedelta(days=5))

    visible = df[df['Trade_Date'] >= x_start]
    vis_vals = pd.concat([
        visible['Implied_SGD_Rate_Pct'].dropna(),
        visible['MA60'].dropna(),
    ])
    y_min, y_max = vis_vals.min(), vis_vals.max()
    y_pad = (y_max - y_min) * 0.15 or 0.05
    ax.set_ylim(y_min - y_pad, y_max + y_pad)

    # Breakout annotation box
    latest_rate = last2['Implied_SGD_Rate_Pct'].iloc[-1]
    above60 = latest_rate > latest_ma60
    breakout_text = (
        f"Latest: {latest_rate:.3f}%\n"
        f"MA60:  {latest_ma60:.3f}%  ({'▲ ABOVE' if above60 else '▼ BELOW'})"
    )
    ax.text(0.01, 0.97, breakout_text, transform=ax.transAxes,
            fontsize=8.5, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='lightyellow', alpha=0.9))

    range_label = f'from {zoom_start.strftime("%b %Y")}' if zoom_start else 'full history'
    ax.set_title(f'USD/SGD {tenor_label} Swap Implied SGD Rate — MA60 ({range_label})',
                 fontsize=11, fontweight='bold')
    ax.set_ylabel('Rate (%)', fontsize=9)
    month_interval = 1 if zoom_start else 2
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=month_interval))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)
    ax.yaxis.set_tick_params(labelsize=8)
    ax.grid(axis='y', linestyle=':', alpha=0.5)
    ax.grid(axis='x', linestyle=':', alpha=0.3)

    legend_elements = [
        Line2D([0], [0], color='#aaaaaa', linewidth=0.8, label='Implied SGD Rate'),
        Line2D([0], [0], color='#1f77b4', linewidth=1.8, label=f'60-day MA ({latest_ma60:.3f}%)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=7,
               label='Last 2 data points'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=8, framealpha=0.85)


# ---------------------------------------------------------------------------
# Step 4 — Build and save charts
# ---------------------------------------------------------------------------

def plot_all(data_by_tenor, zoom_start, file_suffix, suptitle):
    """Save a 3-panel combined PNG and 3 individual PNGs for the given zoom window."""
    fig, axes = plt.subplots(3, 1, figsize=(16, 18))
    fig.suptitle(suptitle, fontsize=14, fontweight='bold', y=0.995)

    for ax, tenor in zip(axes, TENORS):
        plot_tenor(ax, data_by_tenor[tenor], TENOR_LABELS[tenor], zoom_start)

    plt.tight_layout(rect=[0, 0, 1, 0.995])
    combined_path = os.path.join(BASE_DIR, f'swap_implied_ma_analysis_{file_suffix}.png')
    fig.savefig(combined_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {os.path.basename(combined_path)}")

    for tenor in TENORS:
        fig, ax = plt.subplots(figsize=(14, 6))
        plot_tenor(ax, data_by_tenor[tenor], TENOR_LABELS[tenor], zoom_start)
        plt.tight_layout()
        ind_path = os.path.join(BASE_DIR, f'swap_implied_ma_{tenor}_{file_suffix}.png')
        fig.savefig(ind_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  Saved: {os.path.basename(ind_path)}")


# ---------------------------------------------------------------------------
# Step 5 — Console breakout summary
# ---------------------------------------------------------------------------

def print_summary(data_by_tenor):
    print()
    print("=" * 70)
    print("BREAKOUT SUMMARY (vs latest MA values)")
    print("=" * 70)
    for tenor in TENORS:
        df = data_by_tenor[tenor]
        last_row = df.dropna(subset=['Implied_SGD_Rate_Pct']).iloc[-1]
        latest   = last_row['Implied_SGD_Rate_Pct']
        ma60     = last_row['MA60']
        above60  = '▲ ABOVE' if latest > ma60 else '▼ BELOW'
        date_str = last_row['Trade_Date'].strftime('%Y-%m-%d')
        print(f"  {TENOR_LABELS[tenor]}  [{date_str}]  "
              f"Latest={latest:.4f}%  "
              f"MA60={ma60:.4f}% ({above60})")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("SWAP IMPLIED RATE MA BREAKOUT ANALYSIS")
    print("=" * 70)

    data_by_tenor = {}

    print("\n[1/3] Combining and saving files...")
    for tenor in TENORS:
        df = combine_files(tenor)
        df = add_moving_averages(df)
        data_by_tenor[tenor] = df
        out = save_combined(df.drop(columns=['MA60'], errors='ignore'), tenor)
        print(f"  {tenor.upper()}: {len(df)} rows "
              f"({df['Trade_Date'].min().date()} – {df['Trade_Date'].max().date()}) "
              f"→ {os.path.basename(out)}")

    print("\n[2/3] Generating charts...")
    plot_all(data_by_tenor,
             zoom_start=pd.Timestamp('2025-10-02'),
             file_suffix='recent',
             suptitle='USD/SGD Swap Implied SGD Rates — MA60 Breakout (Oct 2025 – present)')
    plot_all(data_by_tenor,
             zoom_start=None,
             file_suffix='full',
             suptitle='USD/SGD Swap Implied SGD Rates — MA60 Breakout (full history)')

    print("\n[3/3] Breakout analysis...")
    print_summary(data_by_tenor)

    # Gap reminder
    print()
    print("NOTE: If a gap exists in early March, the MA lines bridge it correctly.")
    print("      To backfill it, extend FWD_Points_Actual_Historical.xlsx through")
    print("      the missing dates and re-run build_historical_dataset.py.")


if __name__ == '__main__':
    main()
