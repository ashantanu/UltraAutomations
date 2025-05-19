import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = "http://localhost:8000"
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

def login():
    """Login and get access token"""
    login_url = f"{API_BASE_URL}/auth/login"
    payload = {
        "email": EMAIL,
        "password": PASSWORD
    }
    
    response = requests.post(login_url, json=payload)
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.text}")
    
    return response.json()["access_token"]

def test_image_processing():
    # Validate required environment variables
    required_vars = ["EMAIL", "PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise Exception(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    try:
        # Step 1: Login and get token
        print("Logging in...")
        token = login()
        print("Login successful!")
        
        # API endpoint URL
        url = f"{API_BASE_URL}/sanity/process-image"
        
        # Test data
        payload = {
            "template_path": "podcast_thumbnail_template.png"
        }
        
        # Headers with authentication
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        # Make the POST request
        print("Processing image...")
        response = requests.post(url, json=payload, headers=headers)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Create test_outputs directory if it doesn't exist
        output_dir = "test_outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"processed_image_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save the image file
        with open(output_path, 'wb') as f:
            f.write(response.content)
            
        print(f"Image successfully saved to: {output_path}")
        print(f"Response Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {str(e)}")
        if hasattr(e.response, 'text'):
            print("Error details:", e.response.text)
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    test_image_processing() 