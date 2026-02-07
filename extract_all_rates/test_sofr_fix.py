#!/usr/bin/env python3
"""
Test SOFR extraction logic to ensure 1-month is correctly identified
and not confused with 12-month
"""

from bs4 import BeautifulSoup

# Sample HTML matching the actual structure from global-rates.com
sample_html = """
<table class="tablesorter">
<tr>
    <td><a href="/en/interest-rates/cme-term-sofr/1/term-sofr-interest-1-month/">CME Term SOFR 1 month</a></td>
    <td>3.67738 %</td>
</tr>
<tr>
    <td><a href="/en/interest-rates/cme-term-sofr/2/term-sofr-interest-3-months/">CME Term SOFR 3 months</a></td>
    <td>3.67113 %</td>
</tr>
<tr>
    <td><a href="/en/interest-rates/cme-term-sofr/3/term-sofr-interest-6-months/">CME Term SOFR 6 months</a></td>
    <td>3.62770 %</td>
</tr>
<tr>
    <td><a href="/en/interest-rates/cme-term-sofr/4/term-sofr-interest-12-months/">CME Term SOFR 12 months</a></td>
    <td>3.49381 %</td>
</tr>
</table>
"""

def test_sofr_extraction():
    """Test the extraction logic"""
    soup = BeautifulSoup(sample_html, 'html.parser')
    table = soup.find('table')
    
    sofr_rates = {}
    rows = table.find_all('tr')
    
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) >= 2:
            tenor = cells[0].get_text(strip=True).lower()
            rate = cells[1].get_text(strip=True)
            
            # Clean rate
            cleaned = ''.join(c for c in rate if c.isdigit() or c in '.-')
            rate_value = float(cleaned)
            
            # Match exact tenors - be specific to avoid matching "1" in "12"
            if ('1 month' in tenor or '1-month' in tenor or '1month' in tenor) and '12' not in tenor:
                sofr_rates['1M'] = rate_value
                print(f"✓ Matched 1M: '{tenor}' -> {rate_value}%")
            elif '3 month' in tenor or '3-month' in tenor or '3month' in tenor:
                sofr_rates['3M'] = rate_value
                print(f"✓ Matched 3M: '{tenor}' -> {rate_value}%")
            elif '6 month' in tenor or '6-month' in tenor or '6month' in tenor:
                sofr_rates['6M'] = rate_value
                print(f"✓ Matched 6M: '{tenor}' -> {rate_value}%")
            elif '12 month' in tenor or '12-month' in tenor or '12month' in tenor:
                print(f"  Skipped 12M: '{tenor}' -> {rate_value}% (correctly ignored)")
    
    print("\nExtraction Results:")
    print(f"  1M SOFR: {sofr_rates.get('1M', 'NOT FOUND')}%")
    print(f"  3M SOFR: {sofr_rates.get('3M', 'NOT FOUND')}%")
    print(f"  6M SOFR: {sofr_rates.get('6M', 'NOT FOUND')}%")
    
    # Verify results
    expected = {
        '1M': 3.67738,
        '3M': 3.67113,
        '6M': 3.62770
    }
    
    success = True
    print("\nValidation:")
    for period, expected_rate in expected.items():
        if sofr_rates.get(period) == expected_rate:
            print(f"  ✓ {period}: {expected_rate}% (CORRECT)")
        else:
            print(f"  ✗ {period}: Expected {expected_rate}%, got {sofr_rates.get(period, 'MISSING')}")
            success = False
    
    # Most important check: make sure we didn't pick up 12M as 1M
    if sofr_rates.get('1M') == 3.49381:
        print("\n✗✗✗ CRITICAL ERROR: 1M picked up 12-month rate! ✗✗✗")
        success = False
    elif sofr_rates.get('1M') == 3.67738:
        print("\n✓✓✓ SUCCESS: 1M correctly identified (not confused with 12M) ✓✓✓")
    
    return success

if __name__ == "__main__":
    print("=" * 70)
    print("SOFR EXTRACTION TEST")
    print("=" * 70)
    print("\nTesting that 1-month SOFR is correctly distinguished from 12-month...")
    print()
    
    success = test_sofr_extraction()
    
    print("\n" + "=" * 70)
    if success:
        print("ALL TESTS PASSED ✓")
    else:
        print("TESTS FAILED ✗")
    print("=" * 70)
    
    exit(0 if success else 1)
