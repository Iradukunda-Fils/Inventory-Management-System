from typing import Dict, Any, Optional


# -----------------------------
# Utility Builders
# -----------------------------
class TemplateParameterBuilder:
    """Helper to build template parameters."""
    
    @staticmethod
    def text(value: str) -> Dict[str, str]:
        return {"type": "text", "text": str(value)}

    @staticmethod
    def currency(code: str, amount: int, fallback: str) -> Dict[str, Any]:
        return {"type": "currency", "currency": {"code": code, "amount_1000": amount, "fallback_value": fallback}}

    @staticmethod
    def date_time(timestamp: int) -> Dict[str, Any]:
        return {"type": "date_time", "date_time": {"fallback_value": str(timestamp)}}

    @staticmethod
    def image(media_id: str = None, link: str = None) -> Dict[str, Any]:
        if not media_id and not link:
            raise ValueError("Either media_id or link must be provided")
        return {"type": "image", "image": {"id": media_id} if media_id else {"link": link}}

    @staticmethod
    def video(media_id: str = None, link: str = None) -> Dict[str, Any]:
        if not media_id and not link:
            raise ValueError("Either media_id or link must be provided")
        return {"type": "video", "video": {"id": media_id} if media_id else {"link": link}}

    @staticmethod
    def document(media_id: str = None, link: str = None, filename: Optional[str] = None) -> Dict[str, Any]:
        if not media_id and not link:
            raise ValueError("Either media_id or link must be provided")
        doc = {"id": media_id} if media_id else {"link": link}
        if filename:
            doc["filename"] = filename
        return {"type": "document", "document": doc}



# -----------------------------
# Button Builders
# ----------------------------
class ButtonBuilder:
    """Helper to build interactive buttons."""

    @staticmethod
    def reply_button(button_id: str, title: str) -> Dict[str, Any]:
        if len(title) > 20:
            raise ValueError("Button title must be 20 characters or fewer")
        return {"type": "reply", "reply": {"id": button_id, "title": title}}

    @staticmethod
    def url_button(url: str, title: str) -> Dict[str, Any]:
        return {"type": "url", "url": url, "text": title}
        # return {"type": "text", "text": url if url else title}  # can be adapted to WhatsApp "url"

    @staticmethod
    def call_button(phone: str, title: str) -> Dict[str, Any]:
        return {"type": "phone_number", "phone_number": phone, "text": title}
    
    @staticmethod
    def copy_code_button(code: str) -> Dict[str, Any]:
        return {"type": "text", "text": code}  # can be adapted to WhatsApp "copy_code"
    
    @staticmethod
    def coupon_code(code: str) -> Dict[str, Any]:
        return {"type": "coupon_code", "coupon_code": code}  # can be adapted to WhatsApp "copy_code"
    