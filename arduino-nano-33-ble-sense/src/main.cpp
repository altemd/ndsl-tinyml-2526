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
#include "Debounce.h"

MotionManager motionManager;
GyroManager gyroManager;

const unsigned long REST_THRESHOLD = 5000; 
unsigned long lastMotionTime = 0;
bool pictureTaken = false;
bool isWaiting = false;

void setup() {
    Serial.begin(115200);

    if (!BLE.begin()) {
        Serial.println("BLE Failed.");
        while (1);
    }

    if (!motionManager.begin() || !gyroManager.begin()) {
        Serial.println("IMU Failed.");
        while (1);
    }

    BLE.advertise();
    Serial.println("System online");
}

void loop() {
    BLEDevice central = BLE.central();
    
    if (central) {
        Serial.print("Connected to: ");
        Serial.println(central.address());
        lastMotionTime = millis();
        pictureTaken = false;
        isWaiting = false;
        
        while (central.connected()) {
            motionManager.update();
            gyroManager.update();

            bool isMoving = (gyroManager.getGyroStatus() == "ROTATING" || motionManager.getMotionStatus() == "MOVING");
            if (isMoving) {
                lastMotionTime = millis();
                pictureTaken = false;
                isWaiting = false;
                Serial.println("Motion detected, not taking picture.");
                delay (500);
                continue;
            } else {
                unsigned long restDuration = millis() - lastMotionTime;
                if (!isWaiting && !pictureTaken) {
                    isWaiting = true;
                    Serial.print("Ensuring stillness. waiting for ");
                    Serial.print(REST_THRESHOLD / 1000);
                    Serial.println(" seconds before taking a picture.");
                }
                if (restDuration >= REST_THRESHOLD && !pictureTaken) {
                    Serial.println("Taking picture.");
                    pictureTaken = true;
                    isWaiting = false;
                    delay (1000);
                    Serial.println("Photo taken!");
                    continue;
                }
            }
            delay (10);
        }

        Serial.println("Disconnected");
    }
}
