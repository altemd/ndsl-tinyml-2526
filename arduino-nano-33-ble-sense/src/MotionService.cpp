#include "MotionService.h"

MotionManager::MotionManager() : 
  _motionService("12345678-1234-5678-1234-56789abcdef0"),
  _motionChar("12345678-1234-5678-1234-56789abcdef1", BLERead | BLENotify, 16) 
{}

String MotionManager::getMotionStatus() {
    return _motionStatus;
}

bool MotionManager::begin() {
  if (!IMU.begin()) return false;
  
  BLE.setLocalName("Nano33BLE-Motion");
  _motionService.addCharacteristic(_motionChar);
  BLE.addService(_motionService);
  BLE.setAdvertisedService(_motionService);
  
  _motionChar.writeValue("STILL");
  return true;
}

void MotionManager::update() {
  unsigned long now = millis();

  // Read IMU at 10Hz
  if (now - _lastIMURead >= 100) {
    _lastIMURead = now;

    float x, y, z;
    if (IMU.accelerationAvailable()) {
      IMU.readAcceleration(x, y, z);

      float magnitude = sqrt(x * x + y * y + z * z);
      bool currentlyMovingInstant = abs(magnitude - 1.0) > MOTION_THRESHOLD;

      if (currentlyMovingInstant) {
        _lastMotionDetectedTime = now;
      }

      // Debounce logic
      bool isMovingDebounced = (now - _lastMotionDetectedTime < MOTION_DELAY);
      _motionStatus  = (isMovingDebounced ? "MOVING" : "STILL");

      if (isMovingDebounced != _lastMoving) {
        _lastMoving = isMovingDebounced;
        _motionChar.writeValue(_motionStatus);

        Serial.print("Motion State: ");
        Serial.println(_motionStatus);
      }
    }
  }
}