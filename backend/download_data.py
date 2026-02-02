import os
import json
import requests
from pathlib import Path
import gzip
import numpy as np
import shutil

# backend/data/images/person
# backend/data/images/emnist

BASE_DIR = Path(__file__).parent / "data" / "images"
PERSON_DIR = BASE_DIR / "person"
EMNIST_DIR = BASE_DIR / "emnist"

os.makedirs(PERSON_DIR, exist_ok=True)
os.makedirs(EMNIST_DIR, exist_ok=True)

def download_file(url, dest_path):
    print(f"Downloading {url}...")
    try:
        # Use a browser-like User-Agent to avoid generic blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Saved to {dest_path}")
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False



# Valid URLs for Person Detection (YOLO/COCO samples)
# Format: (URL, Label)
PERSON_DATA = [
     # Positives
    ("https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/zidane.jpg", "person"),
    ("https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/bus.jpg", "person"),
    ("https://raw.githubusercontent.com/pjreddie/darknet/master/data/person.jpg", "person"),
    # Negatives
    ("https://raw.githubusercontent.com/pjreddie/darknet/master/data/horses.jpg", "no_person"),
    ("https://raw.githubusercontent.com/pjreddie/darknet/master/data/eagle.jpg", "no_person"),
    ("https://raw.githubusercontent.com/pjreddie/darknet/master/data/dog.jpg", "no_person"),
    ("https://raw.githubusercontent.com/pjreddie/darknet/master/data/giraffe.jpg", "no_person"),
    ("https://raw.githubusercontent.com/pjreddie/darknet/master/data/kite.jpg", "no_person"), # Mostly kite
]

LABELS = {}

def download_person_data():
    print("Downloading Person Detection samples...")
    print(f"Downloading {len(PERSON_DATA)} person samples...")
    for i, (url, label) in enumerate(PERSON_DATA):
        ext = url.split('.')[-1]
        name = f"sample_{i}.{ext}"
        path = PERSON_DIR / name
        
        LABELS[name] = label 
        
        if download_file(url, path):
            print(f"Downloaded {name}")
        else:
            print(f"Failed to download {name}")

def generate_emnist_letters():
    print("Generating EMNIST Letter samples (A-Z)...")
    from PIL import Image, ImageDraw, ImageFont
    import string
    
    # Try to load a generic font, or fallback to default
    try:
        # Windows usually has arial
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    for char in string.ascii_uppercase:
        img = Image.new('L', (28, 28), color=0) # Black background
        draw = ImageDraw.Draw(img)
        
        # Center the text approximately
        # bbox = draw.textbbox((0, 0), char, font=font) 
        # w = bbox[2] - bbox[0]; h = bbox[3] - bbox[1]
        # x = (28 - w) / 2; y = (28 - h) / 2
        
        # Simple centering for default/basic fonts
        draw.text((8, 4), char, fill=255, font=font) 
        
        # Add some noise/transforms to make it look "handwritten" or at least data-like?
        # For now, clean letters are fine for a demo.
        
        name = f"letter_{char}.png"
        img.save(EMNIST_DIR / name)
        LABELS[name] = char # Store 'A', 'B' etc.
        
    print("Generated 26 Letter samples.")

def download_emnist_samples():
    print("Downloading EMNIST (MNIST) samples...")
    # ... (existing content)
    # Images
    current_count = 50
    img_url = "https://ossci-datasets.s3.amazonaws.com/mnist/t10k-images-idx3-ubyte.gz"
    img_gz_path = EMNIST_DIR / "t10k-images-idx3-ubyte.gz"
    # Labels
    lbl_url = "https://ossci-datasets.s3.amazonaws.com/mnist/t10k-labels-idx1-ubyte.gz"
    lbl_gz_path = EMNIST_DIR / "t10k-labels-idx1-ubyte.gz"

    download_file(img_url, img_gz_path)
    download_file(lbl_url, lbl_gz_path)
    
    import struct
    try:
        # Read Labels
        labels = []
        with gzip.open(lbl_gz_path, 'rb') as f:
            magic, size = struct.unpack(">II", f.read(8))
            if magic != 2049:
                print("Invalid label magic")
            else:
                 buf = f.read(current_count) # Read first N labels
                 labels = np.frombuffer(buf, dtype=np.uint8)

        # Read Images
        with gzip.open(img_gz_path, 'rb') as f:
            magic, size = struct.unpack(">II", f.read(8))
            rows, cols = struct.unpack(">II", f.read(8))
            
            from PIL import Image
            for i in range(current_count):
                buf = f.read(rows * cols)
                data = np.frombuffer(buf, dtype=np.uint8).reshape(rows, cols)
                img = Image.fromarray(data, mode='L')
                name = f"digit_{i}.png"
                img.save(EMNIST_DIR / name)
                
                # Save label
                if i < len(labels):
                    LABELS[name] = int(labels[i])

        print(f"Extracted {current_count} MNIST samples with labels.")
        
    except Exception as e:
        print(f"Failed to process MNIST: {e}")

if __name__ == "__main__":
    download_person_data()
    download_emnist_samples()
    generate_emnist_letters()
    
    # Save Labels
    with open(BASE_DIR / "labels.json", "w") as f:
        json.dump(LABELS, f, indent=2)
    print("Saved labels.json")
