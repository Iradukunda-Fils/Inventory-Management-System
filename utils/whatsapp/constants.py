from enum import Enum, StrEnum
# -----------------------------
# Enums for Type Safety
# -----------------------------
class MediaType(Enum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STICKER = "sticker"


class ButtonType(StrEnum):
    REPLY = "reply"
    CALL = "call"
    URL = "url"

class WhatsAppMessageType(str, Enum):
    TEXT = "text"
    TEMPLATE = "template"
    MEDIA = "media"
    INTERACTIVE = "interactive"
    LIST = "list"
    LOCATION = "location"
    CONTACT = "contact"

