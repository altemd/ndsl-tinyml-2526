#ifndef MOTION_SERVICE_H
#define MOTION_SERVICE_H

#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>
#include "Debounce.h"

class MotionManager {
public:
    MotionManager();
    bool begin();
    void update();
    String getMotionStatus();

private:
    BLEService _motionService;
    BLEStringCharacteristic _motionChar;

    const float MOTION_THRESHOLD = 0.04; // sensitivity (difference from 1.0g)
    const unsigned long MOTION_DELAY = GLOBAL_DEBOUNCE; // stay in MOVE state after last movement
    
    bool _lastMoving = false;
    unsigned long _lastMotionDetectedTime = 0;
    unsigned long _lastIMURead = 0;
    String _motionStatus = "STILL";
};

#endif