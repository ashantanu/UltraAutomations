import os
import requests
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL")
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

def login():
    """Login and get access token"""
    if not API_BASE_URL:
        logger.error("API_BASE_URL environment variable not set for login.")
        return None
    if not EMAIL:
        logger.error("EMAIL environment variable not set for login.")
        return None
    if not PASSWORD:
        logger.error("PASSWORD environment variable not set for login.")
        return None

    login_url = f"{API_BASE_URL}/auth/login"
    payload = {
        "email": EMAIL,
        "password": PASSWORD
    }

    try:
        logger.info(f"Attempting to login to {login_url}")
        response = requests.post(login_url, json=payload)

        if response.status_code != 200:
            logger.error(f"Login failed: {response.status_code} - {response.text}")
            return None

        logger.info("Login successful.")
        return response.json().get("access_token")

    except Exception as e:
        logger.error(f"An error occurred during login: {str(e)}")
        return None

def run_summary_job():
    """Logs in and calls the /email-to-youtube endpoint."""
    logger.info("Starting summary job.")

    token = login()
    if not token:
        logger.error("Failed to obtain authentication token. Aborting job.")
        return

    if not API_BASE_URL:
         # This check is technically redundant after login(), but good defensive programming
        logger.error("API_BASE_URL environment variable not set.")
        return

    upload_url = f"{API_BASE_URL}/email-to-youtube"

    headers = {
        'Authorization': f'Bearer {token}'
    }

    try:
        logger.info(f"Calling endpoint: {upload_url}")
        response = requests.post(upload_url, headers=headers)

        if response.status_code == 200:
            logger.info("Email-to-YouTube job triggered successfully.")
            logger.info(f"Response: {response.json()}")
        else:
            logger.error(f"Failed to trigger Email-to-YouTube job. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")

    except Exception as e:
        logger.error(f"An error occurred while calling the endpoint: {str(e)}")

if __name__ == "__main__":
    run_summary_job() 