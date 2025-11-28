#!/usr/bin/env python3
"""
Demo script to test crypto analysis platform with AI agents
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from main import CryptoAnalysisPlatform
from config import AppConfig

async def demo_crypto_analysis():
    """Run a quick demo of the crypto analysis platform."""
    print("\n" + "="*60)
    print("🪙 Crypto Analysis Platform - Demo")
    print("="*60 + "\n")
    
    # Load configuration
    config = AppConfig.from_env()
    app = CryptoAnalysisPlatform(config)
    
    # Display banner
    app.display_banner()
    
    # Test task
    task = "Get the current price of Bitcoin in USD"
    
    print(f"\n{'='*60}")
    print(f"📝 Demo Task: {task}")
    print(f"{'='*60}\n")
    
    try:
        # Run the task
        result = await app.run_task(task, save_output=True)
        print(f"\n✅ Task completed successfully!")
        print(f"\nResult preview: {str(result)[:300]}...")
        
    except Exception as e:
        print(f"\n❌ Error during task execution: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n{'='*60}")
    print("🎉 Demo completed!")
    print("="*60)
    print("\nThe platform is ready. To use interactively:")
    print("  source .venv/bin/activate && python src/main.py")
    print("\nOr run advanced mode:")
    print("  source .venv/bin/activate && python examples/crypto_analysis.py --mode interactive")
    
    return True

if __name__ == "__main__":
    result = asyncio.run(demo_crypto_analysis())
    sys.exit(0 if result else 1)
