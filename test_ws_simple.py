#!/usr/bin/env python3
"""Simple WebSocket test - checking connection only."""
import asyncio
import json
import websockets


async def test_ping():
    """Test WebSocket with ping/pong."""
    uri = "ws://localhost:8500/ws/stream"
    
    print(f"Connecting to {uri}...")
    
    async with websockets.connect(uri) as ws:
        # Wait for connection message
        msg = await ws.recv()
        event = json.loads(msg)
        print(f"Connected: {event}")
        
        # Send ping
        await ws.send(json.dumps({"type": "ping", "payload": {}}))
        
        # Wait for pong
        msg = await ws.recv()
        event = json.loads(msg)
        print(f"Received: {event}")
        
        print("✅ WebSocket working!")


if __name__ == "__main__":
    asyncio.run(test_ping())
