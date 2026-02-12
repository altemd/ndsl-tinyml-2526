#ifndef GYRO_SERVICE_H
#define GYRO_SERVICE_H

#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>
#include "Debounce.h"

class GyroManager {
public:
    GyroManager();
    bool begin();
    void update();
    String getGyroStatus();

private:
    BLEService _gyroService;
    BLEStringCharacteristic _gyroChar;

    // Constants for rotation detection
    const float ROTATION_THRESHOLD = 20.0; // degrees per second
    const unsigned long ROTATION_DELAY = GLOBAL_DEBOUNCE; // Keep "ROTATING" state for 500ms

    // State variables
    bool _lastRotating = false;
    unsigned long _lastRotationDetectedTime = 0;
    unsigned long _lastIMURead = 0;
    String _gyroStatus = "STILL";
};

#endif