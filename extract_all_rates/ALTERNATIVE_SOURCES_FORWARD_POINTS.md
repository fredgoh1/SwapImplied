# Alternative Data Sources for USD/SGD Forward Points

## Problem with Investing.com

Investing.com uses JavaScript to dynamically load the forward rates table. When using `requests` library, we get the page skeleton but not the actual data. Selenium can work but is complex and slow.

## Alternative Sources

### Option 1: Bloomberg (Subscription Required)
- **URL**: Bloomberg Terminal
- **Pros**: Most reliable, real-time data
- **Cons**: Expensive subscription ($2,000+/month)
- **Data**: All tenors including 1M, 3M, 6M forward points

### Option 2: Thomson Reuters Eikon/Refinitiv (Subscription Required)
- **URL**: Refinitiv Workspace
- **Pros**: Professional-grade data, API access
- **Cons**: Expensive subscription
- **Data**: Complete forward curve

### Option 3: SGX Data (Singapore Exchange)
- **URL**: https://www.sgx.com/research-education/derivatives
- **Pros**: Official Singapore data, free
- **Cons**: May not have forward points directly
- **Data**: FX futures which can derive forward points

### Option 4: MAS (Monetary Authority of Singapore)
- **URL**: https://www.mas.gov.sg/statistics/exchange-rates/swap-points
- **Status**: Currently blocks automated access (403 error)
- **Pros**: Official source, should be most accurate
- **Cons**: Anti-bot measures, may require manual access
- **Workaround**: Manual download and input

### Option 5: OANDA API (Free Tier Available)
- **URL**: https://www1.oanda.com/forex-trading/markets/live
- **API Docs**: https://developer.oanda.com/
- **Pros**: Free tier, API access, forward points available
- **Cons**: Need API key, limited free requests
- **Data**: Forward points for major pairs including USD/SGD

### Option 6: Dukascopy
- **URL**: https://www.dukascopy.com/swiss/english/marketwatch/historical/
- **Pros**: Historical data download, free
- **Cons**: Forward points may not be directly available
- **Data**: Spot rates, may need to calculate forward points

### Option 7: Yahoo Finance / Google Finance
- **Status**: Do not provide forward points
- **Only provides**: Spot FX rates

### Option 8: FX Forward Calculator (Manual Calculation)
Calculate forward points using interest rate parity:

**Formula:**
```
Forward Points = Spot Rate × ((1 + Foreign Rate × Days/360) / (1 + Domestic Rate × Days/360) - 1) × 10000
```

Where:
- Spot Rate = Current USD/SGD rate
- Foreign Rate = USD interest rate (use SOFR)
- Domestic Rate = SGD interest rate (use SORA - Singapore Overnight Rate Average)
- Days = Number of days in forward period

**For 1-month:**
```python
import requests

# Get spot rate from free API
spot_response = requests.get("https://open.er-api.com/v6/latest/USD")
spot_rate = spot_response.json()['rates']['SGD']

# Use SOFR rates we already extracted (in decimal, e.g., 4.50% = 0.045)
sofr_1m = 0.0450

# Get SORA rate (Singapore equivalent of SOFR)
# Source: https://www.abs.org.sg/benchmark-rates/sora
# For now, approximate as SOFR minus 0.5% (typical spread)
sora_1m = sofr_1m - 0.005

# Calculate 1-month forward points (30 days)
days = 30
forward_rate = spot_rate * ((1 + sofr_1m * days/360) / (1 + sora_1m * days/360))
forward_points = (forward_rate - spot_rate) * 10000

print(f"1M Forward Points: {forward_points:.2f}")
```

## RECOMMENDED SOLUTIONS

### Best Option: Use OANDA API

**Setup:**
1. Register at https://www.oanda.com/
2. Get free API key from https://developer.oanda.com/
3. Use API to get forward points

**Python Example:**
```python
import requests

def get_oanda_forward_points(api_key, pair='USD_SGD'):
    url = f"https://api-fxtrade.oanda.com/v3/accounts/{account_id}/pricing"
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    params = {
        'instruments': pair
    }
    response = requests.get(url, headers=headers, params=params)
    # Parse forward points from response
    return response.json()
```

### Pragmatic Option: Calculate from SOFR + SORA

Since you're already extracting SOFR rates successfully, you can:
1. Extract SOFR rates (already working)
2. Get SORA rates from ABS Singapore
3. Get spot USD/SGD rate (already working)
4. Calculate forward points using interest rate parity formula

**Pros:**
- Uses data you already have
- No new subscriptions needed
- Mathematically correct

**Cons:**
- Slightly less accurate than actual market forward points
- Need to also scrape SORA rates

### Quick Fix: Manual Input with Template

Create a simple template where you manually enter forward points from any source:

```python
# manual_forward_points.py
from datetime import datetime

def get_manual_forward_points():
    """
    Manually input forward points from any source
    Visit: https://www.investing.com/currencies/usd-sgd-forward-rates
    Or your broker platform
    """
    print("=" * 60)
    print("MANUAL FORWARD POINTS INPUT")
    print("=" * 60)
    print("\nPlease visit:")
    print("https://www.investing.com/currencies/usd-sgd-forward-rates")
    print("\nOr check your broker platform for USD/SGD forward points")
    print()
    
    # Get input
    fp_1m_bid = float(input("1M Forward - Bid: "))
    fp_1m_ask = float(input("1M Forward - Ask: "))
    
    fp_3m_bid = float(input("3M Forward - Bid: "))
    fp_3m_ask = float(input("3M Forward - Ask: "))
    
    fp_6m_bid = float(input("6M Forward - Bid: "))
    fp_6m_ask = float(input("6M Forward - Ask: "))
    
    # Calculate mid rates
    forward_points = {
        '1M': round((fp_1m_bid + fp_1m_ask) / 2, 4),
        '3M': round((fp_3m_bid + fp_3m_ask) / 2, 4),
        '6M': round((fp_6m_bid + fp_6m_ask) / 2, 4)
    }
    
    print("\nCalculated Mid Rates:")
    for period, value in forward_points.items():
        print(f"  {period}: {value}")
    
    return forward_points
```

## Implementation Priority

1. **Immediate**: Manual input (works now, requires 2 minutes daily)
2. **Short-term**: Calculate from SOFR + SORA (automated, ~90% accurate)
3. **Long-term**: OANDA API (fully automated, requires API key setup)

## Singapore SORA Rate Sources

To calculate forward points, you'll also need SORA rates:

1. **ABS Benchmarks** (Official): https://www.abs.org.sg/benchmark-rates/sora
2. **MAS Statistics**: https://www.mas.gov.sg/statistics/
3. **SGX**: Market data section

## Sample Code: Calculate Forward Points

```python
def calculate_forward_points(spot_rate, sofr_rate, sora_rate, days):
    """
    Calculate forward points using interest rate parity
    
    Args:
        spot_rate: Current USD/SGD spot rate
        sofr_rate: USD interest rate (annual, in decimal form)
        sora_rate: SGD interest rate (annual, in decimal form)
        days: Forward period in days
    
    Returns:
        Forward points in pips
    """
    forward_rate = spot_rate * (
        (1 + sofr_rate * days / 360) / 
        (1 + sora_rate * days / 360)
    )
    forward_points = (forward_rate - spot_rate) * 10000
    return round(forward_points, 4)

# Example usage:
spot = 1.3450  # Current USD/SGD
sofr_1m = 0.0450  # 4.50% annual
sora_1m = 0.0400  # 4.00% annual (estimate)

fp_1m = calculate_forward_points(spot, sofr_1m, sora_1m, 30)
fp_3m = calculate_forward_points(spot, sofr_1m * 3, sora_1m * 3, 90)
fp_6m = calculate_forward_points(spot, sofr_1m * 6, sora_1m * 6, 180)

print(f"1M: {fp_1m}, 3M: {fp_3m}, 6M: {fp_6m}")
```

---

**Recommendation**: Start with manual input while implementing the calculated approach using SOFR + SORA rates.
