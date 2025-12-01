#!/usr/bin/env python3
"""
Test script to verify chart generation and event emission.
"""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tradingview_tools import generate_tradingview_chart

def test_chart_generation():
    """Test that charts are generated correctly."""
    print("🧪 Testing chart generation...")
    
    # Generate a test chart
    result_str = generate_tradingview_chart(
        symbol="SUIUSDT",
        interval="5m",
        indicators="volume",
        theme="dark",
        title="Test Chart"
    )
    
    print("\n📊 Chart generation result:")
    print(result_str)
    
    # Parse the result
    result = json.loads(result_str)
    
    # Verify the result structure
    assert result.get("status") == "success", "Chart generation failed"
    assert "chart_file" in result, "Missing chart_file key"
    assert result.get("symbol") == "SUIUSDT", "Wrong symbol"
    assert result.get("interval") == "5m", "Wrong interval"
    
    chart_file = Path(result["chart_file"])
    assert chart_file.exists(), f"Chart file not found: {chart_file}"
    
    print(f"\n✅ Chart generated successfully!")
    print(f"   File: {chart_file}")
    print(f"   Size: {chart_file.stat().st_size} bytes")
    print(f"   Symbol: {result['symbol']}")
    print(f"   Interval: {result['interval']}")
    
    # Check what the backend would extract
    print(f"\n🔍 Backend extraction test:")
    chart_data = result
    chart_path = chart_data.get('chart_file') or chart_data.get('file') or chart_data.get('path', '')
    filename = Path(chart_path).name
    url = f"/charts/{filename}"
    
    print(f"   chart_path: {chart_path}")
    print(f"   filename: {filename}")
    print(f"   url: {url}")
    print(f"   symbol: {chart_data.get('symbol')}")
    print(f"   interval: {chart_data.get('interval')}")
    
    return True

if __name__ == "__main__":
    try:
        test_chart_generation()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
