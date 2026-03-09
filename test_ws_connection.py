import asyncio
import websockets
import json

async def test_connect():
    uri = "ws://127.0.0.1:8765"
    try:
        # Removing the invalid 'timeout' argument
        async with websockets.connect(uri) as websocket:
            print("Successfully connected to Progeny WebSocket server!")
            # Wait for the init message
            greeting = await websocket.recv()
            print(f"Received from server: {greeting}")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    asyncio.run(test_connect())
