from django.conf import settings
# from pathlib import Path
# from dotenv import load_dotenv

# load_environment = load_dotenv(Path("../.env").resolve())

# if load_environment is False:
#     raise ImportError("The .env file not found!")

# -----------------------------
# Settings
# -----------------------------
class Settings:
    """ Centralized settings configurations. """
    GRAPH_API_URL: str = getattr(settings, "GRAPH_API_URL", "https://graph.facebook.com/v20.0")
    WHATSAPP_PHONE_ID: str = getattr(settings, "WHATSAPP_PHONE_ID", "")
    WHATSAPP_TOKEN: str = getattr(settings, "WHATSAPP_TOKEN", "")
    WHATSAPP_APP_SECRET: str = getattr(settings, "WHATSAPP_APP_SECRET", "")
    WHATSAPP_BUSINESS_ID: str = getattr(settings, "WHATSAPP_BUSINESS_ID", "")
    DEFAULT_TIMEOUT: float = getattr(settings, "WHATSAPP_DEFAULT_TIMEOUT", 30.0)
    MAX_BATCH_SIZE: int = getattr(settings, "WHATSAPP_MAX_BATCH_SIZE", 100)
    MAX_TEXT_LENGTH: int = getattr(settings, "WHATSAPP_MAX_TEXT_LENGTH", 4096)

    @classmethod
    def headers(cls) -> dict:
        return {"Authorization": f"Bearer {cls.WHATSAPP_TOKEN}"}

    @classmethod
    def validate(cls) -> bool:
        """Validate required settings are present."""
        if not cls.WHATSAPP_PHONE_ID or not cls.WHATSAPP_TOKEN:
            raise ValueError("WHATSAPP_PHONE_ID and WHATSAPP_TOKEN must be set")
        return True

# # -----------------------------
# # Settings
# # -----------------------------
# class Settings:
#     """ Centralized settings configurations. """
#     GRAPH_API_URL: str = "https://graph.facebook.com/v20.0"
#     WHATSAPP_PHONE_ID: str = os.getenv("WHATSAPP_PHONE_ID", "")
#     WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
#     WHATSAPP_APP_SECRET: str = os.getenv("WHATSAPP_APP_SECRET", "")
#     WHATSAPP_BUSINESS_ID: str = os.getenv("WHATSAPP_BUSINESS_ID", "")
#     DEFAULT_TIMEOUT: float = 30.0
#     MAX_BATCH_SIZE: int = 100
#     MAX_TEXT_LENGTH: int = 4096

#     @classmethod
#     def headers(cls) -> dict:
#         return {
#             "Authorization": f"Bearer {cls.WHATSAPP_TOKEN}",
#             "Content-Type": "application/json"
#             }

#     @classmethod
#     def validate(cls) -> bool:
#         """Validate required settings are present."""
#         if not cls.WHATSAPP_PHONE_ID or not cls.WHATSAPP_TOKEN:
#             raise ValueError("WHATSAPP_PHONE_ID and WHATSAPP_TOKEN must be set")
#         return True