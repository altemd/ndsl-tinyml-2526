#include "PhotoService.h"

PhotoManager::PhotoManager() {}

bool PhotoManager::begin() {
  // We use QCIF (176x144) and GRAYSCALE to save RAM for the AI model
  // 1 is the frame rate divisor
  if (!Camera.begin(QCIF, GRAYSCALE, 1)) {
    return false;
  }

  _width = Camera.width();
  _height = Camera.height();
  _bytesPerPixel = Camera.bytesPerPixel();
  Serial.println(_width);
  Serial.println(_height);
  Serial.println(_bytesPerPixel);
  
  return true;
}

bool PhotoManager::captureAndCrop(int8_t* out_image_data, int target_w, int target_h) {
  // Library invocation to read raw bytes into our buffer
  Camera.readFrame(_rawBuffer);

  // Calculate cropping offsets to center the 96x96 image
  int start_x = (_width - target_w) / 2;
  int start_y = (_height - target_h) / 2;
  int out_idx = 0;

  for (int y = start_y; y < start_y + target_h; y++) {
    for (int x = start_x; x < start_x + target_w; x++) {
      // Get pixel from the raw frame
      byte pixel = _rawBuffer[(y * _width) + x];
      
      // Convert 0..255 unsigned to -128..127 signed for TinyML
      out_image_data[out_idx++] = (int8_t)(pixel - 128);
    }
  }
  return true;
}