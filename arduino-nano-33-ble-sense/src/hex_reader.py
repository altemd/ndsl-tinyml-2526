import numpy as np
import matplotlib.pyplot as plt
import os


def display_arduino_image(filename, width=96, height=96):
    try:
        # Check if file exists
        if not os.path.exists(filename):
            print(f"Error: File '{filename}' not found.")
            return

        # 1. Determine file type and load data
        if filename.endswith(".bin"):
            print(f"Reading binary data from {filename}...")
            with open(filename, 'rb') as f:
                raw_bytes = f.read()
            # Convert binary bytes to list of integers
            pixel_values = list(raw_bytes)
        else:
            print(f"Reading hex text data from {filename}...")
            with open(filename, 'r') as f:
                raw_content = f.read()
            # Clean and split hex strings
            raw_content = raw_content.replace('\n', ',').replace(' ', '')
            hex_list = [h.strip() for h in raw_content.split(',') if h.strip()]
            pixel_values = [int(h, 16) for h in hex_list]

        print(f"Total pixels found: {len(pixel_values)}")

        # 2. Validation
        expected_size = width * height
        if len(pixel_values) < expected_size:
            print(f"Warning: Not enough data. Expected {
                  expected_size}, got {len(pixel_values)}")
            # Pad with zeros if necessary
            pixel_values += [0] * (expected_size - len(pixel_values))
        else:
            pixel_values = pixel_values[:expected_size]

        # 3. REVERSE THE ARDUINO MATH:
        # Arduino logic: (int8_t)(original_pixel - 128)
        # To get back to 0-255: (value + 128) % 256
        final_pixels = []
        for val in pixel_values:
            # We use % 256 to handle the wraparound of signed 8-bit math
            original_pixel = (val + 128) % 256
            final_pixels.append(original_pixel)

        # 4. Reshape into 2D array
        img_array = np.array(
            final_pixels, dtype=np.uint8).reshape((height, width))

        # 5. Plotting
        plt.figure(figsize=(8, 8))
        plt.imshow(img_array, cmap='gray', vmin=0, vmax=255)
        plt.title(f"BLE Captured Image ({width}x{height})\nFile: {filename}")
        plt.axis('off')
        plt.colorbar(label="Brightness (0-255)")
        plt.show()

    except Exception as e:
        print(f"An error occurred: {e}")


# Run the function
if __name__ == "__main__":
    # Prioritize the binary file from BLE, fall back to hex_data.txt
    if os.path.exists("ble_image.bin"):
        display_arduino_image("ble_image.bin")
    else:
        display_arduino_image("hex_data.txt")
