#!/usr/bin/env python3
"""
Forward Points Extraction - With Manual Fallback
Provides multiple methods to get forward points when automated scraping fails
"""

import sys

def manual_forward_points_input():
    """
    Manual input mode for forward points
    Use this when automated extraction fails
    """
    print("\n" + "=" * 70)
    print("MANUAL FORWARD POINTS INPUT MODE")
    print("=" * 70)
    print("\n📋 Please open one of these sources in your browser:")
    print("   1. https://www.investing.com/currencies/usd-sgd-forward-rates")
    print("   2. Your broker platform (e.g., OCBC, DBS, SAXO)")
    print("   3. Bloomberg Terminal (if you have access)")
    print("\n")
    
    print("Enter the BID and ASK values for each tenor:")
    print("(Script will calculate mid rates automatically)\n")
    
    try:
        # 1-month
        print("1-MONTH FORWARD:")
        fp_1m_bid = float(input("  Bid: "))
        fp_1m_ask = float(input("  Ask: "))
        
        # 3-month
        print("\n3-MONTH FORWARD:")
        fp_3m_bid = float(input("  Bid: "))
        fp_3m_ask = float(input("  Ask: "))
        
        # 6-month
        print("\n6-MONTH FORWARD:")
        fp_6m_bid = float(input("  Bid: "))
        fp_6m_ask = float(input("  Ask: "))
        
        # Calculate mid rates
        forward_points = {
            '1M': round((fp_1m_bid + fp_1m_ask) / 2, 4),
            '3M': round((fp_3m_bid + fp_3m_ask) / 2, 4),
            '6M': round((fp_6m_bid + fp_6m_ask) / 2, 4)
        }
        
        print("\n" + "=" * 70)
        print("CALCULATED MID RATES:")
        print("=" * 70)
        for period, value in forward_points.items():
            print(f"  {period}: {value} pips")
        print("=" * 70)
        
        confirm = input("\nAre these values correct? (y/n): ")
        if confirm.lower() != 'y':
            print("Cancelled. Please run again.")
            return None
        
        return forward_points
        
    except ValueError as e:
        print(f"\n✗ Error: Invalid input. Please enter numeric values only.")
        return None
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return None


def calculate_forward_points_from_rates(spot_rate, sofr_rates, sora_rates=None):
    """
    Calculate forward points using interest rate parity
    
    Args:
        spot_rate: Current USD/SGD spot rate
        sofr_rates: Dict with '1M', '3M', '6M' SOFR rates (in %)
        sora_rates: Dict with '1M', '3M', '6M' SORA rates (in %), optional
    
    Returns:
        Dict with '1M', '3M', '6M' forward points
    """
    # If SORA rates not provided, estimate as SOFR - 0.5%
    if sora_rates is None:
        print("⚠ SORA rates not provided. Using SOFR - 0.5% as estimate.")
        sora_rates = {
            '1M': sofr_rates['1M'] - 0.5,
            '3M': sofr_rates['3M'] - 0.5,
            '6M': sofr_rates['6M'] - 0.5
        }
    
    # Convert percentages to decimal
    sofr_decimal = {k: v / 100 for k, v in sofr_rates.items()}
    sora_decimal = {k: v / 100 for k, v in sora_rates.items()}
    
    # Days for each tenor
    days_map = {'1M': 30, '3M': 90, '6M': 180}
    
    forward_points = {}
    
    for period, days in days_map.items():
        sofr = sofr_decimal[period]
        sora = sora_decimal[period]
        
        # Interest rate parity formula
        forward_rate = spot_rate * (
            (1 + sofr * days / 360) / 
            (1 + sora * days / 360)
        )
        
        # Convert to pips (multiply by 10000)
        fp = (forward_rate - spot_rate) * 10000
        forward_points[period] = round(fp, 4)
    
    print("\n✓ Forward points calculated from interest rate parity:")
    for period, value in forward_points.items():
        print(f"  {period}: {value} pips (estimated)")
    
    return forward_points


def main():
    """Interactive CLI for getting forward points"""
    print("=" * 70)
    print("USD/SGD FORWARD POINTS - INTERACTIVE INPUT")
    print("=" * 70)
    print("\nThis tool helps you input forward points data manually.")
    print("Use this when automated extraction from websites fails.\n")
    
    print("Choose an option:")
    print("  1. Manual input (from browser/broker)")
    print("  2. Calculate from SOFR + SORA rates")
    print("  3. Exit")
    
    choice = input("\nYour choice (1-3): ")
    
    if choice == '1':
        forward_points = manual_forward_points_input()
        if forward_points:
            print("\n✓ Forward points ready to use:")
            print(forward_points)
            
            # Save to file option
            save = input("\nSave to file? (y/n): ")
            if save.lower() == 'y':
                import json
                from datetime import datetime
                
                filename = f"forward_points_{datetime.now().strftime('%Y%m%d')}.json"
                with open(filename, 'w') as f:
                    json.dump({
                        'date': datetime.now().isoformat(),
                        'forward_points': forward_points
                    }, f, indent=2)
                print(f"✓ Saved to {filename}")
    
    elif choice == '2':
        print("\nCalculating from interest rates...")
        print("\nEnter SOFR rates (in %, e.g., 4.50 for 4.50%):")
        try:
            sofr_1m = float(input("  1M SOFR: "))
            sofr_3m = float(input("  3M SOFR: "))
            sofr_6m = float(input("  6M SOFR: "))
            
            spot = float(input("\nEnter USD/SGD spot rate (e.g., 1.3450): "))
            
            print("\nDo you have SORA rates? (y/n): ")
            has_sora = input().lower() == 'y'
            
            sora_rates = None
            if has_sora:
                print("\nEnter SORA rates (in %):")
                sora_1m = float(input("  1M SORA: "))
                sora_3m = float(input("  3M SORA: "))
                sora_6m = float(input("  6M SORA: "))
                sora_rates = {'1M': sora_1m, '3M': sora_3m, '6M': sora_6m}
            
            sofr_rates = {'1M': sofr_1m, '3M': sofr_3m, '6M': sofr_6m}
            
            forward_points = calculate_forward_points_from_rates(spot, sofr_rates, sora_rates)
            
            print("\n✓ Calculated forward points:")
            print(forward_points)
            
        except ValueError:
            print("\n✗ Invalid input. Please enter numeric values.")
    
    elif choice == '3':
        print("Exiting...")
        sys.exit(0)
    
    else:
        print("Invalid choice.")
        sys.exit(1)


if __name__ == "__main__":
    main()
