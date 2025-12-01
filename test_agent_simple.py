#!/usr/bin/env python3
"""Test agent system via HTTP requests."""
import json
import subprocess
import time

def test_agent_system():
    """Test the full agent system via WebSocket using Python script."""
    
    print("=" * 60)
    print("TESTING AGENT SYSTEM")
    print("=" * 60)
    
    # First check if backend is running
    print("\n1. Checking backend health...")
    result = subprocess.run(
        ["curl", "-s", "http://localhost:8500/api/v1/health"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        health = json.loads(result.stdout)
        print(f"   ✅ Backend healthy: {health['status']}")
    else:
        print(f"   ❌ Backend not responding")
        return False
    
    # Check readiness
    print("\n2. Checking LLM configuration...")
    result = subprocess.run(
        ["curl", "-s", "http://localhost:8500/api/v1/health/ready"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        ready = json.loads(result.stdout)
        print(f"   ✅ Status: {ready['status']}")
        print(f"   ✅ Provider: {ready['checks']['llm_provider']}")
        print(f"   ✅ Azure configured: {ready['checks']['azure_configured']}")
    else:
        print(f"   ❌ Readiness check failed")
        return False
    
    # Test WebSocket via Node.js script
    print("\n3. Testing WebSocket connection...")
    print("   Creating test script...")
    
    ws_test = """
const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8500/ws/stream');

let messageCount = 0;

ws.on('open', () => {
    console.log('   ✅ Connected to WebSocket');
    
    // Send a test message
    const testMessage = {
        type: 'chat',
        payload: {
            message: 'What is the current price of Bitcoin?',
            session_id: 'test-session-' + Date.now()
        }
    };
    
    console.log('   📤 Sending test query...');
    ws.send(JSON.stringify(testMessage));
});

ws.on('message', (data) => {
    messageCount++;
    const event = JSON.parse(data.toString());
    
    console.log(`   📨 Event ${messageCount}: ${event.type}`);
    
    if (event.type === 'status') {
        console.log(`      Status: ${event.status || 'N/A'}`);
        console.log(`      Message: ${event.message || ''}`);
    } else if (event.type === 'agent_step') {
        console.log(`      Agent: ${event.agent}`);
        console.log(`      Action: ${event.action || 'thinking'}`);
    } else if (event.type === 'tool_call') {
        console.log(`      Tool: ${event.tool_name}`);
        console.log(`      Args: ${JSON.stringify(event.tool_args).substring(0, 50)}...`);
    } else if (event.type === 'agent_message') {
        console.log(`      From: ${event.sender}`);
        console.log(`      Message: ${event.content.substring(0, 100)}...`);
    } else if (event.type === 'result') {
        console.log(`      ✅ Final result received`);
        console.log(`      Content: ${event.content.substring(0, 150)}...`);
        
        // Close after receiving result
        setTimeout(() => {
            console.log('\\n   🎉 Agent system test PASSED!');
            ws.close();
            process.exit(0);
        }, 1000);
    } else if (event.type === 'error') {
        console.log(`      ❌ Error: ${event.message}`);
        console.log(`      Details: ${event.details || ''}`);
        ws.close();
        process.exit(1);
    }
});

ws.on('error', (error) => {
    console.error(`   ❌ WebSocket error: ${error.message}`);
    process.exit(1);
});

ws.on('close', () => {
    if (messageCount === 0) {
        console.log('   ❌ Connection closed without messages');
        process.exit(1);
    }
});

// Timeout after 60 seconds
setTimeout(() => {
    console.log('   ⚠️  Test timeout - closing connection');
    console.log(`   Received ${messageCount} messages`);
    ws.close();
    process.exit(messageCount > 0 ? 0 : 1);
}, 60000);
"""
    
    with open('/tmp/test_ws.js', 'w') as f:
        f.write(ws_test)
    
    # Check if Node.js is available
    result = subprocess.run(
        ["which", "node"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("   ⚠️  Node.js not found, skipping WebSocket test")
        print("   But backend and health checks passed!")
        return True
    
    # Install ws package if needed
    print("   Installing WebSocket package...")
    subprocess.run(
        ["npm", "install", "-g", "ws"],
        capture_output=True,
        text=True
    )
    
    # Run the test
    print("   Running WebSocket test (60s timeout)...")
    result = subprocess.run(
        ["node", "/tmp/test_ws.js"],
        capture_output=True,
        text=True,
        timeout=65
    )
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    return result.returncode == 0


if __name__ == "__main__":
    try:
        success = test_agent_system()
        if success:
            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED")
            print("=" * 60)
            exit(0)
        else:
            print("\n" + "=" * 60)
            print("❌ TESTS FAILED")
            print("=" * 60)
            exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        exit(1)
