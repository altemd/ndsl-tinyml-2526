
import asyncio
import logging
from bleak import BleakScanner, BleakClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TODO: Replace with your actual UUIDs from the Arduino sketch
# These are commonly used examples or you might need to find them via scanning
SERVICE_UUID = "19B10000-E8F2-537E-4F6C-D104768A1214" 
CHARACTERISTIC_UUID_RX = "19B10001-E8F2-537E-4F6C-D104768A1214" # Receiving data from Arduino
CHARACTERISTIC_UUID_TX = "19B10002-E8F2-537E-4F6C-D104768A1214" # Sending commands to Arduino

class BLEService:
    def __init__(self):
        self.client = None
        self.device = None
        self.connected = False
        self.callbacks = []

    async def scan_and_connect(self):
        logger.info("Scanning for Arduino Nano 33 BLE Sense...")
        devices = await BleakScanner.discover()
        target_device = None
        
        for d in devices:
            # You might need to adjust the name check depending on your Arduino sketch
            if d.name and "Arduino" in d.name: 
                target_device = d
                break
        
        if not target_device:
            logger.warning("Arduino not found during scan.")
            self._notify_all("SYSTEM: ARDUINO_SCAN_FAILED")
            return False

        logger.info(f"Found device: {target_device.name} ({target_device.address})")
        self.device = target_device
        
        try:
            self.client = BleakClient(target_device.address)
            await self.client.connect()
            self.connected = True
            logger.info(f"Connected to {target_device.name}")
            self._notify_all("SYSTEM: ARDUINO_CONNECTED")
            
            # Start notifications if the characteristic exists
            # await self.client.start_notify(CHARACTERISTIC_UUID_RX, self.notification_handler)
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.connected = False
            self._notify_all("SYSTEM: ARDUINO_ERROR")
            return False

    async def disconnect(self):
        if self.client and self.connected:
            await self.client.disconnect()
            self.connected = False
            logger.info("Disconnected")
            self._notify_all("SYSTEM: ARDUINO_DISCONNECTED")

    def _notify_all(self, msg):
        for callback in self.callbacks:
            asyncio.create_task(callback(msg))

    def notification_handler(self, sender, data):
        """Handle incoming data from Arduino"""
        # Parse logic depends on how you send data (e.g., struct, string, JSON)
        # For now, we assume a simple string or byte array
        logger.info(f"Received data: {data}")
        msg = data.decode('utf-8').strip()
        
        # Notify all registered callbacks (e.g., websockets)
        for callback in self.callbacks:
            asyncio.create_task(callback(msg))

    def register_callback(self, callback):
        self.callbacks.append(callback)

    async def send_command(self, command: str):
        if self.connected and self.client:
            await self.client.write_gatt_char(CHARACTERISTIC_UUID_TX, command.encode('utf-8'))

ble_manager = BLEService()
