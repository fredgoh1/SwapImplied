# Troubleshooting Selenium Timeout Issues

## Common Error Messages

### "Read timed out" or "Connection timeout"

This typically occurs when:
1. ChromeDriver is not properly installed
2. Chrome browser is not installed
3. Network/firewall is blocking connections
4. The page is taking too long to load

## Solutions (Try in Order)

### Solution 1: Use Requests Mode (Fastest)

The timeout happens in Selenium mode. Try the default requests mode first:

```bash
# Don't use --selenium flag
python update_swap_implied_data.py
```

This is faster and usually works fine for forward points extraction.

### Solution 2: Install/Update Chrome and ChromeDriver

**Windows:**
1. Download and install Chrome: https://www.google.com/chrome/
2. Install webdriver-manager (auto-downloads ChromeDriver):
   ```bash
   pip install webdriver-manager
   ```

**Linux (Ubuntu/Debian):**
```bash
# Install Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb

# Install ChromeDriver automatically
pip install webdriver-manager
```

**macOS:**
```bash
# Install Chrome
brew install --cask google-chrome

# Install ChromeDriver automatically
pip install webdriver-manager
```

### Solution 3: Check Chrome Installation

Verify Chrome is installed:

```bash
# Linux/Mac
google-chrome --version

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --version
```

### Solution 4: Manual ChromeDriver Installation

If webdriver-manager isn't working:

1. Check your Chrome version
2. Download matching ChromeDriver from: https://chromedriver.chromium.org/downloads
3. Place it in your PATH or project directory

### Solution 5: Increase Timeout Settings

If the page is just slow, you can increase timeouts by editing the script:

In `update_swap_implied_data.py`, find this line:
```python
driver.set_page_load_timeout(30)  # 30 seconds
```

Change to:
```python
driver.set_page_load_timeout(60)  # 60 seconds
```

### Solution 6: Check Firewall/Network

Some corporate networks block Selenium. Try:

1. Disable VPN temporarily
2. Check firewall settings
3. Try on a different network (e.g., mobile hotspot)

### Solution 7: Use a Different Browser (Firefox)

If Chrome doesn't work, you can modify the script to use Firefox:

```python
# Install geckodriver for Firefox
pip install webdriver-manager

# Then in the script, replace Chrome with Firefox
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options as FirefoxOptions
```

## Quick Diagnosis Script

Create a file `test_selenium.py`:

```python
#!/usr/bin/env python3
"""Quick Selenium diagnostic script"""

try:
    print("1. Testing Chrome availability...")
    import subprocess
    result = subprocess.run(['google-chrome', '--version'], 
                          capture_output=True, text=True, timeout=5)
    print(f"   ✓ Chrome found: {result.stdout.strip()}")
except Exception as e:
    print(f"   ✗ Chrome not found: {e}")

try:
    print("\n2. Testing Selenium import...")
    from selenium import webdriver
    print("   ✓ Selenium installed")
except ImportError:
    print("   ✗ Selenium not installed - run: pip install selenium")
    exit(1)

try:
    print("\n3. Testing webdriver-manager...")
    from webdriver_manager.chrome import ChromeDriverManager
    print("   ✓ webdriver-manager installed")
except ImportError:
    print("   ⚠ webdriver-manager not installed (optional)")
    print("     Install with: pip install webdriver-manager")

try:
    print("\n4. Testing Chrome WebDriver initialization...")
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except:
        driver = webdriver.Chrome(options=options)
    
    print("   ✓ Chrome WebDriver initialized successfully")
    
    print("\n5. Testing page load...")
    driver.set_page_load_timeout(30)
    driver.get("https://www.google.com")
    print("   ✓ Page loaded successfully")
    
    driver.quit()
    print("\n✓✓✓ ALL TESTS PASSED - Selenium is working correctly! ✓✓✓")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    print("\nTroubleshooting steps:")
    print("1. Install Chrome browser")
    print("2. Run: pip install selenium webdriver-manager")
    print("3. Check firewall/antivirus settings")
    print("4. Try: pip uninstall selenium && pip install selenium")
```

Run it:
```bash
python test_selenium.py
```

## Recommended: Don't Use Selenium Unless Needed

For most cases, the default requests mode works fine:

```bash
# This usually works and is much faster
python update_swap_implied_data.py
```

Only use `--selenium` if:
- You get blocked by anti-bot measures
- The website requires JavaScript to load data
- Requests mode consistently fails

## Still Having Issues?

### Workaround: Manual Data Entry

If all else fails, you can manually extract the data and update files:

1. Visit the websites in your browser:
   - SOFR: https://www.global-rates.com/en/interest-rates/cme-term-sofr/
   - Forward Points: https://www.investing.com/currencies/usd-sgd-forward-rates
   
2. Note down the values

3. Use Python to update files:

```python
import pandas as pd
from datetime import datetime

# Your manual values
date = datetime.now().strftime('%Y-%m-%d')
sofr_1m = 3.68  # Your value
sofr_3m = 3.67  # Your value
sofr_6m = 3.63  # Your value
fx = 1.345      # Your value
fp_1m = -27.3   # Your value
fp_3m = -77.5   # Your value
fp_6m = -148.5  # Your value

# Update files
for period, sofr, fp in [('1m', sofr_1m, fp_1m), 
                         ('3m', sofr_3m, fp_3m), 
                         ('6m', sofr_6m, fp_6m)]:
    filepath = f'../swap_implied_input/input_master_{period}.xlsx'
    df = pd.read_excel(filepath)
    new_row = {
        'Date': date,
        f'{period[0]}mSOFR': sofr,
        'USDSGD_FX': fx,
        'ForwardPoints': fp
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(filepath, index=False)
    print(f"✓ Updated {period}")
```

## Error Reference

| Error Message | Most Likely Cause | Solution |
|---------------|-------------------|----------|
| `Read timed out` | ChromeDriver connection issue | Use requests mode (no --selenium) |
| `Chrome not found` | Chrome not installed | Install Chrome browser |
| `chromedriver not found` | ChromeDriver missing | Install webdriver-manager |
| `Session not created` | Version mismatch | Update Chrome and ChromeDriver |
| `Network error` | Firewall/proxy blocking | Check network settings |

---

**TL;DR:** Don't use `--selenium` flag unless the default mode fails. It's faster and more reliable.
