import asyncio
from bleak import BleakScanner, BleakClient

# Configuration
ARDUINO_ADDR = '02:7B:B9:31:62:1A'
MOTION_UUID = '12345678-1234-5678-1234-56789abcdef1'
GYRO_UUID = '12345678-1234-5678-1234-56789abcdef3'
IMAGE_UUID = '12345678-1234-5678-1234-56789abcdef5'

# Image reconstruction buffer
image_data_full = bytearray()
EXPECTED_SIZE = 9216  # 96 * 96


def motion_handler(sender, data):
    try:
        msg = data.decode()
    except:
        msg = data
    print(f"Motion Update: {msg}")


def gyro_handler(sender, data):
    try:
        msg = data.decode()
    except:
        msg = data
    print(f"Gyro Update: {msg}")


def image_handler(sender, data):
    global image_data_full
    image_data_full.extend(data)

    print(f"Receiving Image: {len(image_data_full)
                              }/{EXPECTED_SIZE} bytes", end='\r')

    if len(image_data_full) >= EXPECTED_SIZE:
        print(f"\n[SUCCESS] Full image received ({
              len(image_data_full)} bytes).")

        # Save as binary
        with open("ble_image.bin", "wb") as f:
            f.write(image_data_full)

        # Save as CSV hex for the visualization script
        with open("hex_data.txt", "w") as f:
            hex_vals = [f"{b:02X}" for b in image_data_full]
            f.write(",".join(hex_vals))

        print("Data saved to hex_data.txt and ble_image.bin")
        image_data_full = bytearray()  # Reset for next capture


async def motion_main():
    print(f"Scanning for Arduino at {ARDUINO_ADDR}...")

    while True:
        try:
            async with BleakClient(ARDUINO_ADDR, timeout=20.0) as client:
                print(f"\nConnected to {ARDUINO_ADDR}")

                # This helper finds the specific characteristic object to avoid UUID ambiguity
                def find_char(uuid):
                    for service in client.services:
                        for char in service.characteristics:
                            if char.uuid.lower() == uuid.lower():
                                return char
                    return None

                # Resolve the actual characteristic objects
                char_motion = find_char(MOTION_UUID)
                char_gyro = find_char(GYRO_UUID)
                char_image = find_char(IMAGE_UUID)

                if char_motion and char_gyro and char_image:
                    # Subscribe using the characteristic objects (not the UUID strings)
                    await client.start_notify(char_motion, motion_handler)
                    await client.start_notify(char_gyro, gyro_handler)
                    await client.start_notify(char_image, image_handler)
                    print("Subscribed to all notifications successfully.")
                else:
                    print("Error: Could not find all required characteristics.")
                    await client.disconnect()

                while client.is_connected:
                    await asyncio.sleep(1.0)

                print("\nDisconnected. Retrying...")

        except Exception as e:
            print(f"\n[Connection Status]: {e}")
            print("Cleaning up and retrying in 3 seconds...")
            await asyncio.sleep(3)

if __name__ == "__main__":
    try:
        asyncio.run(motion_main())
    except KeyboardInterrupt:
        print("\nUser stopped the script.")
