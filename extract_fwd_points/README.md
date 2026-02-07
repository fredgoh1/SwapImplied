# USD/SGD Forward Points Extractor

This script extracts 1-month, 3-month, and 6-month USD/SGD forward points from Investing.com and saves them to an Excel file with professional formatting.

## Features

- ✅ Extracts forward points for 1M, 3M, and 6M periods
- ✅ Saves data to professionally formatted Excel file
- ✅ Two extraction methods: requests (fast) and Selenium (reliable)
- ✅ Automatic fallback to Selenium if requests fails
- ✅ Includes bid, ask, high, low, change, and timestamp data
- ✅ Color-coded Excel output with frozen headers

## Installation

### Required Python Packages

```bash
pip install requests beautifulsoup4 openpyxl
```

### Optional (for Selenium mode)

```bash
pip install selenium webdriver-manager
```

For Selenium mode, you'll also need Chrome browser installed. The script will automatically download ChromeDriver if you have `webdriver-manager` installed.

## Usage

### Basic Usage (Requests Method)

```bash
python extract_forward_points_selenium.py
```

This uses the faster requests method, which usually works but may occasionally be blocked by anti-bot measures.

### Using Selenium (More Reliable)

```bash
python extract_forward_points_selenium.py --selenium
```

This launches a headless Chrome browser to extract the data. It's slower but more reliable.

### Custom Output Filename

```bash
python extract_forward_points_selenium.py -o my_custom_filename.xlsx
```

### Help

```bash
python extract_forward_points_selenium.py --help
```

## Output

The script creates an Excel file with the following structure:

| Period   | Bid      | Ask      | High     | Low      | Change   | Time     |
|----------|----------|----------|----------|----------|----------|----------|
| 1-Month  | -27.4700 | -27.1700 | -27.4700 | -27.3000 | 0.0900   | 0:56:29  |
| 3-Month  | -77.7300 | -77.3300 | -77.6500 | -77.5500 | -0.0100  | 0:57:44  |
| 6-Month  | -148.9700| -147.9700| -148.6000| -148.5000| 0.0300   | 0:56:14  |

**Note**: Forward points are in pips. Negative values indicate forward discount.

## Excel File Features

- Professional formatting with color-coded headers
- Alternating row colors for readability
- Frozen header row for easy scrolling
- Automatic column width adjustment
- Extraction timestamp
- Source URL reference

## Troubleshooting

### "Failed to extract forward points data"

1. **Check internet connection**: Ensure you can access https://www.investing.com
2. **Try Selenium mode**: Run with `--selenium` flag
3. **Install Chrome**: Required for Selenium mode
4. **Check firewall**: Ensure Python can make outbound connections

### Selenium Issues

1. **Chrome not found**: Install Chrome browser
2. **ChromeDriver issues**: Install webdriver-manager: `pip install webdriver-manager`
3. **Timeout errors**: The website may be slow; the script waits up to 15 seconds

### Import Errors

If you get import errors, install missing packages:
```bash
pip install requests beautifulsoup4 openpyxl selenium webdriver-manager
```

## Scheduling Automatic Extraction

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., daily at 9:00 AM)
4. Action: Start a program
   - Program: `python`
   - Arguments: `C:\path\to\extract_forward_points_selenium.py`
   - Start in: `C:\path\to\`

### Linux/Mac (cron)

Add to crontab (`crontab -e`):
```bash
# Run daily at 9:00 AM
0 9 * * * cd /path/to/script && /usr/bin/python3 extract_forward_points_selenium.py
```

## Data Source

Data is extracted from: https://www.investing.com/currencies/usd-sgd-forward-rates

**Disclaimer**: This script is for educational and personal use only. Please respect Investing.com's terms of service and use rate limiting if running frequently.

## Technical Details

### Extraction Methods

1. **Requests + BeautifulSoup**: 
   - Fast (< 5 seconds)
   - May be blocked by anti-bot measures
   - First choice for regular use

2. **Selenium + ChromeDriver**:
   - Slower (~15-20 seconds)
   - More reliable (simulates real browser)
   - Automatic fallback option

### Data Parsed

For each period (1M, 3M, 6M), the script extracts:
- **Bid**: Bid price in pips
- **Ask**: Ask price in pips  
- **High**: Day's high price
- **Low**: Day's low price
- **Change**: Change from previous close
- **Time**: Timestamp of last update

## Example Output

```
============================================================
USD/SGD Forward Points Extractor
============================================================

Using requests method...
✓ Found 1-Month: Bid=-27.4700, Ask=-27.1700
✓ Found 3-Month: Bid=-77.7300, Ask=-77.3300
✓ Found 6-Month: Bid=-148.9700, Ask=-147.9700

✓ Successfully extracted 3 forward rate entries

✓ Data successfully saved to usd_sgd_forward_points.xlsx

============================================================
SUCCESS! Excel file created: usd_sgd_forward_points.xlsx
============================================================
```

## License

This script is provided as-is for educational purposes. Use responsibly and in accordance with Investing.com's terms of service.
