#!/usr/bin/env python3
"""
Quick test of live agent streaming with Azure OpenAI.
"""
import asyncio
import websockets
import json

async def test_agent_chat():
    uri = "ws://localhost:8500/ws/stream"
    
    print("🔌 Connecting to WebSocket...")
    async with websockets.connect(uri) as websocket:
        print("✅ Connected!")
        
        # Send a simple crypto query
        message = {
            "type": "chat",
            "message": "What is the current price of Bitcoin?"
        }
        
        print(f"\n📤 Sending: {message['message']}")
        await websocket.send(json.dumps(message))
        
        print("\n📥 Receiving events...")
        print("-" * 60)
        
        event_count = 0
        try:
            async for msg in websocket:
                event_count += 1
                data = json.loads(msg)
                event_type = data.get("type", "unknown")
                
                if event_type == "status":
                    status = data.get("status")
                    print(f"[{event_count:02d}] STATUS: {status}")
                
                elif event_type == "agent_step":
                    agent = data.get("agent", "")
                    emoji = data.get("emoji", "")
                    message = data.get("message", "")
                    print(f"[{event_count:02d}] AGENT: {emoji} {agent}")
                    print(f"       {message[:80]}...")
                
                elif event_type == "tool_call":
                    tool = data.get("tool_name", "")
                    print(f"[{event_count:02d}] TOOL: {tool}")
                
                elif event_type == "tool_result":
                    result = data.get("result", "")
                    print(f"[{event_count:02d}] RESULT: {result[:80]}...")
                
                elif event_type == "progress":
                    turn = data.get("turn_number", 0)
                    max_turns = data.get("max_turns", 0)
                    print(f"[{event_count:02d}] PROGRESS: Turn {turn}/{max_turns}")
                
                elif event_type == "result":
                    result = data.get("result", "")
                    format_type = data.get("format", "")
                    print(f"[{event_count:02d}] RESULT ({format_type}): {result[:100]}...")
                    print("\n✅ Conversation complete!")
                    break
                
                elif event_type == "error":
                    error = data.get("error", "")
                    print(f"[{event_count:02d}] ❌ ERROR: {error}")
                    break
                
                # Safety: stop after 50 events
                if event_count >= 50:
                    print("\n⚠️  Reached 50 events, stopping...")
                    break
                    
        except websockets.exceptions.ConnectionClosed:
            print("\n🔌 Connection closed")
        
        print("-" * 60)
        print(f"\n📊 Total events received: {event_count}")

if __name__ == "__main__":
    print("=" * 60)
    print("LIVE AGENT TEST - Phase 3 Verification")
    print("=" * 60)
    asyncio.run(test_agent_chat())
