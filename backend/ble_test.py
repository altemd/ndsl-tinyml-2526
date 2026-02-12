"""
Minimal BLE Test - Python (bleak)
Scans for the Arduino, connects, and prints notifications.
"""
import asyncio
from bleak import BleakScanner, BleakClient

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdefa"
CHAR_UUID = "12345678-1234-5678-1234-56789abcdef7"

def notification_handler(sender, data):
    msg = data.decode("utf-8")
    print(f"  << Received: {msg}")

async def main():
    print("="*50)
    print("  BLE Connection Test")
    print("="*50)
    
    # Step 1: Scan
    print("\n[1] Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=5)
    
    target = None
    for d in devices:
        name = d.name or "Unknown"
        print(f"    Found: {name} ({d.address})")
        if "Nano33BLE" in name:
            target = d
    
    if not target:
        print("\n[!] Arduino not found. Make sure it's powered on.")
        return
    
    print(f"\n[2] Connecting to {target.name} ({target.address})...")
    
    async with BleakClient(target.address) as client:
        print(f"    Connected: {client.is_connected}")
        
        # List services
        print("\n[3] Services found:")
        for service in client.services:
            print(f"    Service: {service.uuid}")
            for char in service.characteristics:
                print(f"      Char: {char.uuid} [{', '.join(char.properties)}]")
        
        # Subscribe to notifications
        print(f"\n[4] Subscribing to {CHAR_UUID}...")
        await client.start_notify(CHAR_UUID, notification_handler)
        
        print("    Listening for 10 seconds...\n")
        await asyncio.sleep(10)
        
        await client.stop_notify(CHAR_UUID)
    
    print("\n[Done] Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
