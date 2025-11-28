"""Quick test to verify crypto_tools import works in code execution"""
from crypto_tools import get_crypto_price
import json

# Test the import
result = get_crypto_price("bitcoin")
data = json.loads(result)
print(f"✅ Successfully imported and used crypto_tools!")
print(f"Bitcoin price: ${data.get('price', 'N/A')}")
