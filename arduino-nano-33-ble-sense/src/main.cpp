/*
Flow of system:
1. Initial state: Sleep / Low Power 
2. Detect motion
    - If motion, go to 1.
    - if no motion go to 3.
3. Capture image
4. Run image similarity algorithm with adjustable threshold
    - If image similar, go to 5
    - If image different, go to 6
5. Run AI inference
6. Transmit data (i.e., model classification | image similarity) to ubuntu host via BLE
*/ 

#include <ArduinoBLE.h>
#include "MotionService.h"
#include "GyroService.h"
#include "PhotoService.h"
#include "Debounce.h"

/* =======================
   BLE Services & Chars
   ======================= */
BLEService customService("12345678-1234-5678-1234-56789abcdefa");

BLEStringCharacteristic motionChar("12345678-1234-5678-1234-56789abcdef1", BLERead | BLENotify, 16);
BLEStringCharacteristic gyroChar("12345678-1234-5678-1234-56789abcdef3", BLERead | BLENotify, 16);
// Image characteristic: 128-byte chunks for streaming 96x96 grid
BLECharacteristic imageChar("12345678-1234-5678-1234-56789abcdef5", BLERead | BLENotify, 128);

/* =======================
   Global Managers
   ======================= */
MotionManager motionManager;
GyroManager gyroManager;
PhotoManager photoManager;

int8_t imageBuffer[96 * 96]; // 9,216 bytes
const unsigned long REST_THRESHOLD = 2000; 
unsigned long lastMotionTime = 0;
bool pictureTaken = false;
bool isWaiting = false;

/* =======================
   Helper: Print to Serial
   ======================= */
void printImageHex(int8_t* data, int w, int h) {
  Serial.println("--- HEX DATA START ---");
  for (int i = 0; i < (w * h); i++) {
    if ((uint8_t)data[i] < 0x10) Serial.print("0");
    Serial.print((uint8_t)data[i], HEX);
    if (i < (w * h) - 1) Serial.print(",");
    if ((i + 1) % 16 == 0) {
        Serial.println();
        BLE.poll(); // Keep BLE connection alive during long print
    }
  }
  Serial.println("\n--- HEX DATA END ---");
}

/* =======================
   Helper: Stream over BLE
   ======================= */
void streamImageBLE(int8_t* data, int totalSize) {
    int chunkSize = 128;
    int sentBytes = 0;
    Serial.println("Streaming image over BLE...");

    while (sentBytes < totalSize) {
        int remaining = totalSize - sentBytes;
        int currentChunkSize = (remaining < chunkSize) ? remaining : chunkSize;

        imageChar.writeValue(&data[sentBytes], currentChunkSize);
        sentBytes += currentChunkSize;

        delay(25); // Small delay to prevent congestion
        BLE.poll();
    }
    Serial.println("BLE Stream Done.");
}

/* =======================
   Setup
   ======================= */
void setup() {
    Serial.begin(115200);

    if (!BLE.begin()) {
        Serial.println("BLE Failed.");
        while (1);
    }

    // Set stability parameters
    BLE.setLocalName("Nano33BLE-Sensing");

    customService.addCharacteristic(motionChar);
    customService.addCharacteristic(gyroChar);
    customService.addCharacteristic(imageChar);
    BLE.addService(customService);

    if (!motionManager.begin() || !gyroManager.begin() || !photoManager.begin()) {
        Serial.println("Sensors/Camera Failed.");
        while (1);
    }

    BLE.setAdvertisedService(customService);
    BLE.advertise();
    Serial.println("System online - Ready for Connection");
}

/* =======================
   Main Loop
   ======================= */
void loop() {
    BLEDevice central = BLE.central();
    BLE.poll();

    // 1. Update Sensors
    motionManager.update();
    gyroManager.update();

    // Update BLE characteristics with latest sensor states
    motionChar.writeValue(motionManager.getMotionStatus());
    gyroChar.writeValue(gyroManager.getGyroStatus());

    // 2. Motion Logic
    bool isMoving = (gyroManager.getGyroStatus() == "ROTATING" || motionManager.getMotionStatus() == "MOVING");

    if (isMoving) {
        lastMotionTime = millis();
        pictureTaken = false;
        isWaiting = false;
    } else {
        unsigned long restDuration = millis() - lastMotionTime;

        if (!isWaiting && !pictureTaken) {
            isWaiting = true;
            Serial.println("Ensuring stillness...");
        }

        if (restDuration >= REST_THRESHOLD && !pictureTaken) {
            Serial.println("Capture Triggered.");
            
            if (photoManager.captureAndCrop(imageBuffer, 96, 96)) {
                pictureTaken = true;
                isWaiting = false;
                Serial.println("Success! Processing data...");
                
                BLE.poll();
                printImageHex(imageBuffer, 96, 96);
                
                // 3. Stream to BLE if connected
                if (central && central.connected()) {
                    streamImageBLE(imageBuffer, 96 * 96);
                }
            } else {
                Serial.println("Photo Capture failed!");
                lastMotionTime = millis(); // retry
            }
        }
    }

    // 4. Handle connection status
    if (central && !central.connected()) {
        BLE.advertise(); // Ensure we advertise if central drops
    }

    delay(10);
}