
import asyncio
import logging
from bleak import BleakScanner, BleakClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# BLE UUIDs matching the Arduino sketch (main.cpp)
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdefa" 
CHARACTERISTIC_UUID_RX = "12345678-1234-5678-1234-56789abcdef7"  # Inference results

class BLEService:
    def __init__(self):
        self.client = None
        self.device = None
        self.connected = False
        self.callbacks = []

    async def scan_and_connect(self):
        print("[BLE] Scanning for Arduino Nano 33 BLE Sense...")
        try:
            devices = await BleakScanner.discover(timeout=5)
        except Exception as e:
            print(f"[BLE] ✗ Scan error: {e}")
            self._notify_all("SYSTEM: ARDUINO_SCAN_FAILED")
            return False
        
        target_device = None
        for d in devices:
            name = d.name or "Unknown"
            if "Nano33BLE" in name:
                target_device = d
                print(f"[BLE] Found: {name} ({d.address})")
                break
        
        if not target_device:
            print("[BLE] ✗ Arduino not found. Make sure it's powered on.")
            self._notify_all("SYSTEM: ARDUINO_SCAN_FAILED")
            return False

        self.device = target_device
        
        try:
            import traceback
            print(f"[BLE] Connecting to {target_device.name} ({target_device.address})...")
            self.client = BleakClient(target_device.address, timeout=20.0)
            await self.client.connect()
            self.connected = True
            print(f"[BLE] ✓ Connected!")
            self._notify_all("SYSTEM: ARDUINO_CONNECTED")
            
            # Subscribe to notifications
            await self.client.start_notify(CHARACTERISTIC_UUID_RX, self.notification_handler)
            print(f"[BLE] ✓ Subscribed to notifications")
            
            return True
        except Exception as e:
            print(f"[BLE] ✗ Connection failed: {type(e).__name__}: {e}")
            traceback.print_exc()
            self.connected = False
            self._notify_all("SYSTEM: ARDUINO_ERROR")
            return False

    async def disconnect(self):
        if self.client and self.connected:
            try:
                await self.client.stop_notify(CHARACTERISTIC_UUID_RX)
            except:
                pass
            await self.client.disconnect()
            self.connected = False
            print("[BLE] Disconnected")
            self._notify_all("SYSTEM: ARDUINO_DISCONNECTED")

    def _notify_all(self, msg):
        for callback in self.callbacks:
            asyncio.create_task(callback(msg))

    def notification_handler(self, sender, data):
        """Handle incoming data from Arduino"""
        msg = data.decode('utf-8').strip()
        print(f"[BLE] << {msg}")
        
        # Forward to all registered callbacks (WebSocket → frontend)
        for callback in self.callbacks:
            asyncio.create_task(callback(msg))

    def register_callback(self, callback):
        self.callbacks.append(callback)

    async def send_command(self, command: str):
        if self.connected and self.client:
            await self.client.write_gatt_char(CHARACTERISTIC_UUID_RX, command.encode('utf-8'))

ble_manager = BLEService()
