#include "GyroService.h"

GyroManager::GyroManager() : 
  // Use a unique UUID (ending in '2' and '3' to differentiate from Motion)
  _gyroService("12345678-1234-5678-1234-56789abcdef2"),
  _gyroChar("12345678-1234-5678-1234-56789abcdef3", BLERead | BLENotify, 16) 
{}

String GyroManager::getGyroStatus() {
    return _gyroStatus;
}

bool GyroManager::begin() {
  // IMU.begin() is usually called once. If MotionManager already called it, 
  // this will just return true.
  if (!IMU.begin()) return false;

  _gyroService.addCharacteristic(_gyroChar);
  BLE.addService(_gyroService);
  BLE.setAdvertisedService(_gyroService);
  
  _gyroChar.writeValue("STILL");
  return true;
}

void GyroManager::update() {
  unsigned long now = millis();

  // Read Gyro at 10Hz
  if (now - _lastIMURead >= 100) {
    _lastIMURead = now;

    float x, y, z;
    if (IMU.gyroscopeAvailable()) {
      IMU.readGyroscope(x, y, z);

      // Calculate the magnitude of angular velocity
      float magnitude = sqrt(x * x + y * y + z * z);
      
      // Check if currently rotating above threshold
      bool isRotatingInstant = magnitude > ROTATION_THRESHOLD;

      if (isRotatingInstant) {
        _lastRotationDetectedTime = now;
      }

      // Logic: Stay "ROTATING" if we saw rotation within the last ROTATION_DELAY ms
      bool isRotatingDebounced = (now - _lastRotationDetectedTime < ROTATION_DELAY);
      String a = getGyroStatus();
      _gyroStatus  = (isRotatingDebounced ? "ROTATING" : "STILL");

      if (isRotatingDebounced != _lastRotating) {
        _lastRotating = isRotatingDebounced;
        _gyroChar.writeValue(_gyroStatus);
        
        Serial.print("Gyro State: ");
        Serial.println(_gyroStatus);
      }
    }
  }
}