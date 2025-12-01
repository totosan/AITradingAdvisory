#!/usr/bin/env python3
"""
Quick test of frontend and backend connectivity.
"""
import requests
import json


def test_backend():
    """Test backend API."""
    print("🔍 Testing Backend API...")
    try:
        resp = requests.get("http://localhost:8500/api/v1/health", timeout=5)
        if resp.status_code == 200:
            print(f"   ✅ Backend: {resp.json()['status']}")
            return True
        else:
            print(f"   ❌ Backend: Status {resp.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Backend: {e}")
        return False


def test_frontend():
    """Test frontend is serving."""
    print("🔍 Testing Frontend...")
    try:
        resp = requests.get("http://localhost:5173/", timeout=5)
        if resp.status_code == 200 and 'root' in resp.text:
            print(f"   ✅ Frontend: Serving React app")
            return True
        else:
            print(f"   ❌ Frontend: Status {resp.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Frontend: {e}")
        return False


def test_websocket_endpoint():
    """Test WebSocket endpoint is available."""
    print("🔍 Testing WebSocket endpoint...")
    try:
        resp = requests.get("http://localhost:8500/ws/status", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ WebSocket: {data['active_connections']} connections")
            return True
        else:
            print(f"   ❌ WebSocket: Status {resp.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ WebSocket: {e}")
        return False


def main():
    print()
    print("=" * 60)
    print("🧪 Full Stack Test - Backend + Frontend")
    print("=" * 60)
    print()
    
    backend_ok = test_backend()
    frontend_ok = test_frontend()
    ws_ok = test_websocket_endpoint()
    
    print()
    print("=" * 60)
    
    if backend_ok and frontend_ok and ws_ok:
        print("✅ FULL STACK OPERATIONAL")
        print()
        print("📱 Access URLs from your HOST browser:")
        print("   Frontend: http://localhost:5173")
        print("   Backend:  http://localhost:8500/docs")
        print()
        print("🎉 Open http://localhost:5173 in your browser to use the app!")
    else:
        print("❌ ISSUES DETECTED")
        print()
        if not backend_ok:
            print("   Backend not responding - run: ./start.sh")
        if not frontend_ok:
            print("   Frontend not responding - run: cd frontend && npm run dev")
        if not ws_ok:
            print("   WebSocket not available - check backend")
    
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
