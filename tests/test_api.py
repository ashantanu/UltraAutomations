import os
import requests
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def main():
    # Get credentials from environment variables
    email = os.getenv('EMAIL')
    password = os.getenv('PASSWORD')
    base_url = os.getenv('BASE_URL', 'http://localhost:8000')
    
    if not email or not password:
        logger.error("Email or password not found in environment variables")
        return

    # Login request
    logger.info("Making login request...")
    login_url = f"{base_url}/auth/login"
    login_data = {
        "email": email,
        "password": password
    }
    
    try:
        login_response = requests.post(
            login_url,
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        login_response.raise_for_status()
        login_data = login_response.json()
        logger.info("Login successful")
        
        # Extract access token
        access_token = login_data.get('access_token')
        if not access_token:
            logger.error("No access token found in login response")
            return
            
        # Chat request
        logger.info("Making chat request...")
        chat_url = f"{base_url}/chat"
        chat_data = {
            "message": "hello"
        }
        
        chat_response = requests.post(
            chat_url,
            json=chat_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
        )
        chat_response.raise_for_status()
        chat_data = chat_response.json()
        
        logger.info("Chat response received:")
        logger.info(json.dumps(chat_data, indent=2))
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {str(e)}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main() 