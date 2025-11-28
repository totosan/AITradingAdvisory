#!/usr/bin/env python3
"""
Quick test script for crypto analysis platform
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from crypto_tools import get_crypto_price, get_historical_data
from crypto_charts import create_crypto_chart

async def test_crypto_platform():
    print("🧪 Testing Crypto Analysis Platform\n")
    
    # Test 1: Get Bitcoin price
    print("1️⃣ Testing price fetch...")
    try:
        price_data = get_crypto_price("bitcoin")
        print(f"✅ Bitcoin price fetched successfully")
        print(f"   Preview: {price_data[:100]}...\n")
    except Exception as e:
        print(f"❌ Price fetch failed: {e}\n")
        return False
    
    # Test 2: Get historical data
    print("2️⃣ Testing historical data...")
    try:
        hist_data = get_historical_data("bitcoin", 7)
        print(f"✅ Historical data fetched successfully")
        print(f"   Preview: {hist_data[:150]}...\n")
    except Exception as e:
        print(f"❌ Historical data failed: {e}\n")
        return False
    
    # Test 3: Generate chart
    print("3️⃣ Testing chart generation...")
    try:
        chart_result = create_crypto_chart("bitcoin", 7, ['sma', 'rsi'])
        print(f"✅ Chart generated successfully")
        print(f"   Result: {chart_result[:200]}...\n")
    except Exception as e:
        print(f"❌ Chart generation failed: {e}\n")
        return False
    
    print("✅ All crypto tools working!\n")
    return True

if __name__ == "__main__":
    result = asyncio.run(test_crypto_platform())
    if result:
        print("🎉 Platform is ready for use!")
        print("\nTo start interactive mode, run:")
        print("  source .venv/bin/activate && python src/main.py")
    else:
        print("❌ Some tests failed. Check errors above.")
        sys.exit(1)
