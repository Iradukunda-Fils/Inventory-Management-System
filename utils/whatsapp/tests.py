"""
Comprehensive Unit Tests for WhatsApp Message Sender Module

Run with: pytest test_whatsapp.py -v
or: python -m pytest test_whatsapp.py -v --cov=whatsapp_module
"""

from django.core.exceptions import ValidationError
from _parameters import TemplateParameterBuilder, ButtonBuilder
from .helpers import generate_whatsapp_options
from unittest.mock import Mock, patch
import httpx
import pytest
import json

# Assuming the module is named whatsapp_module.py
# Adjust import based on your actual module name
try:
    from . import (
        Settings,
        WhatsAppClient,
        MessageResponse,
        MediaUploadResponse,
        TextMessage,
        TemplateMessage,
        MediaMessage,
        InteractiveMessage,
        ListMessage,
        LocationMessage,
        ContactMessage,
        BatchMessageSender,
        QuickSend,
        TemplateParameterBuilder,
        ButtonBuilder,
        MediaType,
        whatsapp_client,
    )
except ImportError:
    # If module not found, skip tests
    pytest.skip("WhatsApp module not found", allow_module_level=True)


# -----------------------------
# Fixtures
# -----------------------------
@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("WHATSAPP_PHONE_ID", "123456789")
    monkeypatch.setenv("WHATSAPP_TOKEN", "test_token_123")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "test_secret")
    monkeypatch.setenv("WHATSAPP_BUSINESS_ID", "business_123")
    # Force reload settings
    Settings.WHATSAPP_PHONE_ID = "123456789"
    Settings.WHATSAPP_TOKEN = "test_token_123"
    Settings.WHATSAPP_APP_SECRET = "test_secret"
    Settings.WHATSAPP_BUSINESS_ID = "business_123"


@pytest.fixture
def valid_phone():
    """Valid phone number for testing."""
    return "+250788123456"


@pytest.fixture
def mock_success_response():
    """Mock successful API response."""
    return {
        "messaging_product": "whatsapp",
        "contacts": [{"input": "+250788123456", "wa_id": "250788123456"}],
        "messages": [{"id": "wamid.test123"}]
    }


@pytest.fixture
def mock_error_response():
    """Mock error API response."""
    return {
        "error": {
            "message": "Unknown response format",
            "type": "OAuthException",
            "code": 100,
            "fbtrace_id": "test_trace"
        }
    }


# -----------------------------
# Settings Tests
# -----------------------------
class TestSettings:
    """Test Settings class."""
    
    def test_settings_validation_success(self, mock_env_vars):
        """Test successful settings validation."""
        assert Settings.validate() is True
    
    def test_settings_validation_missing_phone_id(self, monkeypatch):
        """Test validation fails without PHONE_ID."""
        monkeypatch.setenv("WHATSAPP_PHONE_ID", "")
        Settings.WHATSAPP_PHONE_ID = ""
        
        with pytest.raises(ValueError, match="WHATSAPP_PHONE_ID"):
            Settings.validate()
    
    def test_settings_validation_missing_token(self, monkeypatch):
        """Test validation fails without TOKEN."""
        monkeypatch.setenv("WHATSAPP_PHONE_ID", "123")
        monkeypatch.setenv("WHATSAPP_TOKEN", "")
        Settings.WHATSAPP_PHONE_ID = "123"
        Settings.WHATSAPP_TOKEN = ""
        
        with pytest.raises(ValueError, match="WHATSAPP_TOKEN"):
            Settings.validate()
    
    def test_settings_headers(self, mock_env_vars):
        """Test headers generation."""
        headers = Settings.headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token_123"
        assert headers["Content-Type"] == "application/json"


# -----------------------------
# Response Models Tests
# -----------------------------
class TestMessageResponse:
    """Test MessageResponse dataclass."""
    
    def test_from_api_response_success(self, mock_success_response):
        """Test parsing successful API response."""
        response = MessageResponse.from_api_response(mock_success_response)
        
        assert response.success is True
        assert response.message_id == "wamid.test123"
        assert response.error_message is None
        assert response.raw_response == mock_success_response
    
    def test_from_api_response_error(self, mock_error_response):
        """Test parsing error API response."""
        response = MessageResponse.from_api_response(mock_error_response)
        
        assert response.success is False
        assert response.error_message == "Unknown response format"
        assert response.error_code == 100
        assert response.message_id is None
    
    def test_from_api_response_unknown_format(self):
        """Test parsing unknown response format."""
        response = MessageResponse.from_api_response({"unknown": "format"})
        
        assert response.success is False
        assert response.error_message == "Unknown response format"
    
    def test_message_response_str(self):
        """Test string representation."""
        success_resp = MessageResponse(success=True, message_id="msg123")
        error_resp = MessageResponse(success=False, error_message="Test error", error_code=400)
        
        assert "success=True" in str(success_resp)
        assert "msg123" in str(success_resp)
        assert "success=False" in str(error_resp)
        assert "Test error" in str(error_resp)


class TestMediaUploadResponse:
    """Test MediaUploadResponse dataclass."""
    
    def test_success_upload(self):
        """Test successful upload response."""
        response = MediaUploadResponse(success=True, media_id="media123")
        assert response.success is True
        assert response.media_id == "media123"
        assert "media123" in str(response)
    
    def test_failed_upload(self):
        """Test failed upload response."""
        response = MediaUploadResponse(success=False, error_message="File not found")
        assert response.success is False
        assert "File not found" in str(response)


# -----------------------------
# WhatsApp Client Tests
# -----------------------------
class TestWhatsAppClient:
    """Test WhatsAppClient class."""
    
    def test_client_initialization(self, mock_env_vars):
        """Test client initialization."""
        client = WhatsAppClient()
        assert client.base_url.endswith("/messages")
        assert client.media_url.endswith("/media")
        assert "Authorization" in client.headers
    
    @patch('httpx.Client')
    def test_send_success(self, mock_client, mock_env_vars, mock_success_response):
        """Test successful message send."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_success_response
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        client = WhatsAppClient()
        payload = {"messaging_product": "whatsapp", "to": "+250788123456"}
        response = client.send(payload)
        
        assert response.success is True
        assert response.message_id == "wamid.test123"
    
    @patch('httpx.Client')
    def test_send_http_error(self, mock_client, mock_env_vars, mock_error_response):
        """Test send with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = mock_error_response
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        client = WhatsAppClient()
        payload = {"messaging_product": "whatsapp"}
        response = client.send(payload)
        
        assert response.success is False
        assert response.error_message is not None
    
    @patch('httpx.Client')
    def test_send_network_error(self, mock_client, mock_env_vars):
        """Test send with network error."""
        mock_client.return_value.__enter__.return_value.post.side_effect = \
            httpx.RequestError("Network error")
        
        client = WhatsAppClient()
        response = client.send({"test": "payload"})
        
        assert response.success is False
        assert "Network error" in response.error_message
    
    def test_validate_phone_number_valid(self):
        """Test valid phone number validation."""
        valid, result = WhatsAppClient.validate_phone_number("+250788123456")
        assert valid is True
        assert result == "+250788123456"
    
    def test_validate_phone_number_with_spaces(self):
        """Test phone number validation with spaces."""
        valid, result = WhatsAppClient.validate_phone_number("+250 788 123 456")
        assert valid is True
        assert result == "+250788123456"
    
    def test_validate_phone_number_invalid_no_plus(self):
        """Test invalid phone number without +."""
        valid, result = WhatsAppClient.validate_phone_number("250788123456")
        assert valid is False
        assert "must start with +" in result
    
    def test_validate_phone_number_invalid_chars(self):
        """Test invalid phone number with letters."""
        valid, result = WhatsAppClient.validate_phone_number("+250ABC123")
        assert valid is False
        assert "only digits" in result
    
    def test_validate_phone_number_too_short(self):
        """Test phone number too short."""
        valid, result = WhatsAppClient.validate_phone_number("+12345")
        assert valid is False
        assert "7-15 digits" in result
    
    def test_validate_webhook_signature_valid(self, mock_env_vars):
        """Test valid webhook signature."""
        payload = '{"test": "data"}'
        # Generate valid signature
        import hmac
        import hashlib
        signature = hmac.new(
            Settings.WHATSAPP_APP_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        is_valid = WhatsAppClient.validate_webhook_signature(payload, signature)
        assert is_valid is True
    
    def test_validate_webhook_signature_with_prefix(self, mock_env_vars):
        """Test webhook signature with sha256= prefix."""
        payload = '{"test": "data"}'
        import hmac
        import hashlib
        signature = "sha256=" + hmac.new(
            Settings.WHATSAPP_APP_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        is_valid = WhatsAppClient.validate_webhook_signature(payload, signature)
        assert is_valid is True
    
    def test_validate_webhook_signature_invalid(self, mock_env_vars):
        """Test invalid webhook signature."""
        payload = '{"test": "data"}'
        signature = "invalid_signature"
        
        is_valid = WhatsAppClient.validate_webhook_signature(payload, signature)
        assert is_valid is False
    
    @patch('httpx.Client')
    def test_mark_as_read_success(self, mock_client, mock_env_vars):
        """Test marking message as read."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        client = WhatsAppClient()
        result = client.mark_as_read("msg123")
        
        assert result is True
    
    @patch('httpx.Client')
    def test_mark_as_read_failure(self, mock_client, mock_env_vars):
        """Test marking message as read failure."""
        mock_client.return_value.__enter__.return_value.post.side_effect = \
            Exception("Error")
        
        client = WhatsAppClient()
        result = client.mark_as_read("msg123")
        
        assert result is False


# -----------------------------
# Builder Tests
# -----------------------------
class TestTemplateParameterBuilder:
    """Test TemplateParameterBuilder class."""

    def test_text_parameter(self):
        """Test text parameter creation."""
        param = TemplateParameterBuilder.text("Hello")
        assert param == {"type": "text", "text": "Hello"}

    def test_text_parameter_converts_number(self):
        """Test text parameter converts numbers."""
        param = TemplateParameterBuilder.text(123)
        assert param == {"type": "text", "text": "123"}

    def test_currency_parameter(self):
        """Test currency parameter creation."""
        param = TemplateParameterBuilder.currency("USD", 50000, "$50")
        assert param["type"] == "currency"
        assert param["currency"]["code"] == "USD"
        assert param["currency"]["amount_1000"] == 50000
        assert param["currency"]["fallback_value"] == "$50"

    def test_date_time_parameter(self):
        """Test date_time parameter creation."""
        param = TemplateParameterBuilder.date_time(1696118400)
        assert param == {"type": "date_time", "date_time": {"fallback_value": "1696118400"}}

    def test_image_with_id(self):
        """Test image parameter with media ID."""
        param = TemplateParameterBuilder.image(media_id="img123")
        assert param == {"type": "image", "image": {"id": "img123"}}

    def test_video_with_id(self):
        """Test video parameter with media ID."""
        param = TemplateParameterBuilder.video(media_id="vid123")
        assert param == {"type": "video", "video": {"id": "vid123"}}

    def test_document_with_id(self):
        """Test document parameter creation without filename."""
        param = TemplateParameterBuilder.document(media_id="doc123")
        assert param == {"type": "document", "document": {"id": "doc123"}}

    def test_document_with_filename(self):
        """Test document parameter creation with filename."""
        param = TemplateParameterBuilder.document(media_id="doc123", filename="file.pdf")
        assert param == {"type": "document", "document": {"id": "doc123", "filename": "file.pdf"}}



class TestButtonBuilder:
    """Test ButtonBuilder class."""
    
    def test_reply_button(self):
        """Test reply button creation."""
        button = ButtonBuilder.reply_button("btn1", "Click Me")
        assert button["type"] == "reply"
        assert button["reply"]["id"] == "btn1"
        assert button["reply"]["title"] == "Click Me"
        
    def test_reply_button_title_too_long(self):
        """Test reply button with too long title."""
        with pytest.raises(ValueError, match="Button title must be 20 characters or fewer"):
            ButtonBuilder.reply_button("btn1", "This title is way too long")
            
    def test_url_button(self):
        """Test URL button creation."""
        button = ButtonBuilder.url_button("https://example.com", "Visit")
        assert button["type"] == "url"
        assert button["url"] == "https://example.com"

        
    def test_call_button(self):
        button = ButtonBuilder.call_button("+250788123456", "Call Us")
        assert button["type"] == "phone_number"
        assert button["phone_number"] == "+250788123456"



# -----------------------------
# Message Type Tests
# -----------------------------
class TestTextMessage:
    """Test TextMessage class."""
    
    def test_text_message_creation(self, mock_env_vars, valid_phone):
        """Test text message creation."""
        msg = TextMessage(valid_phone, "Hello World")
        assert msg.to == valid_phone
        assert msg.body == "Hello World"
        assert msg.preview_url is False
    
    def test_text_message_with_preview(self, mock_env_vars, valid_phone):
        """Test text message with URL preview."""
        msg = TextMessage(valid_phone, "Check https://example.com", preview_url=True)
        assert msg.preview_url is True
    
    def test_text_message_too_long(self, mock_env_vars, valid_phone):
        """Test text message exceeds max length."""
        long_text = "a" * 5000
        with pytest.raises(ValueError, match="Text message exceeds maximum length of %d characters" % Settings.MAX_TEXT_LENGTH):
            TextMessage(valid_phone, long_text)
    
    def test_text_message_build_payload(self, mock_env_vars, valid_phone):
        """Test text message payload building."""
        msg = TextMessage(valid_phone, "Test")
        payload = msg.build_payload()
        
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == valid_phone
        assert payload["type"] == "text"
        assert payload["text"]["body"] == "Test"
    
    def test_text_formatting_bold(self):
        """Test bold text formatting."""
        assert TextMessage.bold("Hello") == "*Hello*"
    
    def test_text_formatting_italic(self):
        """Test italic text formatting."""
        assert TextMessage.italic("Hello") == "_Hello_"
    
    def test_text_formatting_strikethrough(self):
        """Test strikethrough text formatting."""
        assert TextMessage.strikethrough("Hello") == "~Hello~"
    
    def test_text_formatting_monospace(self):
        """Test monospace text formatting."""
        assert TextMessage.monospace("code") == "```code```"
    
    def build_payload(self, mock_env_vars, valid_phone):
        """Test payload preview."""
        msg = TextMessage(valid_phone, "Test", preview_url=True)
        preview = msg.preview_payload()
        assert isinstance(preview, str)
        assert valid_phone in preview


# -----------------------------
# TemplateMessage Tests
# -----------------------------
class TestTemplateMessage:
    """Test TemplateMessage class."""

    def test_template_creation(self, mock_env_vars, valid_phone):
        """Test template message creation."""
        msg = TemplateMessage(valid_phone, "welcome_template")
        assert msg.name == "welcome_template"
        assert msg.language == "rw_RW"

    def test_template_with_custom_language(self, mock_env_vars, valid_phone):
        """Test template with custom language."""
        msg = TemplateMessage(valid_phone, "hello", language="en_US")
        assert msg.language == "en_US"

    def test_add_body_text(self, mock_env_vars, valid_phone):
        """Test adding body text parameters."""
        msg = TemplateMessage(valid_phone, "test")
        msg.add_body_text("John").add_body_text("Doe")

        assert len(msg._body_params) == 2
        assert msg._body_params[0]["text"] == "John"
        assert msg._body_params[1]["text"] == "Doe"

    def test_add_header_image(self, mock_env_vars, valid_phone):
        """Test adding image header."""
        msg = TemplateMessage(valid_phone, "test")
        msg.add_header_image("img123")

        assert len(msg._header_params) == 1
        assert msg._header_params[0]["type"] == "image"
        assert msg._header_params[0]["image"]["id"] == "img123"

    def test_add_button_url(self, mock_env_vars, valid_phone):
        """Test adding URL button."""
        msg = TemplateMessage(valid_phone, "test")
        button_param = ButtonBuilder.url_button("https://example.com", "Visit")
        msg.add_button_param(0, button_param)

        assert len(msg._button_params) == 1
        assert msg._button_params[0]["sub_type"] == "url"
        assert msg._button_params[0]["parameters"][0]["url"] == "https://example.com"

    def test_template_build_payload_complete(self, mock_env_vars, valid_phone):
        """Test complete template payload with header, body, and button."""
        msg = (
            TemplateMessage(valid_phone, "exam_notification", "rw_RW")
            .add_header_image("img_video123")
            .add_body_text("15")
            .add_body_text("Math, Physics")
            .add_button_param(0, ButtonBuilder.url_button("https://exam.com", "Details"))
        )

        payload = msg.build_payload()

        assert payload["type"] == "template"
        assert payload["template"]["name"] == "exam_notification"

        # Components: header, body, button
        components = payload["template"]["components"]
        assert len(components) == 3

        # Header check
        assert components[0]["type"] == "header"
        assert components[0]["parameters"][0]["image"]["id"] == "img_video123"

        # Body check
        assert components[1]["type"] == "body"
        assert components[1]["parameters"][0]["text"] == "15"
        assert components[1]["parameters"][1]["text"] == "Math, Physics"

        # Button check
        button_component = components[2]
        assert button_component["type"] == "button"
        assert button_component["sub_type"] == "url"
        assert button_component["parameters"][0]["url"] == "https://exam.com"


class TestMediaMessage:
    """Test MediaMessage class."""

    def test_media_with_id(self, mock_env_vars, valid_phone):
        """Test media message with media ID."""
        msg = MediaMessage(valid_phone, MediaType.IMAGE, media_id="img123")
        assert msg.media_id == "img123"
        assert msg.media_type == "image"
        payload = msg.build_payload()
        assert payload["type"] == "image"
        assert payload["image"]["id"] == "img123"

    def test_media_with_url(self, mock_env_vars, valid_phone):
        """Test media message with URL."""
        msg = MediaMessage(valid_phone, "video", media_url="https://example.com/video.mp4")
        assert msg.media_url == "https://example.com/video.mp4"
        payload = msg.build_payload()
        assert payload["type"] == "video"
        assert payload["video"]["link"] == "https://example.com/video.mp4"

    def test_media_with_caption(self, mock_env_vars, valid_phone):
        """Test media message with caption."""
        msg = MediaMessage(valid_phone, MediaType.IMAGE, media_id="img123", caption="Beautiful sunset")
        assert msg.caption == "Beautiful sunset"
        payload = msg.build_payload()
        assert payload["image"]["caption"] == "Beautiful sunset"

    def test_media_caption_too_long(self, mock_env_vars, valid_phone):
        """Test media caption exceeds max length."""
        long_caption = "a" * 2000
        with pytest.raises(ValueError, match="Caption exceeds maximum length of 1024 characters"):
            MediaMessage(valid_phone, MediaType.IMAGE, media_id="img123", caption=long_caption)

    def test_media_build_payload_no_id_or_url(self, mock_env_vars, valid_phone):
        """Test media payload without ID or URL raises error."""
        
        with pytest.raises(ValueError, match="Either media_id or media_url must be provided"):
            msg = MediaMessage(valid_phone, MediaType.IMAGE.value)
            msg.build_payload()

    def test_media_build_payload_with_document(self, mock_env_vars, valid_phone):
        """Test document media payload with filename and caption."""
        msg = MediaMessage(
            valid_phone,
            MediaType.DOCUMENT,
            media_id="doc123",
            filename="report.pdf",
            caption="Monthly report"
        )
        payload = msg.build_payload()

        assert payload["type"] == "document"
        assert payload["document"]["id"] == "doc123"
        assert payload["document"]["filename"] == "report.pdf"
        assert payload["document"]["caption"] == "Monthly report"

    def test_media_build_payload_with_sticker(self, mock_env_vars, valid_phone):
        """Test sticker payload works with only media_id."""
        msg = MediaMessage(valid_phone, MediaType.STICKER, media_id="st123")
        payload = msg.build_payload()
        assert payload["type"] == "sticker"
        assert payload["sticker"]["id"] == "st123"



class TestInteractiveMessage:
    """Test InteractiveMessage class."""
    
    def test_interactive_creation(self, mock_env_vars, valid_phone):
        """Test interactive message creation."""
        msg = InteractiveMessage(valid_phone, "Choose option", header="Menu")
        assert msg.body == "Choose option"
        assert msg.header == "Menu"
    
    def test_add_reply_button(self, mock_env_vars, valid_phone):
        """Test adding reply buttons."""
        msg = InteractiveMessage(valid_phone, "Choose")
        msg.add_reply_button("btn1", "Option 1")
        msg.add_reply_button("btn2", "Option 2")
        
        assert len(msg._buttons) == 2
    
    def test_max_buttons_exceeded(self, mock_env_vars, valid_phone):
        """Test maximum buttons limit."""
        msg = InteractiveMessage(valid_phone, "Choose")
        msg.add_reply_button("btn1", "Option 1")
        msg.add_reply_button("btn2", "Option 2")
        msg.add_reply_button("btn3", "Option 3")
        
        with pytest.raises(ValueError, match="Maximum %d reply buttons allowed" % 3):
            msg.add_reply_button("btn4", "Option 4")
    
    def test_interactive_build_payload(self, mock_env_vars, valid_phone):
        """Test interactive message payload."""
        msg = (
            InteractiveMessage(valid_phone, "Choose", header="Menu", footer="Reply ASAP")
            .add_reply_button("yes", "Yes")
            .add_reply_button("no", "No")
        )
        
        payload = msg.build_payload()
        
        assert payload["type"] == "interactive"
        assert payload["interactive"]["type"] == "button"
        assert len(payload["interactive"]["action"]["buttons"]) == 2


class TestListMessage:
    """Test ListMessage class."""
    
    def test_list_creation(self, mock_env_vars, valid_phone):
        """Test list message creation."""
        msg = ListMessage(valid_phone, "Select subject", "View Subjects")
        assert msg.body == "Select subject"
        assert msg.button_text == "View Subjects"
    
    def test_add_section(self, mock_env_vars, valid_phone):
        """Test adding section with rows."""
        msg = ListMessage(valid_phone, "Choose", "Select")
        rows = [
            {"id": "1", "title": "Math"},
            {"id": "2", "title": "Physics"}
        ]
        msg.add_section("Sciences", rows)
        
        assert len(msg._sections) == 1
        assert msg._sections[0]["title"] == "Sciences"
    
    def test_add_row_to_last_section(self, mock_env_vars, valid_phone):
        """Test adding row to last section."""
        msg = ListMessage(valid_phone, "Choose", "Select")
        msg.add_section("Test", [])
        msg.add_row_to_last_section("1", "Option 1", "Description")
        
        assert len(msg._sections[0]["rows"]) == 1
        assert msg._sections[0]["rows"][0]["description"] == "Description"
    
    def test_add_row_without_section(self, mock_env_vars, valid_phone):
        """Test adding row without section raises error."""
        msg = ListMessage(valid_phone, "Choose", "Select")
        
        with pytest.raises(ValueError, match="No sections available"):
            msg.add_row_to_last_section("1", "Option")


class TestLocationMessage:
    """Test LocationMessage class."""
    
    def test_location_creation(self, mock_env_vars, valid_phone):
        """Test location message creation."""
        msg = LocationMessage(
            valid_phone,
            latitude=-1.9441,
            longitude=30.0619,
            name="Kigali Convention Centre",
            address="KG 2 Roundabout, Kigali"
        )
        
        assert msg.latitude == -1.9441
        assert msg.longitude == 30.0619
    
    def test_location_build_payload(self, mock_env_vars, valid_phone):
        """Test location payload."""
        msg = LocationMessage(valid_phone, -1.9441, 30.0619, "Test", "Address")
        payload = msg.build_payload()
        
        assert payload["type"] == "location"
        assert payload["location"]["latitude"] == -1.9441


class TestContactMessage:
    """Test ContactMessage class."""
    
    def test_contact_creation(self, mock_env_vars, valid_phone):
        """Test contact message creation."""
        msg = ContactMessage(valid_phone)
        assert len(msg._contacts) == 0
    
    def test_add_simple_contact(self, mock_env_vars, valid_phone):
        """Test adding simple contact."""
        msg = ContactMessage(valid_phone)
        msg.add_simple_contact("John Doe", "+250788123456")
        
        assert len(msg._contacts) == 1
        assert msg._contacts[0]["name"]["first_name"] == "John Doe"


# -----------------------------
# Batch Operations Tests
# -----------------------------
class TestBatchMessageSender:
    """Test BatchMessageSender class."""
    
    def test_batch_creation(self):
        """Test batch sender creation."""
        batch = BatchMessageSender()
        assert len(batch.messages) == 0
    
    def test_add_messages(self, mock_env_vars, valid_phone):
        """Test adding messages to batch."""
        batch = BatchMessageSender()
        batch.add(TextMessage(valid_phone, "Hello"))
        batch.add(TextMessage(valid_phone, "World"))
        
        assert len(batch.messages) == 2
    
    def test_batch_size_limit(self, mock_env_vars, valid_phone):
        """Test batch size limit."""
        batch = BatchMessageSender()
        
        # Add up to limit
        for i in range(Settings.MAX_BATCH_SIZE):
            batch.add(TextMessage(valid_phone, f"Message {i}"))
        
        # Exceeding should raise error
        with pytest.raises(ValueError, match="Batch size limit"):
            batch.add(TextMessage(valid_phone, "Extra"))
    
    def test_clear_batch(self, mock_env_vars, valid_phone):
        """Test clearing batch."""
        batch = BatchMessageSender()
        batch.add(TextMessage(valid_phone, "Test"))
        batch.clear()
        
        assert len(batch.messages) == 0


# -----------------------------
# Quick Send Tests
# -----------------------------
class TestQuickSend:
    """Test QuickSend helper class."""
    
    @patch.object(WhatsAppClient, 'send')
    def test_quick_send_text(self, mock_send, mock_env_vars, valid_phone, mock_success_response):
        """Test quick send text message."""
        mock_send.return_value = MessageResponse.from_api_response(mock_success_response)
        
        response = QuickSend.text(valid_phone, "Quick message")
        
        assert response.success is True
        mock_send.assert_called_once()
    
    @patch.object(WhatsAppClient, 'send')
    def test_quick_send_template(self, mock_send, mock_env_vars, valid_phone, mock_success_response):
        """Test quick send template."""
        mock_send.return_value = MessageResponse.from_api_response(mock_success_response)
        
        response = QuickSend.template(valid_phone, "welcome", ["John", "Doe"])
        
        assert response.success is True
    
    @patch.object(WhatsAppClient, 'send')
    def test_quick_send_buttons(self, mock_send, mock_env_vars, valid_phone, mock_success_response):
        """Test quick send buttons."""
        mock_send.return_value = MessageResponse.from_api_response(mock_success_response)
        
        response = QuickSend.buttons(
            valid_phone,
            "Choose option",
            [("yes", "Yes"), ("no", "No")]
        )
        
        assert response.success is True


# -----------------------------
# Integration Tests
# -----------------------------
class TestMessageIntegration:
    """Integration tests for complete message flows."""
    
    @patch.object(WhatsAppClient, 'send')
    def test_text_message_with_callbacks(self, mock_send, mock_env_vars, valid_phone, mock_success_response):
        """Test text message with success callback."""
        mock_send.return_value = MessageResponse.from_api_response(mock_success_response)
        
        success_called = []
        
        def on_success(response, context):
            success_called.append(True)
            assert context["user_id"] == 123
        
        msg = (
            TextMessage(valid_phone, "Test")
            .with_context(user_id=123)
            .on_success(on_success)
        )
        
        response = msg.send()
        
        assert response.success is True
        assert len(success_called) == 1
    
    @patch.object(WhatsAppClient, 'send')
    def test_template_message_complex(self, mock_send, mock_env_vars, valid_phone, mock_success_response):
        """Test complex template message."""
        mock_send.return_value = MessageResponse.from_api_response(mock_success_response)
        
        msg = (
            TemplateMessage(valid_phone, "exam_notification", "rw_RW")
            .add_header_video(link="https://example.com/video.mp4")
            .add_body_text("15")
            .add_body_text("Math, Physics")
            .add_copy_code_button(0, "EXAM2024")
        )
        
        payload = msg.build_payload()
        response = msg.send()
        
        # Verify payload structure
        assert payload["template"]["name"] == "exam_notification"
        assert len(payload["template"]["components"]) == 3
        
        # Verify header
        header = payload["template"]["components"][0]
        assert header["type"] == "header"
        assert header["parameters"][0]["type"] == "video"
        
        # Verify body
        body = payload["template"]["components"][1]
        assert body["type"] == "body"
        assert len(body["parameters"]) == 2
        
        # Verify button
        button = payload["template"]["components"][2]
        assert button["type"] == "button"
        assert button["sub_type"] == "copy_code"
        
        assert response.success is True
    
    def test_fluent_api_chaining(self, mock_env_vars, valid_phone):
        """Test fluent API method chaining."""
        msg = (
            TextMessage(valid_phone, "Test")
            .with_context(user_id=123, action="test")
            .on_success(lambda r, c: None)
            .on_error(lambda r, c: None)
        )
        
        assert msg._context["user_id"] == 123
        assert msg._on_success is not None
        assert msg._on_error is not None


# -----------------------------
# Error Handling Tests
# -----------------------------
class TestErrorHandling:
    """Test error handling scenarios."""
    
    @patch.object(WhatsAppClient, 'send')
    def test_error_callback_execution(self, mock_send, mock_env_vars, valid_phone, mock_error_response):
        """Test error callback is called on failure."""
        mock_send.return_value = MessageResponse.from_api_response(mock_error_response)
        
        error_called = []
        
        def on_error(response, context):
            error_called.append(True)
            assert response.success is False
        
        msg = TextMessage(valid_phone, "Test").on_error(on_error)
        response = msg.send()
        
        assert response.success is False
        assert len(error_called) == 1
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_media_upload_file_not_found(self, mock_open, mock_env_vars):
        """Test media upload with non-existent file."""
        client = WhatsAppClient()
        response = client.upload_media("/nonexistent/file.jpg")
        
        assert response.success is False
        assert "File not found" in response.error_message


# -----------------------------
# Async Tests
# -----------------------------
@pytest.mark.asyncio
class TestAsyncOperations:
    """Test async operations."""
    
    @patch('httpx.AsyncClient')
    async def test_asend(self, mock_async_client, mock_env_vars, mock_success_response):
        """Test async message send."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_success_response
        
        mock_async_client.return_value.__aenter__.return_value.post = \
            Mock(return_value=mock_response)
        
        client = WhatsAppClient()
        payload = {"messaging_product": "whatsapp"}
        response = await client.asend(payload)
        
        assert response.success is True
    
    @patch('httpx.AsyncClient')
    async def test_message_send_direct_async(self, mock_async_client, mock_env_vars, 
                                            valid_phone, mock_success_response):
        """Test message send_direct_async method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_success_response
        
        mock_async_client.return_value.__aenter__.return_value.post = \
            Mock(return_value=mock_response)
        
        msg = TextMessage(valid_phone, "Async test")
        response = await msg.send_direct_async()
        
        assert response.success is True


# -----------------------------
# Payload Validation Tests
# -----------------------------
class TestPayloadValidation:
    """Test payload structure validation."""
    
    def test_text_payload_structure(self, mock_env_vars, valid_phone):
        """Validate text message payload structure."""
        msg = TextMessage(valid_phone, "Test", preview_url=True)
        payload = msg.build_payload()
        
        required_keys = ["messaging_product", "to", "type", "text"]
        assert all(key in payload for key in required_keys)
        assert payload["messaging_product"] == "whatsapp"
        assert payload["type"] == "text"
        assert "body" in payload["text"]
        assert "preview_url" in payload["text"]
    
    def test_template_payload_structure(self, mock_env_vars, valid_phone):
        """Validate template message payload structure."""
        msg = TemplateMessage(valid_phone, "test_template")
        msg.add_body_text("param1")
        payload = msg.build_payload()
        
        assert payload["type"] == "template"
        assert "template" in payload
        assert "name" in payload["template"]
        assert "language" in payload["template"]
        assert "components" in payload["template"]
    
    def test_media_payload_structure(self, mock_env_vars, valid_phone):
        """Validate media message payload structure."""
        msg = MediaMessage(valid_phone, MediaType.IMAGE, media_id="img123", caption="Test")
        payload = msg.build_payload()
        
        assert payload["type"] == "image"
        assert "image" in payload
        assert payload["image"]["id"] == "img123"
        assert payload["image"]["caption"] == "Test"
    
    def test_interactive_payload_structure(self, mock_env_vars, valid_phone):
        """Validate interactive message payload structure."""
        msg = InteractiveMessage(valid_phone, "Choose", header="Menu")
        msg.add_reply_button("btn1", "Option 1")
        payload = msg.build_payload()
        
        assert payload["type"] == "interactive"
        assert "interactive" in payload
        assert payload["interactive"]["type"] == "button"
        assert "body" in payload["interactive"]
        assert "action" in payload["interactive"]


# -----------------------------
# Real-World Scenario Tests
# -----------------------------
class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    @patch.object(WhatsAppClient, 'send')
    def test_exam_notification_flow(self, mock_send, mock_env_vars, mock_success_response):
        """Test complete exam notification flow."""
        mock_send.return_value = MessageResponse.from_api_response(mock_success_response)
        
        student_phone = "+250788123456"
        
        # Step 1: Welcome message
        welcome = TextMessage(
            student_phone,
            f"{TextMessage.bold('Hello Student!')} Your exam is scheduled."
        )
        response1 = welcome.send()
        assert response1.success is True
        
        # Step 2: Template with video
        template = (
            TemplateMessage(student_phone, "progress_report")
            .add_header_video(link="https://example.com/video.mp4")
            .add_body_text("15")
            .add_body_text("Math, Physics")
        )
        response2 = template.send()
        assert response2.success is True
        
        # Step 3: Interactive confirmation
        confirm = (
            InteractiveMessage(student_phone, "Will you attend?")
            .add_reply_button("yes", "Yes")
            .add_reply_button("no", "No")
        )
        response3 = confirm.send()
        assert response3.success is True
    
    @patch.object(WhatsAppClient, 'send')
    def test_batch_notification_campaign(self, mock_send, mock_env_vars, mock_success_response):
        """Test batch messaging campaign."""
        mock_send.return_value = MessageResponse.from_api_response(mock_success_response)
        
        students = [
            {"phone": "+250788111111", "name": "Alice"},
            {"phone": "+250788222222", "name": "Bob"},
            {"phone": "+250788333333", "name": "Charlie"},
        ]
        
        batch = BatchMessageSender()
        
        for student in students:
            msg = TextMessage(
                student["phone"],
                f"Hello {student['name']}, your results are ready!"
            )
            batch.add(msg)
        
        assert len(batch.messages) == 3
        
        # Send all
        responses = batch.send()
        assert len(responses) == 3
        assert all(r.success for r in responses)


# -----------------------------
# Edge Cases Tests
# -----------------------------
class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_text_message(self, mock_env_vars, valid_phone):
        """Test empty text message."""
        msg = TextMessage(valid_phone, "")
        payload = msg.build_payload()
        assert payload["text"]["body"] == ""
    
    def test_special_characters_in_text(self, mock_env_vars, valid_phone):
        """Test special characters in text."""
        special_text = "Hello! @#$%^&*() 测试 العربية 🎉"
        msg = TextMessage(valid_phone, special_text)
        payload = msg.build_payload()
        assert payload["text"]["body"] == special_text
    
    def test_phone_number_normalization(self):
        """Test phone number normalization."""
        numbers = [
            ("+250 788 123 456", "+250788123456"),
            ("+250-788-123-456", "+250788123456"),
            ("+250(788)123456", "+250788123456"),
        ]
        
        for input_num, expected in numbers:
            valid, result = WhatsAppClient.validate_phone_number(input_num)
            assert valid is True
            assert result == expected
    
    def test_maximum_text_length_boundary(self, mock_env_vars, valid_phone):
        """Test text at maximum length boundary."""
        max_text = "a" * Settings.MAX_TEXT_LENGTH
        msg = TextMessage(valid_phone, max_text)
        assert len(msg.body) == Settings.MAX_TEXT_LENGTH
        
        # One character over should fail
        with pytest.raises(ValueError):
            TextMessage(valid_phone, max_text + "a")
    
    def test_template_with_no_parameters(self, mock_env_vars, valid_phone):
        """Test template with no parameters."""
        msg = TemplateMessage(valid_phone, "simple_template")
        payload = msg.build_payload()
        
        # Should have empty components or no components
        assert "components" in payload["template"]
        assert len(payload["template"]["components"]) == 0


# -----------------------------
# Performance and Concurrency Tests
# -----------------------------
class TestPerformance:
    """Test performance-related scenarios."""
    
    def test_batch_size_limit_enforcement(self, mock_env_vars, valid_phone):
        """Test batch size limit is enforced."""
        batch = BatchMessageSender()
        
        # Should accept up to MAX_BATCH_SIZE
        for i in range(Settings.MAX_BATCH_SIZE):
            batch.add(TextMessage(valid_phone, f"Message {i}"))
        
        assert len(batch.messages) == Settings.MAX_BATCH_SIZE
    
    def test_large_payload_generation(self, mock_env_vars, valid_phone):
        """Test generating large but valid payload."""
        msg = TextMessage(valid_phone, "a" * 4000)  # Near max
        payload = msg.build_payload()
        
        # Should be serializable to JSON
        json_str = json.dumps(payload)
        assert len(json_str) > 0


# -----------------------------
# Security Tests
# -----------------------------
class TestSecurity:
    """Test security-related functionality."""
    
    def test_webhook_signature_validation_timing_safe(self, mock_env_vars):
        """Test webhook signature uses timing-safe comparison."""
        import hmac
        import hashlib
        
        payload = '{"test": "data"}'
        correct_sig = hmac.new(
            Settings.WHATSAPP_APP_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Correct signature
        assert WhatsAppClient.validate_webhook_signature(payload, correct_sig) is True
        
        # Incorrect signature
        wrong_sig = "0" * 64
        assert WhatsAppClient.validate_webhook_signature(payload, wrong_sig) is False
    
    def test_no_secret_injection_in_logs(self, mock_env_vars, caplog):
        """Test that secrets don't appear in logs."""
        import logging
        
        with caplog.at_level(logging.DEBUG):
            msg = TextMessage("+250788123456", "Test")
            payload = msg.build_payload()
        
        # Token should not appear in any log
        for record in caplog.records:
            assert Settings.WHATSAPP_TOKEN not in record.message


# -----------------------------
# Documentation Tests
# -----------------------------
class TestDocumentation:
    """Test that docstrings and documentation are present."""
    
    def test_classes_have_docstrings(self):
        """Test that main classes have docstrings."""
        classes = [
            Settings,
            WhatsAppClient,
            MessageResponse,
            TextMessage,
            TemplateMessage,
            MediaMessage,
        ]
        
        for cls in classes:
            assert cls.__doc__ is not None, f"{cls.__name__} missing docstring"
    
    def test_public_methods_have_docstrings(self):
        """Test that public methods have docstrings."""
        methods = [
            WhatsAppClient.send,
            WhatsAppClient.upload_media,
            TextMessage.build_payload,
        ]
        
        for method in methods:
            assert method.__doc__ is not None


# ===========================================================
# TEXT MESSAGE TESTS
# ===========================================================
def test_text_message_basic():
    """✅ Should generate a valid text message payload"""
    options = generate_whatsapp_options(
        msg_type="text",
        message_body="Hello, World!",
        preview_url=True
    )
    assert options == {
        "type": "text",
        "body": "Hello, World!",
        "preview_url": True,
    }


def test_text_message_defaults():
    """✅ Should work with defaults and empty message body"""
    options = generate_whatsapp_options(msg_type="text")
    assert options["type"] == "text"
    assert options["body"] == ""
    assert options["preview_url"] is False


# ===========================================================
# TEMPLATE MESSAGE TESTS
# ===========================================================
@patch("builder.TemplateParameterBuilder.text", side_effect=lambda v: {"type": "text", "text": v})
def test_template_message_with_params(mock_text):
    """✅ Should build a template payload with all params"""
    options = generate_whatsapp_options(
        msg_type="template",
        template_name="invoice_template",
        body_params=["param1", {"type": "text", "text": "param2"}],
        header_params=["Header Text"],
        button_params=[
            {"sub_type": "url", "param": "https://example.com"},
            {"sub_type": "phone_number", "param": "+250788000000"},
            {"sub_type": "copy_code", "param": "XYZ123"},
            {"sub_type": "coupon_code", "param": "ABC999"},
        ],
    )
    assert options["type"] == "template"
    assert options["name"] == "invoice_template"
    assert len(options["body_params"]) == 2
    assert len(options["header_params"]) == 1
    assert len(options["button_params"]) == 4


def test_template_message_with_dict_header_param():
    """✅ Should accept dict header params as valid"""
    options = generate_whatsapp_options(
        msg_type="template",
        template_name="header_dict_test",
        header_params=[{"type": "text", "text": "Header"}],
    )
    assert options["header_params"][0]["text"] == "Header"


def test_template_message_with_unknown_button_subtype():
    """✅ Should handle unknown button subtype gracefully"""
    options = generate_whatsapp_options(
        msg_type="template",
        template_name="unknown_button_test",
        button_params=[{"sub_type": "mystery", "param": "???", "index": 2}],
    )
    assert options["button_params"][0]["sub_type"] == "mystery"
    assert "param" in options["button_params"][0]


def test_template_message_without_name_raises_error():
    """🚫 Should raise ValidationError when template name missing"""
    with pytest.raises(ValidationError):
        generate_whatsapp_options(msg_type="template")


def test_invalid_body_param_type_raises_error():
    """🚫 Should raise ValidationError when body param invalid type"""
    with pytest.raises(ValidationError):
        generate_whatsapp_options(
            msg_type="template",
            template_name="broken_template",
            body_params=[123]
        )


# ===========================================================
# MEDIA MESSAGE TESTS
# ===========================================================
def test_media_message_with_media_id():
    """✅ Should generate valid media payload with media_id"""
    options = generate_whatsapp_options(
        msg_type="media",
        media_type="image",
        media_id="abc123",
        caption="A nice image"
    )
    assert options["media_type"] == "image"
    assert options["caption"] == "A nice image"


def test_media_message_with_media_url():
    """✅ Should generate valid media payload with media_url"""
    options = generate_whatsapp_options(
        msg_type="media",
        media_url="https://example.com/photo.jpg"
    )
    assert options["media_type"] == "image"
    assert options["media_url"] == "https://example.com/photo.jpg"


def test_media_message_requires_media_id_or_url():
    """🚫 Should raise ValidationError if both media_id and media_url missing"""
    with pytest.raises(ValidationError):
        generate_whatsapp_options(msg_type="media")


# ===========================================================
# INTERACTIVE MESSAGE TESTS
# ===========================================================
@patch("builder.ButtonBuilder.reply_button", return_value={"type": "reply", "id": "opt1", "title": "Option 1"})
@patch("builder.ButtonBuilder.url_button", return_value={"type": "url", "url": "https://example.com", "title": "Visit"})
@patch("builder.ButtonBuilder.call_button", return_value={"type": "phone_number", "title": "Call"})
@patch("builder.ButtonBuilder.copy_code_button", return_value={"type": "copy_code", "title": "Copy"})
@patch("builder.ButtonBuilder.coupon_code", return_value={"type": "coupon_code", "title": "Coupon"})
def test_interactive_message_with_buttons(mock_coupon, mock_copy, mock_call, mock_url, mock_reply):
    """✅ Should build interactive message with multiple buttons"""
    options = generate_whatsapp_options(
        msg_type="interactive",
        message_body="Choose one:",
        header="Header text",
        footer="Footer text",
        buttons=[
            {"type": "reply", "id": "opt1", "title": "Option 1"},
            {"type": "url", "url": "https://example.com", "title": "Visit"},
            {"type": "phone_number", "phone": "+250788000000", "title": "Call"},
            {"type": "copy_code", "code": "ABC123"},
            {"type": "coupon_code", "code": "DISC10"},
        ],
    )

    assert options["type"] == "interactive"
    assert len(options["buttons"]) == 5
    assert options["header"] == "Header text"
    assert options["footer"] == "Footer text"


# ===========================================================
# INVALID TYPE TEST
# ===========================================================
def test_invalid_message_type_raises_error():
    """🚫 Should raise ValidationError for unsupported message type"""
    with pytest.raises(ValidationError):
        generate_whatsapp_options(msg_type="alien")

# -----------------------------
# Test Runner
# -----------------------------
# if __name__ == "__main__":
#     pytest.main([__file__, "-v", "--tb=short"])