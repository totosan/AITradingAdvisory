#!/usr/bin/env python3
"""
Phase 7 Learning System - Interactive Test Script

Run this script to test the Learning System features interactively.
Requires backend running on localhost:8500

Usage:
    python tests/test_learning_system_live.py
"""
import asyncio
import json
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/workspaces/AITradingAdvisory')

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()


def print_header(title: str):
    console.print(Panel(f"[bold blue]{title}[/]", expand=False))


def print_success(msg: str):
    console.print(f"[green]✅ {msg}[/]")


def print_error(msg: str):
    console.print(f"[red]❌ {msg}[/]")


def print_info(msg: str):
    console.print(f"[yellow]ℹ️  {msg}[/]")


# =============================================================================
# Test 1: Strategy Classification
# =============================================================================
def test_strategy_classification():
    """Test the IntentRouter strategy classification."""
    print_header("Test 1: Strategy Classification")
    
    from src.intent_router import IntentRouter, StrategyType
    
    router = IntentRouter()
    
    test_cases = [
        ("BTC seitwärts in Range 94k-98k, Support kaufen", StrategyType.RANGE),
        ("ETH Breakout über 4000, Pullback abwarten", StrategyType.BREAKOUT_PULLBACK),
        ("SOL im Aufwärtstrend, EMA Cross bullish", StrategyType.TREND_FOLLOWING),
        ("RSI Divergenz bei BTC - Umkehr erwartet", StrategyType.REVERSAL),
        ("Schneller Scalp auf 5m Chart", StrategyType.SCALPING),
        ("Was ist der BTC Preis?", StrategyType.UNKNOWN),
    ]
    
    table = Table(title="Strategy Classification Results")
    table.add_column("Query", style="cyan", max_width=40)
    table.add_column("Expected", style="yellow")
    table.add_column("Got", style="green")
    table.add_column("Confidence", style="magenta")
    table.add_column("Status")
    
    all_passed = True
    for query, expected in test_cases:
        strategy, confidence = router.classify_strategy(query)
        passed = strategy == expected
        if not passed:
            all_passed = False
        
        table.add_row(
            query[:40] + "..." if len(query) > 40 else query,
            expected.value,
            strategy.value,
            f"{confidence:.2f}",
            "✅" if passed else "❌"
        )
    
    console.print(table)
    
    if all_passed:
        print_success("All strategy classifications passed!")
    else:
        print_error("Some classifications failed")
    
    return all_passed


# =============================================================================
# Test 2: Database Tables
# =============================================================================
async def test_database_tables():
    """Test that all Phase 7 tables exist."""
    print_header("Test 2: Database Tables")
    
    try:
        # This would require the backend imports - skip if not available
        print_info("Checking tables via Docker exec...")
        import subprocess
        result = subprocess.run(
            [
                "docker", "exec", "magentic-backend-dev", "python3", "-c",
                """
from app.core.database import get_engine
import asyncio
async def check():
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.run_sync(lambda c: c.execute(
            __import__('sqlalchemy').text('SELECT name FROM sqlite_master WHERE type=\"table\"')
        ).fetchall())
        print(','.join([r[0] for r in result]))
asyncio.run(check())
"""
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_error(f"Docker exec failed: {result.stderr}")
            return False
        
        tables = result.stdout.strip().split(',')
        
        required_tables = [
            'users', 'conversations', 'messages',
            'predictions', 'prediction_evaluations', 'global_insights'
        ]
        
        table = Table(title="Database Tables")
        table.add_column("Table", style="cyan")
        table.add_column("Status")
        
        all_found = True
        for req in required_tables:
            found = req in tables
            if not found:
                all_found = False
            table.add_row(req, "✅ Found" if found else "❌ Missing")
        
        console.print(table)
        
        if all_found:
            print_success("All required tables exist!")
        else:
            print_error("Some tables are missing")
        
        return all_found
        
    except Exception as e:
        print_error(f"Error checking tables: {e}")
        return False


# =============================================================================
# Test 3: API Endpoints
# =============================================================================
async def test_api_endpoints():
    """Test that all Phase 7 API endpoints are registered."""
    print_header("Test 3: API Endpoints")
    
    try:
        import subprocess
        result = subprocess.run(
            [
                "docker", "exec", "magentic-backend-dev",
                "curl", "-s", "http://localhost:8500/openapi.json"
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_error(f"Curl failed: {result.stderr}")
            return False
        
        openapi = json.loads(result.stdout)
        paths = list(openapi.get('paths', {}).keys())
        
        required_endpoints = [
            '/api/v1/predictions/',
            '/api/v1/predictions/stats',
            '/api/v1/predictions/{prediction_id}',
            '/api/v1/predictions/{prediction_id}/feedback',
            '/api/v1/predictions/insights/global',
        ]
        
        table = Table(title="API Endpoints")
        table.add_column("Endpoint", style="cyan")
        table.add_column("Status")
        
        all_found = True
        for endpoint in required_endpoints:
            found = endpoint in paths
            if not found:
                all_found = False
            table.add_row(endpoint, "✅ Found" if found else "❌ Missing")
        
        console.print(table)
        
        if all_found:
            print_success("All API endpoints registered!")
        else:
            print_error("Some endpoints are missing")
        
        return all_found
        
    except Exception as e:
        print_error(f"Error checking endpoints: {e}")
        return False


# =============================================================================
# Test 4: FeedbackContext Generation
# =============================================================================
async def test_feedback_context():
    """Test FeedbackContext generation."""
    print_header("Test 4: Feedback Context Generation")
    
    try:
        import subprocess
        result = subprocess.run(
            [
                "docker", "exec", "magentic-backend-dev", "python3", "-c",
                """
import asyncio
from app.core.database import get_db
from app.services.feedback_context import FeedbackContextService
from app.models.database import StrategyType

async def test():
    async for session in get_db():
        service = FeedbackContextService(session, 'test-user')
        context = await service.get_strategy_context(StrategyType.RANGE)
        word_count = len(context.split())
        print(f"WORDS:{word_count}")
        print(f"CONTEXT:{context[:200]}")
        break

asyncio.run(test())
"""
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_error(f"Exec failed: {result.stderr}")
            return False
        
        lines = result.stdout.strip().split('\n')
        word_count = 0
        context_preview = ""
        
        for line in lines:
            if line.startswith("WORDS:"):
                word_count = int(line.split(":")[1])
            if line.startswith("CONTEXT:"):
                context_preview = line.split(":", 1)[1]
        
        console.print(Panel(
            f"[cyan]Word count:[/] {word_count}\n"
            f"[cyan]Token limit:[/] ~200 tokens (~60 words)\n"
            f"[cyan]Preview:[/] {context_preview}...",
            title="Feedback Context"
        ))
        
        if word_count < 100:
            print_success(f"Context is within token budget ({word_count} words)")
            return True
        else:
            print_error(f"Context may exceed token budget ({word_count} words)")
            return False
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False


# =============================================================================
# Test 5: Create Test Prediction
# =============================================================================
async def test_create_prediction():
    """Create a test prediction via repository."""
    print_header("Test 5: Create Test Prediction")
    
    try:
        import subprocess
        result = subprocess.run(
            [
                "docker", "exec", "magentic-backend-dev", "python3", "-c",
                """
import asyncio
import json
from app.core.database import get_db
from app.core.repositories import PredictionRepository
from app.models.database import StrategyType

async def create():
    async for session in get_db():
        repo = PredictionRepository(session)
        
        prediction = await repo.create(
            user_id='test-user-live',
            conversation_id='test-conv-live',
            strategy_type=StrategyType.RANGE,
            symbol='BTCUSDT',
            direction='long',
            entry_price=95000.0,
            stop_loss=94000.0,
            take_profit_json=json.dumps([96000.0, 97000.0]),
            timeframe='4h',
            confidence='high',
            signals_json=json.dumps(['RSI oversold', 'Support bounce']),
            analysis_summary='Test prediction from live test script'
        )
        await session.commit()
        
        print(f"ID:{prediction.id}")
        print(f"STRATEGY:{prediction.strategy_type.value}")
        print(f"STATUS:{prediction.status.value}")
        break

asyncio.run(create())
"""
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_error(f"Exec failed: {result.stderr}")
            return False
        
        lines = result.stdout.strip().split('\n')
        pred_id = ""
        strategy = ""
        status = ""
        
        for line in lines:
            if line.startswith("ID:"):
                pred_id = line.split(":")[1]
            if line.startswith("STRATEGY:"):
                strategy = line.split(":")[1]
            if line.startswith("STATUS:"):
                status = line.split(":")[1]
        
        console.print(Panel(
            f"[green]Prediction created successfully![/]\n\n"
            f"[cyan]ID:[/] {pred_id}\n"
            f"[cyan]Strategy:[/] {strategy}\n"
            f"[cyan]Status:[/] {status}",
            title="New Prediction"
        ))
        
        print_success("Prediction created and persisted!")
        return True
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False


# =============================================================================
# Main
# =============================================================================
async def main():
    console.print("\n")
    console.print(Panel.fit(
        "[bold green]Phase 7: Learning System - Live Tests[/]\n"
        "Testing strategy classification, database, API, and predictions",
        border_style="green"
    ))
    console.print("\n")
    
    results = {
        "Strategy Classification": test_strategy_classification(),
        "Database Tables": await test_database_tables(),
        "API Endpoints": await test_api_endpoints(),
        "Feedback Context": await test_feedback_context(),
        "Create Prediction": await test_create_prediction(),
    }
    
    console.print("\n")
    print_header("Summary")
    
    table = Table(title="Test Results")
    table.add_column("Test", style="cyan")
    table.add_column("Result")
    
    all_passed = True
    for test_name, passed in results.items():
        if not passed:
            all_passed = False
        table.add_row(test_name, "✅ PASSED" if passed else "❌ FAILED")
    
    console.print(table)
    
    if all_passed:
        console.print("\n[bold green]🎉 All tests passed! Phase 7 is working correctly.[/]\n")
    else:
        console.print("\n[bold red]⚠️  Some tests failed. Check the output above.[/]\n")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
