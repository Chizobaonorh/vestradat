"""
Example: How to use VestraDAT with Cloudinary

This example shows how to upload images to Cloudinary and use the URLs
with the VestraDAT measurement API.
"""

import cloudinary
import cloudinary.uploader
import requests
import json

# Configure Cloudinary (replace with your credentials)
cloudinary.config(
    cloud_name="your-cloud-name",
    api_key="your-api-key", 
    api_secret="your-api-secret"
)

def upload_to_cloudinary(image_path, public_id=None):
    """Upload image to Cloudinary and return URL"""
    try:
        result = cloudinary.uploader.upload(
            image_path,
            public_id=public_id,
            transformation=[
                {'width': 500, 'height': 700, 'crop': 'limit'},  # Optimize size
                {'quality': 'auto'},  # Auto quality
                {'format': 'jpg'}  # Convert to JPG
            ]
        )
        return result['secure_url']
    except Exception as e:
        print(f"Upload failed: {e}")
        return None

def measure_with_cloudinary_urls(front_url, side_url, height_cm, api_url="http://localhost:5000/measure"):
    """Send measurement request using Cloudinary URLs"""
    payload = {
        "frontImageUrl": front_url,
        "sideImageUrl": side_url,
        "userHeight": height_cm
    }
    
    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Measurement failed: {e}")
        return None

# Example usage
if __name__ == "__main__":
    # Upload images to Cloudinary
    front_url = upload_to_cloudinary("path/to/front_image.jpg", "user123_front")
    side_url = upload_to_cloudinary("path/to/side_image.jpg", "user123_side")
    
    if front_url and side_url:
        print(f"Front image: {front_url}")
        print(f"Side image: {side_url}")
        
        # Get measurements
        result = measure_with_cloudinary_urls(front_url, side_url, 170)
        
        if result and result.get('success'):
            measurements = result['measurements']
            print("\nMeasurements:")
            for key, value in measurements.items():
                print(f"  {key}: {value:.1f} inches")
        else:
            print("Measurement failed")
    else:
        print("Image upload failed")