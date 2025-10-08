import pytest
from unittest.mock import patch
from exception import ValidationError
from option import generate_whatsapp_options
from utils.whatsapp import ButtonBuilder, TemplateParameterBuilder


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

