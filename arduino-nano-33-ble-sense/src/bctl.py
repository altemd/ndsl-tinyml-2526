import asyncio
from bleak import BleakScanner, BleakClient

ARDUINO_ADDR = '02:7B:B9:31:62:1A'
BATTERY_UUID = '00002a19-0000-1000-8000-00805f9b34fb'
# /org/bluez/hci0/dev_02_7B_B9_31_62_1A/service000a/char000b
MOTION_UUID = '12345678-1234-5678-1234-56789abcdef1'
GYRO_UUID = '12345678-1234-5678-1234-56789abcdef3'


async def scan():
    devices = await BleakScanner.discover()
    for d in devices:
        print(d)

# asyncio.run(scan())


async def inspect():
    async with BleakClient(ARDUINO_ADDR) as client:
        for service in client.services:
            print(f'{service.description}: {service.uuid}')
            for i, characteristic in enumerate(service.characteristics):
                print(
                    f'    {i+1}. {characteristic.description}: {characteristic.uuid}')

# asyncio.run(inspect())


async def read_battery():
    async with BleakClient(ARDUINO_ADDR) as client:
        value = await client.read_gatt_char(BATTERY_UUID)
        print(value)
        print(f'Battery: {value[0]}%')

# asyncio.run(read_battery())


def batt_handler(sender, data):
    print(f'Battery: {ord(data.decode())}%')


async def batt_notify():
    async with BleakClient(ARDUINO_ADDR) as client:
        await client.start_notify(BATTERY_UUID, batt_handler)
        await asyncio.Event().wait()

# asyncio.run(batt_notify())


def motion_handler(sender, data):
    try:
        msg = data.decode()
    except UnicodeDecodeError:
        msg = data
    print(f"Motion: {msg}")


def gyro_handler(sender, data):
    try:
        msg = data.decode()
    except UnicodeDecodeError:
        msg = data
    print(f"Gyro: {msg}")


async def motion_main():
    async with BleakClient(ARDUINO_ADDR) as client:
        print("Connected")

        # Subscribe to notifications
        # await client.start_notify(BATTERY_UUID, batt_handler)
        await client.start_notify(MOTION_UUID, motion_handler)
        await client.start_notify(GYRO_UUID, gyro_handler)

        print("Subscribed to motion notifications")

        # Keep program alive
        await asyncio.Event().wait()


asyncio.run(motion_main())