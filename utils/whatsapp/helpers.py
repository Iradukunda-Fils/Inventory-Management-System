from typing import Any, Dict, List, Optional
from django.core.exceptions import ValidationError
from .constants import WhatsAppMessageType
from ._parameters import TemplateParameterBuilder, ButtonBuilder


def generate_whatsapp_options(
    msg_type: str = WhatsAppMessageType.TEXT,
    message_body: str = "",
    *,
    preview_url: bool = False,
    template_name: Optional[str] = None,
    language: str = "rw_RW",
    body_params: Optional[List[Any]] = None,
    header_params: Optional[List[Any]] = None,
    button_params: Optional[List[Dict[str, Any]]] = None,
    media_type: Optional[str] = None,
    media_id: Optional[str] = None,
    media_url: Optional[str] = None,
    caption: Optional[str] = None,
    filename: Optional[str] = None,
    header: Optional[str] = None,
    footer: Optional[str] = None,
    buttons: Optional[List[Dict[str, Any]]] = None,
    list_button_text: Optional[str] = None,
    list_sections: Optional[List[Dict[str, Any]]] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    location_name: Optional[str] = None,
    address: Optional[str] = None,
    contacts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generates a clean, validated, and structured WhatsApp message options dictionary.
    This dictionary is serializable for DB storage and compatible with WhatsAppService.build_payload_from_task().

    Supported message types:
    - text
    - template
    - media
    - interactive
    - list
    - location
    - contacts
    """

    msg_type = msg_type.lower().strip()
    options: Dict[str, Any] = {"type": msg_type}

    # -----------------------------
    # TEXT MESSAGE
    # -----------------------------

    match msg_type:
        case  WhatsAppMessageType.TEXT:
            if not message_body:
                raise ValidationError("Text message requires a message body.")
            options.update({
                "body": message_body,
                "preview_url": preview_url,
            })

        # -----------------------------
        # TEMPLATE MESSAGE
        # -----------------------------
        case WhatsAppMessageType.TEMPLATE:
            if not template_name:
                raise ValidationError("Template name is required for template messages.")

            options.update({
                "name": template_name,
                "language": language,
                "body_params": [],
                "header_params": [],
                "button_params": [],
            })

            # Body Parameters
            for param in body_params or []:
                if isinstance(param, str):
                    options["body_params"].append(TemplateParameterBuilder.text(param))
                elif isinstance(param, dict):
                    options["body_params"].append(param)
                else:
                    raise ValidationError(f"Invalid body parameter type: {type(param).__name__}")

            # Header Parameters
            for hp in header_params or []:
                if isinstance(hp, str):
                    options["header_params"].append(TemplateParameterBuilder.text(hp))
                elif isinstance(hp, dict):
                    options["header_params"].append(hp)
                else:
                    raise ValidationError(f"Invalid header parameter type: {type(hp).__name__}")

            # Button Parameters
            for btn in button_params or []:
                sub_type = btn.get("sub_type", "url").lower()
                param = btn.get("param")
                title = btn.get("title", "Open")

                if sub_type == "url":
                    built_param = ButtonBuilder.url_button(param, title)
                elif sub_type == "phone_number":
                    built_param = ButtonBuilder.call_button(param, title)
                elif sub_type == "copy_code":
                    built_param = ButtonBuilder.copy_code_button(param)
                elif sub_type == "coupon_code":
                    built_param = ButtonBuilder.coupon_code(param)
                else:
                    raise ValidationError(f"Unsupported button sub_type: {sub_type}")

                options["button_params"].append({
                    "index": btn.get("index", 0),
                    "param": built_param,
                    "sub_type": sub_type,
                })

        # -----------------------------
        # MEDIA MESSAGE
        # -----------------------------
        case WhatsAppMessageType.MEDIA:
            if not (media_id or media_url):
                raise ValidationError("Media messages require either 'media_id' or 'media_url'.")

            options.update({
                "media_type": media_type or "image",
                "media_id": media_id,
                "media_url": media_url,
                "caption": caption or message_body,
                "filename": filename,
            })

        # -----------------------------
        # INTERACTIVE BUTTON MESSAGE
        # -----------------------------
        case WhatsAppMessageType.INTERACTIVE:
            if not message_body:
                raise ValidationError("Interactive message requires a body.")

            organized_buttons: List[Dict[str, Any]] = []
            for btn in buttons or []:
                b_type = btn.get("type", "reply").lower()
                title = btn.get("title", "")
                if b_type == "reply":
                    built = ButtonBuilder.reply_button(btn.get("id"), title)
                elif b_type == "url":
                    built = ButtonBuilder.url_button(btn.get("url"), title)
                elif b_type == "phone_number":
                    built = ButtonBuilder.call_button(btn.get("phone"), title)
                elif b_type == "copy_code":
                    built = ButtonBuilder.copy_code_button(btn.get("code"))
                elif b_type == "coupon_code":
                    built = ButtonBuilder.coupon_code(btn.get("code"))
                else:
                    raise ValidationError(f"Unsupported button type: {b_type}")
                organized_buttons.append(built)

            options.update({
                "body": message_body,
                "header": header,
                "footer": footer,
                "buttons": organized_buttons,
            })

        # -----------------------------
        # LIST MESSAGE
        # -----------------------------
        case WhatsAppMessageType.LIST:
            if not list_button_text or not list_sections:
                raise ValidationError("List message requires 'list_button_text' and 'list_sections'.")

            options.update({
                "body": message_body,
                "header": header,
                "footer": footer,
                "button_text": list_button_text,
                "sections": list_sections,
            })

        # -----------------------------
        # LOCATION MESSAGE
        # -----------------------------
        case WhatsAppMessageType.LOCATION:
            if not all([latitude, longitude, location_name, address]):
                raise ValidationError("Location messages require latitude, longitude, name, and address.")
            options.update({
                "latitude": latitude,
                "longitude": longitude,
                "name": location_name,
                "address": address,
            })

        # -----------------------------
        # CONTACT MESSAGE
        # -----------------------------
        case WhatsAppMessageType.CONTACT:
            if not contacts:
                raise ValidationError("Contacts message requires at least one contact.")
            options.update({
                "contacts": contacts,
            })

        # -----------------------------
        # UNSUPPORTED MESSAGE TYPE
        # -----------------------------
        case _:
            raise ValidationError(f"Unsupported message type: '{msg_type}'")

    return options
