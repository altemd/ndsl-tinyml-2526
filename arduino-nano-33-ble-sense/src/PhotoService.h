#ifndef PHOTO_SERVICE_H
#define PHOTO_SERVICE_H

#include <Arduino_OV767X.h>

class PhotoManager {
public:
    PhotoManager();
    bool begin();
    bool captureAndCrop(int8_t* out_image_data, int target_w, int target_h);

private:
    int _width;
    int _height;
    int _bytesPerPixel;
    // Buffer for one raw frame (QCIF Grayscale = 176 * 144 * 1)
    byte _rawBuffer[176 * 144]; 
};

#endif