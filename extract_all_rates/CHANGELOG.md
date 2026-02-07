# CHANGELOG - Version 2.2

## Fixes Applied

### Version 2.2 (February 6, 2025) - Timeout Fix

**Problem:** Selenium mode experiencing timeout errors when extracting forward points:
```
Error: HTTPConnectionPool(host='localhost', port=61526): Read timed out
```

**Changes:**
1. **Improved Selenium timeout handling**
   - Added explicit page load timeout (30 seconds)
   - Added script timeout (30 seconds)
   - Better error messages indicating timeout vs other issues
   - Proper cleanup of ChromeDriver on timeout

2. **Better error messages and guidance**
   - Clear indication when using Selenium vs requests mode
   - Progress messages during extraction
   - Specific tips when timeout occurs
   - Recommendation to avoid --selenium unless needed

3. **Graceful fallback behavior**
   - Requests mode tries first (fast, no timeout issues)
   - Only suggests --selenium when requests mode fails
   - Better exception handling for both modes

4. **Added troubleshooting documentation**
   - Created `TROUBLESHOOTING_SELENIUM.md` with comprehensive guide
   - Diagnostic script to test Selenium setup
   - Manual workaround if automation fails

**Recommendation:** Don't use `--selenium` flag unless the default requests mode fails. The requests mode is faster and doesn't have timeout issues.

---

### Version 2.1 (February 6, 2025) - SOFR and Directory Fixes

### 1. Fixed SOFR Rate Extraction Bug ✓

**Problem:** The script was incorrectly extracting the 12-month SOFR rate instead of the 1-month SOFR rate.

**Root Cause:** The original pattern matching logic was too broad:
```python
if '1' in tenor and 'month' in tenor.lower():
    sofr_rates['1M'] = self._clean_rate(rate)
```

This matched both "1 month" AND "12 months" because the string "12 months" contains the character "1".

**Solution:** Made the pattern matching more specific:
```python
if ('1 month' in tenor or '1-month' in tenor or '1month' in tenor) and '12' not in tenor:
    sofr_rates['1M'] = self._clean_rate(rate)
```

Now the code:
1. Explicitly looks for "1 month" (with space), "1-month", or "1month"
2. Explicitly excludes any match containing "12"

**Verification:** Created `test_sofr_fix.py` which confirms:
- ✓ 1M SOFR: 3.67738% (correctly extracted)
- ✓ 3M SOFR: 3.67113% (correctly extracted)
- ✓ 6M SOFR: 3.62770% (correctly extracted)
- ✓ 12M SOFR: Correctly ignored

### 2. Changed Default Input Directory ✓

**Change:** Updated default master file location from `/swap_implied_input` to `../swap_implied_input`

**Rationale:** The new path places the input directory as a sibling folder in the parent directory, which is a more standard project structure:

```
parent_folder/
├── scripts/                    # Your scripts
│   ├── update_swap_implied_data.py
│   ├── run_swap_updater.sh
│   └── ...
└── swap_implied_input/        # Data files (sibling folder)
    ├── input_master_1m.xlsx
    ├── input_master_3m.xlsx
    └── input_master_6m.xlsx
```

**Files Updated:**
- `update_swap_implied_data.py` - Changed `DataUpdater` default from `/swap_implied_input` to `../swap_implied_input`
- `run_swap_updater.bat` - Updated directory check
- `run_swap_updater.sh` - Updated directory check
- `README_swap_implied.md` - Updated all path references
- `QUICKSTART.md` - Updated path references

### Testing

Run the included test to verify the SOFR fix:
```bash
python test_sofr_fix.py
```

Expected output:
```
✓✓✓ SUCCESS: 1M correctly identified (not confused with 12M) ✓✓✓
ALL TESTS PASSED ✓
```

### Migration Guide

If you were using the old default directory `/swap_implied_input`, you have two options:

**Option 1: Move your data to the new location (recommended)**
```bash
# Linux/Mac
mv /swap_implied_input ../swap_implied_input

# Windows
move \swap_implied_input ..\swap_implied_input
```

**Option 2: Use the --input-dir flag to specify your old location**
```bash
python update_swap_implied_data.py --input-dir /swap_implied_input
```

### Compatibility

- ✓ Backward compatible via `--input-dir` flag
- ✓ All existing functionality preserved
- ✓ No changes to file formats or column structure

### Summary

| Item | Before | After |
|------|--------|-------|
| 1M SOFR Extraction | ❌ Incorrectly picked up 12M | ✅ Correctly extracts 1M |
| Default Directory | `/swap_implied_input` | `../swap_implied_input` |
| Pattern Matching | Broad (`'1' in tenor`) | Specific (`'1 month' in tenor and '12' not in tenor`) |

---

**Version:** 2.2  
**Date:** February 6, 2025  
**Status:** Tested and verified
