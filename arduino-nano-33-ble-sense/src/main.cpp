/*
  BLE + Camera + TFLite Person Detection
  - No motion/gyro sensors (stripped for RAM)
  - Continuously captures images with OV7675 camera
  - Runs person detection inference on each frame
  - Sends results via BLE
*/
#include <ArduinoBLE.h>
#include <MicroTFLite.h>
#include "model.h"
#include "PhotoService.h"

/* BLE */
BLEService customService("12345678-1234-5678-1234-56789abcdefa");
BLEStringCharacteristic inferenceChar("12345678-1234-5678-1234-56789abcdef7", BLERead | BLENotify, 20);

/* TFLite */
const int kTensorArenaSize = 93 * 1024;
static uint8_t tensorArena[kTensorArenaSize] __attribute__((aligned(16)));

/* Camera */
PhotoManager photoManager;
int8_t imageBuffer[96 * 96]; // 9KB cropped image

int counter = 0;

void setup() {
    Serial.begin(115200);
    delay(1000);

    // 1. BLE
    if (!BLE.begin()) {
        Serial.println("BLE Failed!");
        while (1);
    }
    BLE.setLocalName("Nano33BLE-Sensing");
    customService.addCharacteristic(inferenceChar);
    BLE.addService(customService);
    BLE.setAdvertisedService(customService);
    BLE.advertise();
    Serial.println("[OK] BLE advertising as 'Nano33BLE-Sensing'");

    // 2. Camera
    if (!photoManager.begin()) {
        Serial.println("Camera Failed!");
        while (1);
    }
    Serial.println("[OK] Camera initialized (QCIF 176x144 Grayscale)");

    // 3. TFLite
    if (!ModelInit(g_person_detect_model_data, tensorArena, kTensorArenaSize)) {
        Serial.println("TFLite Init Failed! Arena too small?");
        while (1);
    }
    Serial.println("[OK] TFLite model loaded");
    Serial.println("[OK] Ready - waiting for BLE connection to start inference");
}

void loop() {
    BLE.poll();

    // Only run inference when a central device is connected
    BLEDevice central = BLE.central();
    if (!central || !central.connected()) {
        delay(100);
        return;
    }

    // Capture image from camera
    if (!photoManager.captureAndCrop(imageBuffer, 96, 96)) {
        Serial.println("Capture failed!");
        delay(1000);
        return;
    }

    // Copy captured image into TFLite input tensor
    for (int i = 0; i < 96 * 96; i++) {
        ModelSetInput(imageBuffer[i], i);
    }

    // Run inference
    BLE.poll();
    if (!ModelRunInference()) {
        Serial.println("Inference Failed!");
        delay(2000);
        return;
    }

    // Read results: index 0 = Not Person, index 1 = Person
    float notPersonScore = ModelGetOutput(0);
    float personScore = ModelGetOutput(1);

    Serial.print("#");
    Serial.print(counter);
    Serial.print(" Person: ");
    Serial.print(personScore, 4);
    Serial.print(", Not Person: ");
    Serial.println(notPersonScore, 4);

    // Send over BLE
    String msg = "Person: " + String(personScore, 2);
    inferenceChar.writeValue(msg);

    counter++;

    // Non-blocking delay: poll BLE every 100ms to stay responsive
    for (int i = 0; i < 10; i++) {
        BLE.poll();
        delay(100);
    }
}
