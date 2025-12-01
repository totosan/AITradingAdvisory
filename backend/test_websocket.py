#!/usr/bin/env python3
"""
Test WebSocket connection with agent integration.
"""
import asyncio
import json
import sys
from datetime import datetime
import websockets


async def test_websocket():
    """Test WebSocket connection and send a simple query."""
    uri = "ws://localhost:8500/ws/stream"
    
    print(f"🔌 Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # Wait for connection confirmation
            msg = await websocket.recv()
            event = json.loads(msg)
            print(f"📨 {event.get('type')}: {event.get('message', '')}")
            
            # Send a simple query
            query = {
                "type": "chat",
                "payload": {
                    "message": "What is the current price of Bitcoin?"
                }
            }
            
            print(f"\n📤 Sending query: {query['payload']['message']}")
            await websocket.send(json.dumps(query))
            
            # Receive and display events
            event_count = 0
            max_events = 50  # Limit for testing
            
            while event_count < max_events:
                try:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    event = json.loads(msg)
                    event_count += 1
                    
                    event_type = event.get('type', 'unknown')
                    timestamp = event.get('timestamp', datetime.now().isoformat())
                    
                    # Display based on event type
                    if event_type == 'status':
                        status = event.get('status', '')
                        message = event.get('message', '')
                        print(f"📊 [{status.upper()}] {message}")
                        
                        # Stop if idle or completed
                        if status in ['idle', 'completed']:
                            print("\n✅ Query completed!")
                            break
                    
                    elif event_type == 'agent_step':
                        agent = event.get('agent', '')
                        emoji = event.get('emoji', '🤖')
                        message = event.get('message', '')
                        print(f"\n{emoji} {agent}: {message}")
                    
                    elif event_type == 'tool_call':
                        agent = event.get('agent', '')
                        tool_name = event.get('tool_name', '')
                        print(f"  🔧 Calling {tool_name}")
                    
                    elif event_type == 'tool_result':
                        tool_name = event.get('tool_name', '')
                        preview = event.get('result_preview', '')
                        if preview:
                            print(f"  ✔️ {tool_name}: {preview[:100]}...")
                    
                    elif event_type == 'progress':
                        current = event.get('current_turn', 0)
                        max_turns = event.get('max_turns', 10)
                        percentage = event.get('percentage', 0)
                        print(f"  📈 Progress: {current}/{max_turns} ({percentage:.0f}%)")
                    
                    elif event_type == 'result':
                        content = event.get('content', '')
                        agents_used = event.get('agents_used', [])
                        print(f"\n📄 FINAL RESULT:")
                        print(f"   Agents: {', '.join(agents_used)}")
                        print(f"   Content length: {len(content)} chars")
                        print(f"   Preview: {content[:200]}...")
                    
                    elif event_type == 'chart_generated':
                        symbol = event.get('symbol', '')
                        url = event.get('url', '')
                        print(f"  📊 Chart generated for {symbol}: {url}")
                    
                    elif event_type == 'error':
                        message = event.get('message', '')
                        details = event.get('details', '')
                        print(f"❌ ERROR: {message}")
                        if details:
                            print(f"   Details: {details}")
                        break
                    
                    elif event_type == 'pong':
                        print("  🏓 Pong received")
                    
                    else:
                        print(f"  ❓ Unknown event: {event_type}")
                
                except asyncio.TimeoutError:
                    print("⏱️ Timeout waiting for events")
                    break
            
            if event_count >= max_events:
                print(f"\n⚠️ Reached max events limit ({max_events})")
            
            print(f"\n📊 Total events received: {event_count}")
    
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("🧪 WebSocket Agent Integration Test")
    print("=" * 50)
    asyncio.run(test_websocket())
