@echo off
REM USD/SGD Forward Points Extractor - Windows Batch Script
echo.
echo ============================================================
echo USD/SGD Forward Points Extractor
echo ============================================================
echo.

REM Try requests method first
python extract_forward_points_selenium.py

REM Check if successful
if %errorlevel% neq 0 (
    echo.
    echo First attempt failed. Trying Selenium method...
    python extract_forward_points_selenium.py --selenium
)

echo.
echo Press any key to exit...
pause > nul
