# app/whatsapp_service.py
import logging
from typing import Any, Dict
from .models import SMSTask
from utils.whatsapp import (
    WhatsAppClient, TextMessage, TemplateMessage, 
    MediaMessage, InteractiveMessage
    )  # adjust import paths

logger = logging.getLogger(__name__)

whatsapp_client = WhatsAppClient()  # Initialize your WhatsApp client here

class WhatsAppService:
    """
    Thin adapter that:
     - Converts MessageTask -> WhatsApp payload (supports advanced options)
     - Sends payloads using existing whatsapp_client/QuickSend wrappers
     - Normalizes responses to a dict with 'success' and 'message_id'
    """

    def build_payload_from_task(self, task: SMSTask) -> Dict[str, Any]:
        """
        Build the WhatsApp Cloud API payload from MessageTask instance and its options.
        Supported options (examples):
          - {"type": "text", "preview_url": False}
          - {"type": "template", "name": "invoice_template", "language": "en_US", "body_params": [...]}
          - {"type": "media", "media_type": "image", "media_id": "...", media_url: "...", "caption": "..."}
          - {"type": "interactive", "buttons":[...]}
        If options is empty, defaults to text message using message_body.
        """
        opts = getattr(task, "options", {}) or {}
        msg_type = opts.get("type", "text")

        if msg_type == "template":
            name = opts.get("name")
            language = opts.get("language", "rw_RW")
            tm = TemplateMessage(to=task.recipient, name=name, language=language)
            for p in opts.get("body_params", []):
                tm.add_body_param(p)
            for hp in opts.get("header_params", []):
                tm.add_header_param(hp)
            for btn in opts.get("button_params", []):
                # expecting items already in the right format or using ButtonBuilder
                tm.add_button_param(index=btn.get("index", 0), param=btn.get("param"), sub_type=btn.get("sub_type", "url"))
            return tm.build_payload()

        elif msg_type == "media":
            media_type = opts.get("media_type", "image")
            media_id = opts.get("media_id", None) 
            media_url = opts.get("media_url", None)
            filename = opts.get("filename", None)
            
            if not media_id and not media_url:
                raise ValueError("Media ID or URL must be provided for media messages")
            
            caption = opts.get("caption") or task.message_body
            mm = MediaMessage(to=task.recipient, media_type=media_type, 
            media_url=media_url, media_id=media_id, caption=caption,
            filename=filename)
            return mm.build_payload()

        elif msg_type == "interactive":
            body = opts.get("body", task.message_body)
            header = opts.get("header")
            footer = opts.get("footer")
            im = InteractiveMessage(to=task.recipient, body=body, header=header, footer=footer)
            for btn in opts.get("buttons", []):
                im.add_reply_button(btn.get("id"), btn.get("title"))
            return im.build_payload()

        else:
            # default / fallback: plain text
            tm = TextMessage(to=task.recipient, body=task.message_body, preview_url=opts.get("preview_url", False))
            return tm.build_payload()

    def summarize_response(self, response: Any) -> Dict[str, Any]:
        """
        Return a small serializable summary of the external response for logs.
        Implementation should map your client's response structure to simple keys.
        """
        if isinstance(response, dict):
            return {k: response.get(k) for k in ("message_id", "success", "error") if k in response}
        # attempt to extract attributes
        return {"raw_type": type(response).__name__}

    def send_raw(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a raw payload to WhatsApp. Uses your low-level client.
        Return dict: {"success": bool, "message_id": str|None, "raw": client_response, "error": str|None}
        """
        try:
            # If your whatsapp_client expects the same payload shape, call it directly:
            client_resp = whatsapp_client.send(payload)
            # Normalize - adapt to your client's response fields
            return {
                "success": getattr(client_resp, "success", True),
                "message_id": getattr(client_resp, "message_id", None) or getattr(client_resp, "id", None),
                "raw": getattr(client_resp, "raw_response", None),
            }
        except Exception as exc:
            logger.exception("WhatsAppService.send_raw failed")
            return {"success": False, "error": str(exc)}
