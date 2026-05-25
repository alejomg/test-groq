import httpx
import os
from loguru import logger

BACKEND_URL = f"{os.getenv("APP_HOST", "http://127.0.0.1")}:{os.getenv("APP_PORT", "8000")}"
DIALOG_PATH = "/api/v1/dialog"
CONNECTION_TIMEOUT = 60.0


async def send_api_request(message: str, duuid: str = None) -> dict:
    """
    Sends the message to the server and gets the response.
    """
    payload = {
        "message": message,
        "duuid": str(duuid) if duuid else None
    }

    logger.info(f"Sending payload: {payload}")

    async with httpx.AsyncClient(timeout=CONNECTION_TIMEOUT) as client:
        try:
            response = await client.post(f"{BACKEND_URL}{DIALOG_PATH}", json=payload)

            if response.status_code == 200:
                logger.info(f"Response: {response.json()}")
                return response.json()
            else:
                logger.error(f"Server error ({response.status_code}): {response.text}")
                raise Exception(f"Server error {response.status_code}.")

        except httpx.RequestError as exc:
            logger.error(f"Server connection error: {exc}")
            raise Exception("Server connection error.")
