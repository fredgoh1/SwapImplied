#!/bin/bash
# USD/SGD Forward Points Extractor - Linux/Mac Shell Script

echo ""
echo "============================================================"
echo "USD/SGD Forward Points Extractor"
echo "============================================================"
echo ""

# Try requests method first
python3 extract_forward_points_selenium.py

# Check if successful
if [ $? -ne 0 ]; then
    echo ""
    echo "First attempt failed. Trying Selenium method..."
    python3 extract_forward_points_selenium.py --selenium
fi

echo ""
echo "Press Enter to exit..."
read
