from .settings import Settings
import httpx
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import hmac
import hashlib
import mimetypes
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MessageResponse:
    """
    A structured representation of WhatsApp API responses.

    This class is designed to normalize both success and error_message responses
    while keeping the original raw response available for debugging.
    """
    success: bool
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[int] = None
    error_type: Optional[str] = None
    error_user_msg: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = field(default=None, repr=False)
    extra: Dict[str, Any] = field(default_factory=dict, repr=False)

    # -----------------------------
    # Factory methods
    # -----------------------------
    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> "MessageResponse":
        """Factory method to create response from WhatsApp Graph API reply."""
        if "messages" in response:  # ✅ Success response
            return cls(
                success=True,
                message_id=response["messages"][0].get("id"),
                raw_response=response,
                extra={k: v for k, v in response.items() if k not in {"messages", "contacts"}}
            )

        if "error" in response:  # ❌ Error response
            err = response["error"]
            return cls(
                success=False,
                error_message=err.get("message"),
                error_code=err.get("code"),
                error_type=err.get("type"),
                error_user_msg=err.get("error_user_msg"),
                raw_response=response,
                extra={k: v for k, v in err.items() if k not in {"message", "code", "type", "error_user_msg"}}
            )

        # Unknown/unsupported format
        return cls(success=False, error_message="Unknown response format", raw_response=response)

    @classmethod
    def from_success(cls, message_id: str, raw_response: Optional[Dict[str, Any]] = None) -> "MessageResponse":
        """Directly create a success response (useful in testing)."""
        return cls(success=True, message_id=message_id, raw_response=raw_response)

    @classmethod
    def from_error(cls, error_message: str, code: Optional[int] = None,
                   raw_response: Optional[Dict[str, Any]] = None) -> "MessageResponse":
        """Directly create an error response (useful in exception handling)."""
        return cls(success=False, error_message=error_message, error_code=code, raw_response=raw_response)

    # -----------------------------
    # Convenience methods    # Convenience methods

    # -----------------------------
    def is_success(self) -> bool:
        return self.success

    def is_error(self) -> bool:
        return not self.success



@dataclass
class MediaUploadResponse:
    success: bool
    media_id: Optional[str] = None
    error_message: Optional[str] = None



# -----------------------------
# WhatsApp API Client
# -----------------------------
class WhatsAppClient:
    """Enhanced WhatsApp Cloud API client with utilities."""

    def __init__(self):
        self.base_url = f"{Settings.GRAPH_API_URL}/{Settings.WHATSAPP_PHONE_ID}/messages"
        self.media_url = f"{Settings.GRAPH_API_URL}/{Settings.WHATSAPP_PHONE_ID}/media"
        self.headers = Settings.headers()
        Settings.validate()

    def send(self, payload: dict) -> MessageResponse:
        """Synchronous message send with structured response."""
        try:
            with httpx.Client(timeout=Settings.DEFAULT_TIMEOUT) as client:
                response = client.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                success_res = MessageResponse.from_api_response(response.json())
                print(success_res)
                
                if success_res.success:
                    print(f"Message sent successfully: {success_res.message_id}")
                
                return success_res
            
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error: {exc.response.status_code} - {exc.response.text}")
            api_error_status =  MessageResponse(success=False, error_message=f"HTTP {exc.response.status_code}: {exc.response.text}")
            print(api_error_status)
            return api_error_status
        
        except Exception as exc:
            logger.error(f"Send error: {exc}", exc_info=True)
            exec_error = MessageResponse(success=False, error_message=str(exc))
            print(exec_error)
            return exec_error

    async def asend(self, payload: dict) -> MessageResponse:
        """Async message send with structured response."""
        try:
            async with httpx.AsyncClient(timeout=Settings.DEFAULT_TIMEOUT) as client:
                response = await client.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                success_res =  MessageResponse.from_api_response(response.json())
                print(success_res)
                return success_res
            
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error: {exc.response.status_code} - {exc.response.text}")
            api_error_status = MessageResponse(success=False, error_message=f"HTTP {exc.response.status_code}: {exc.response.text}")
            print(api_error_status)
            return api_error_status
        except Exception as exc:
            logger.error(f"Send async error: {exc}", exc_info=True)
            return MessageResponse(success=False, error_message=str(exc))

    def upload_media(self, file_path: str, mime_type: Optional[str] = None) -> MediaUploadResponse:
        """Upload media file and get media ID."""
        try:
            path = Path(file_path)
            if not path.exists():
                return MediaUploadResponse(success=False, error_message=f"File not found: {file_path}")

            if mime_type is None:
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    return MediaUploadResponse(success=False, error_message="Could not determine MIME type")

            with httpx.Client(timeout=60.0) as client:
                with open(file_path, "rb") as f:
                    files = {"file": (path.name, f, mime_type)}
                    data = {"messaging_product": "whatsapp"}
                    response = client.post(self.media_url, headers=self.headers, data=data, files=files)
                    response.raise_for_status()
                    result = response.json()
                    return MediaUploadResponse(success=True, media_id=result.get("id"))
        except Exception as exc:
            logger.error(f"Media upload error: {exc}", exc_info=True)
            return MediaUploadResponse(success=False, error_message=str(exc))

    async def upload_media_async(self, file_path: str, mime_type: Optional[str] = None) -> MediaUploadResponse:
        """Async media upload."""
        try:
            path = Path(file_path)
            if not path.exists():
                return MediaUploadResponse(success=False, error_message=f"File not found: {file_path}")

            if mime_type is None:
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    return MediaUploadResponse(success=False, error_message="Could not determine MIME type")

            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(file_path, "rb") as f:
                    files = {"file": (path.name, f, mime_type)}
                    data = {"messaging_product": "whatsapp"}
                    response = await client.post(self.media_url, headers=self.headers, data=data, files=files)
                    response.raise_for_status()
                    result = response.json()
                    return MediaUploadResponse(success=True, media_id=result.get("id"))
        except Exception as exc:
            logger.error(f"Media upload async error: {exc}", exc_info=True)
            return MediaUploadResponse(success=False, error_message=str(exc))
        
    def mark_as_read(self, message_id: str) -> MessageResponse:
        """Mark a WhatsApp message as read and return a structured response."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()

                # Parse API response safely
                try:
                    data = response.json()
                except ValueError:
                    data = {}

                logger.info(f"Message {message_id} marked as read")
                return MessageResponse.from_success(
                    message_id=message_id,
                    raw_response=data or {"status_code": response.status_code}
                )

        except httpx.HTTPStatusError as exc:
            # Graph API responded with an error status
            try:
                error_data = exc.response.json()
            except ValueError:
                error_data = {"error": {"message": exc.response.text}}

            logger.error(
                f"Failed to mark message {message_id} as read - HTTP {exc.response.status_code}",
                exc_info=True
            )
            return MessageResponse.from_api_response(error_data)

        except httpx.RequestError as exc:
            # Network issue
            logger.error(
                f"Network error while marking {message_id} as read: {exc}",
                exc_info=True
            )
            return MessageResponse.from_error(
                error_message=str(exc),
                raw_response={"exception_type": "RequestError"}
            )

        except Exception as exc:
            # Unexpected errors
            logger.error(
                f"Unexpected error while marking {message_id} as read: {exc}",
                exc_info=True
            )
            return MessageResponse.from_error(
                error_message=str(exc),
                raw_response={"exception_type": exc.__class__.__name__}
            )

    @staticmethod
    def validate_webhook_signature(payload: str, signature: str) -> bool:
        """Validate webhook signature from Meta."""
        if not Settings.WHATSAPP_APP_SECRET:
            logger.warning("WHATSAPP_APP_SECRET not set, skipping validation")
            return True
        
        expected_signature = hmac.new(
            Settings.WHATSAPP_APP_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    
    @staticmethod
    def validate_phone_number(phone: str) -> tuple[bool, str]:
        """Validate and clean a phone number for WhatsApp use."""
        cleaned = phone.replace(" ", "").replace("-", "")
        digits = cleaned[1:]
        if not digits.isdigit():
            return False, "Phone number must contain only digits"
        if not (7 <= len(digits) <= 15):
            return False, "Phone number must be 7-15 digits long"
        return True, cleaned



# Shared client instance
WHATSAPP_CLIENT = WhatsAppClient()