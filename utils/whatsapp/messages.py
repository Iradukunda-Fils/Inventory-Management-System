from ._model import WhatsAppClient, WHATSAPP_CLIENT as whatsapp_client
from .settings import Settings
from typing import Any, Callable, Dict, List, Optional, Union
from abc import ABC, abstractmethod
from celery import group
import logging
from .constants import MediaType
from ._parameters import TemplateParameterBuilder, ButtonBuilder
from ._model import MessageResponse
from celery.result import AsyncResult



logger = logging.getLogger(__name__)


# -----------------------------
# Base Message Abstraction
# -----------------------------
class WhatsAppMessage(ABC):
    """Enhanced base class with fluent API and callbacks."""

    client: WhatsAppClient = whatsapp_client

    def __init__(self, to: str, 
        client: Optional["WhatsAppClient"] = None
    ) -> None:
        self.to = to
        self._on_success: Optional[Callable] = None
        self._on_error: Optional[Callable] = None
        self._context: Dict[str, Any] = {}

        if client is not None:
            self.client = client

    @abstractmethod
    def build_payload(self) -> dict:
        """Build JSON payload for WhatsApp Cloud API."""

    def with_context(self, **kwargs) -> "WhatsAppMessage":
        """Add context data for callbacks (fluent API)."""
        self._context.update(kwargs)
        return self

    def on_success(self, callback: Callable[[MessageResponse, Dict], None]) -> "WhatsAppMessage":
        """Set success callback (fluent API)."""
        self._on_success = callback
        return self

    def on_error(self, callback: Callable[[MessageResponse, Dict], None]) -> "WhatsAppMessage":
        """Set error callback (fluent API)."""
        self._on_error = callback
        return self

    def apply_async_task_send(self, task_to_apply: Callable, countdown: int = 0, eta: Optional[Any] = None):
        """Queue message with Celery (fluent API)."""
        task_id = task_to_apply.apply_async(
            args=[self.build_payload(), self._context],
            countdown=countdown,
            eta=eta
        )
        return task_id

    def send_task(self, task_to_apply: Callable):
        task_id = task_to_apply.delay(
            self.build_payload(), self._context
            )
        return task_id

    def send(self) -> MessageResponse:
        """Direct sync send with callbacks."""
        response = self.client.send(self.build_payload())
        self._execute_callbacks(response)
        return response

    async def asend(self) -> MessageResponse:
        """Direct async send with callbacks."""
        response = await self.client.asend(self.build_payload())
        self._execute_callbacks(response)
        return response

    def _execute_callbacks(self, response: MessageResponse):
        """Execute registered callbacks."""
        try:
            if response.success and self._on_success:
                self._on_success(response, self._context)
            elif not response.success and self._on_error:
                self._on_error(response, self._context)
        except Exception as exc:
            logger.error(f"Callback execution error: {exc}", exc_info=True)


# -----------------------------
# Message Types
# -----------------------------
class TextMessage(WhatsAppMessage):
    """Enhanced text message with formatting helpers."""
    
    def __new__(cls, *args, **kwargs):
        if len(args) >= 2 and len(args[1]) > 4096:
            raise ValueError("Text message exceeds maximum length of 4096 characters")
        
        if 'body' in kwargs and len(kwargs['body']) > 4096:
            raise ValueError("Text message exceeds maximum length of 4096 characters")
        return super().__new__(cls)

    def __init__(self, to: str, body: str, preview_url: bool = False, 
        client: Optional["WhatsAppClient"] = None
        ) -> None:
        super().__init__(to, client)
        self.body = body
        self.preview_url = preview_url

    def build_payload(self):
        """ Build text message payload. """
        return {
            "messaging_product": "whatsapp",
            "to": self.to,
            "type": "text",
            "text": {"body": self.body, "preview_url": self.preview_url},
        }

    @classmethod
    def bold(cls, text: str) -> str:
        """Format text as bold."""
        return f"*{text}*"

    @classmethod
    def italic(cls, text: str) -> str:
        """Format text as italic."""
        return f"_{text}_"

    @classmethod
    def strikethrough(cls, text: str) -> str:
        """Format text as strikethrough."""
        return f"~{text}~"

    @classmethod
    def monospace(cls, text: str) -> str:
        """Format text as monospace."""
        return f"```{text}```"
    


class TemplateMessage(WhatsAppMessage):
    """Template message builder with support for body, header, and button parameters."""

    def __init__(self, to: str, name: str, language: str = "rw_RW", 
        client: Optional["WhatsAppClient"] = None
        ) -> None:
        super().__init__(to, client)
        self.name = name
        self.language = language
        self._body_params: List[Dict[str, Any]] = []
        self._header_params: List[Dict[str, Any]] = []
        self._button_params: List[Dict[str, Any]] = []

    # --- Body Methods ---
    def add_body_param(self, param: Dict[str, Any]) -> "TemplateMessage":
        self._body_params.append(param)
        return self

    def add_body_text(self, text: str) -> "TemplateMessage":
        return self.add_body_param(TemplateParameterBuilder.text(text))

    # --- Header Methods ---
    def add_header_param(self, param: Dict[str, Any]) -> "TemplateMessage":
        self._header_params.append(param)
        return self

    def add_header_image(self, media_id: str = None, link: str = None) -> "TemplateMessage":
        return self.add_header_param(TemplateParameterBuilder.image(media_id, link))

    def add_header_video(self, media_id: str = None, link: str = None) -> "TemplateMessage":
        return self.add_header_param(TemplateParameterBuilder.video(media_id, link))

    def add_header_document(self, media_id: str = None, link: str = None, filename: Optional[str] = None) -> "TemplateMessage":
        return self.add_header_param(TemplateParameterBuilder.document(media_id, link, filename))

    def add_header_text(self, text: str) -> "TemplateMessage":
        return self.add_header_param(TemplateParameterBuilder.text(text))

    # --- Button Methods ---
    def add_button_param(self, index: int, param: Dict[str, Any], sub_type: str = "url") -> "TemplateMessage":
        self._button_params.append({
            "type": "button",
            "sub_type": sub_type,
            "index": str(index),
            "parameters": [param]
        })
        return self

    def add_url_button(self, index: int, url: str, title: str) -> "TemplateMessage":
        return self.add_button_param(index, ButtonBuilder.url_button(url, title), "url")

    def add_call_button(self, index: int, phone: str, title: str) -> "TemplateMessage":
        return self.add_button_param(index, ButtonBuilder.call_button(phone, title), "call")

    def add_copy_code_button(self, index: int, code: str) -> "TemplateMessage":
        return self.add_button_param(index, ButtonBuilder.copy_code_button(code), "copy_code")
    
    def add_coupon_code_button(self, index: int, exam_code: str) -> "TemplateMessage":
        return self.add_button_param(index, ButtonBuilder.coupon_code(exam_code), "copy_code")

    # --- Payload ---
    def build_payload(self):
        components = []
        if self._header_params:
            components.append({"type": "header", "parameters": self._header_params})
        if self._body_params:
            components.append({"type": "body", "parameters": self._body_params})
        if self._button_params:
            components.extend(self._button_params)

        return {
            "messaging_product": "whatsapp",
            "to": self.to,
            "type": "template",
            "template": {
                "name": self.name,
                "language": {"code": self.language},
                "components": components,
            },
        }


class MediaMessage(WhatsAppMessage):
    """Enhanced media message with file upload support."""
    def __init__(
        self, 
        to: str, 
        media_type: Union[MediaType, str], 
        media_id: Optional[str] = None, 
        media_url: Optional[str] = None, 
        caption: Optional[str] = None, 
        filename: Optional[str] = None,
        client: Optional["WhatsAppClient"] = None
    ) -> None:
        super().__init__(to, client)

        self.media_type = media_type.value if isinstance(media_type, MediaType) else media_type
        self.media_id = media_id
        self.media_url = media_url
        self.caption = caption
        self.filename = filename

        # --- Validation rules ---
        if caption and len(caption) > 1024:
            raise ValueError("Caption exceeds maximum length of 1024 characters")

        if not media_id and not media_url:
            raise ValueError("Either media_id or media_url must be provided")

        if self.media_type == MediaType.DOCUMENT.value and not filename:
            raise ValueError("Document messages require a filename")

        if filename and self.media_type != MediaType.DOCUMENT.value:
            raise ValueError("Filename is only valid for documents")

    @classmethod
    def from_file(
        cls, 
        to: str, 
        file_path: str, 
        media_type: Union[MediaType, str], 
        caption: Optional[str] = None
    ) -> "MediaMessage":
        """Create media message from file (auto-uploads)."""

        upload_result = cls.client.upload_media(file_path)
        if not upload_result.success:
            raise ValueError(f"Failed to upload media: {upload_result.error_message}")

        return cls(to, media_type, media_id=upload_result.media_id, caption=caption)

    @classmethod
    async def from_file_async(
        cls, 
        to: str, 
        file_path: str, 
        media_type: Union[MediaType, str], 
        caption: Optional[str] = None
    ) -> "MediaMessage":
        """Create media message from file asynchronously."""

        upload_result = await cls.client.upload_media_async(file_path)
        if not upload_result.success:
            raise ValueError(f"Failed to upload media: {upload_result.error}")

        return cls(to, media_type, media_id=upload_result.media_id, caption=caption)

    def build_payload(self) -> Dict[str, Any]:
        media: Dict[str, Any] = {"id": self.media_id} if self.media_id else {"link": self.media_url}

        if self.caption:
            media["caption"] = self.caption
        if self.filename and self.media_type == MediaType.DOCUMENT.value:
            media["filename"] = self.filename

        return {
            "messaging_product": "whatsapp",
            "to": self.to,
            "type": self.media_type,
            self.media_type: media,
        }



class InteractiveMessage(WhatsAppMessage):
    """Enhanced interactive message with builder pattern."""

    MAX_BODY_LENGTH = 1024
    MAX_HEADER_LENGTH = 60
    MAX_FOOTER_LENGTH = 60
    MAX_BUTTONS = 3

    def __init__(self, to: str, body: str, 
        header: Optional[str] = None, 
        footer: Optional[str] = None,
        client: Optional["WhatsAppClient"] = None
    ) -> None:
        
        super().__init__(to, client)

        if not body:
            raise ValueError("Body text is required for interactive messages")
        if len(body) > self.MAX_BODY_LENGTH:
            raise ValueError("Body text exceeds maximum length of %d characters" % self.MAX_BODY_LENGTH)

        if header and len(header) > self.MAX_HEADER_LENGTH:
            raise ValueError("Header exceeds maximum length of %d characters" % self.MAX_HEADER_LENGTH)

        if footer and len(footer) > self.MAX_FOOTER_LENGTH:
            raise ValueError("Footer exceeds maximum length of %d characters" % self.MAX_FOOTER_LENGTH)

        self.header = header
        self.body = body
        self.footer = footer
        self._buttons: List[Dict[str, Any]] = []

    def add_reply_button(self, button_id: str, title: str) -> "InteractiveMessage":
        """Add a reply button (quick reply)."""
        if len(self._buttons) >= self.MAX_BUTTONS:
            raise ValueError("Maximum %d reply buttons allowed" % self.MAX_BUTTONS)

        button = {
            "type": "reply",
            "reply": {
                "id": button_id,
                "title": title[:20],  # WhatsApp button title max = 20 chars
            },
        }
        self._buttons.append(button)
        return self

    def build_payload(self) -> Dict[str, Any]:
        interactive: Dict[str, Any] = {
            "type": "button",
            "body": {"text": self.body},
            "action": {"buttons": self._buttons},
        }

        if self.header:
            interactive["header"] = {"type": "text", "text": self.header}
        
        if self.footer:
            interactive["footer"] = {"text": self.footer}

        return {
            "messaging_product": "whatsapp",
            "to": self.to,
            "type": "interactive",
            "interactive": interactive,
        }



class ListMessage(WhatsAppMessage):
    """Interactive list message."""

    def __init__(self, to: str, body: str, 
        button_text: str, header: Optional[str] = None, 
        footer: Optional[str] = None, 
        client: Optional["WhatsAppClient"] = None
    ) -> None:
        super().__init__(to, client)
        
        self.header = header
        self.body = body
        self.footer = footer
        self.button_text = button_text
        self._sections: List[Dict[str, Any]] = []

    def add_section(self, title: str, rows: List[Dict[str, str]]) -> "ListMessage":
        """Add section with rows (fluent API)."""
        self._sections.append({"title": title, "rows": rows})
        return self

    def add_row_to_last_section(self, row_id: str, title: str, description: Optional[str] = None) -> "ListMessage":
        """Quick add row to last section."""
        if not self._sections:
            raise ValueError("No sections available. Add a section first.")
        
        row = {"id": row_id, "title": title}
        if description:
            row["description"] = description
        
        self._sections[-1]["rows"].append(row)
        return self

    def build_payload(self):
        interactive: Dict[str, Any] = {
            "type": "list",
            "body": {"text": self.body},
            "action": {
                "button": self.button_text,
                "sections": self._sections
            }
        }

        if self.header:
            interactive["header"] = {"type": "text", "text": self.header}
        
        if self.footer:
            interactive["footer"] = {"text": self.footer}

        return {
            "messaging_product": "whatsapp",
            "to": self.to,
            "type": "interactive",
            "interactive": interactive,
        }


class LocationMessage(WhatsAppMessage):
    def __init__(self, to: str, latitude: float,
        longitude: float, name: str, address: str,
        client: Optional["WhatsAppClient"] = None
    ) -> None:
        
        super().__init__(to, client)
        
        self.latitude = latitude
        self.longitude = longitude
        self.name = name
        self.address = address

    def build_payload(self):
        return {
            "messaging_product": "whatsapp",
            "to": self.to,
            "type": "location",
            "location": {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "name": self.name,
                "address": self.address,
            },
        }


class ContactMessage(WhatsAppMessage):
    """Enhanced contact message with builder."""

    def __init__(self, to: str, client: Optional["WhatsAppClient"] = None) -> None:
        super().__init__(to, client)
        self._contacts: List[Dict[str, Any]] = []

    def add_contact(self, contact: Dict[str, Any]) -> "ContactMessage":
        """Add contact (fluent API)."""
        self._contacts.append(contact)
        return self

    def add_simple_contact(self, name: str, phone: str, formatted_name: Optional[str] = None) -> "ContactMessage":
        """Quick add contact with name and phone."""
        contact = {
            "name": {"formatted_name": formatted_name or name, "first_name": name},
            "phones": [{"phone": phone, "type": "CELL"}]
        }
        return self.add_contact(contact)

    def build_payload(self):
        return {
            "messaging_product": "whatsapp",
            "to": self.to,
            "type": "contacts",
            "contacts": self._contacts,
        }


# -----------------------------
# Batch Operations
# -----------------------------
class BatchMessageSender:
    """Send messages to multiple recipients efficiently."""

    def __init__(self):
        self.messages: List[WhatsAppMessage] = []

    def add(self, message: WhatsAppMessage) -> "BatchMessageSender":
        """Add message to batch (fluent API)."""
        if len(self.messages) >= Settings.MAX_BATCH_SIZE:
            raise ValueError(f"Batch size limit ({Settings.MAX_BATCH_SIZE}) exceeded")
        self.messages.append(message)
        return self

    def send(self) -> List[MessageResponse]:
        """Send all messages synchronously."""
        responses = []
        for msg in self.messages:
            responses.append(msg.send())
        return responses

    def send_group_of_tasks(self, task_to_apply: Callable) -> AsyncResult:
        """Send all messages as Celery group."""
        job = group(task_to_apply.s(msg.build_payload()) for msg in self.messages)
        return job.apply_async()

    def clear(self) -> "BatchMessageSender":
        """Clear all messages."""
        self.messages.clear()
        return self


# -----------------------------
# Quick Send Helpers
# -----------------------------
class QuickSend:
    """Convenience methods for common messaging patterns."""

    @staticmethod
    def text(to: str, message: str, preview_url: bool = False) -> MessageResponse:
        """Quick send text message."""
        return TextMessage(to, message, preview_url).send()

    @staticmethod
    def template(to: str, template_name: str, 
        body_params: Optional[List[str]] = None, 
        language: str = "rw_RW"
    ) -> MessageResponse:
        """Quick send template with text parameters."""
        msg = TemplateMessage(to, template_name, language)
        if body_params:
            for param in body_params:
                msg.add_body_text(param)
        return msg.send()

    @staticmethod
    def image(to: str, media_id: str, caption: Optional[str] = None) -> MessageResponse:
        """Quick send image."""
        return MediaMessage(to, MediaType.IMAGE, media_id=media_id, caption=caption).send()

    @staticmethod
    def document(to: str, media_id: str, filename: Optional[str] = None, 
                 caption: Optional[str] = None) -> MessageResponse:
        """Quick send document."""
        return MediaMessage(to, MediaType.DOCUMENT, media_id=media_id, 
                          caption=caption, filename=filename).send()

    @staticmethod
    def location(to: str, lat: float, lon: float, name: str, address: str) -> MessageResponse:
        """Quick send location."""
        return LocationMessage(to, lat, lon, name, address).send()

    @staticmethod
    def buttons(to: str, body: str, button_configs: List[tuple], 
                header: Optional[str] = None, footer: Optional[str] = None) -> MessageResponse:
        """Quick send interactive buttons. button_configs: [(id, title), ...]"""
        msg = InteractiveMessage(to, body, header, footer)
        for btn_id, title in button_configs:
            msg.add_reply_button(btn_id, title)
        return msg.send()


__all__ = (
    "WhatsAppMessage",
    "TextMessage",
    "TemplateMessage",
    "MediaMessage",
    "InteractiveMessage",
    "ListMessage",
    "LocationMessage",
    "ContactMessage",
    "BatchMessageSender",
    "QuickSend",
)


