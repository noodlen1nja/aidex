import pytest

from aidex.redact import BUILTIN_PATTERNS, RedactionError, redact_pii


def test_email_redacted() -> None:
    result = redact_pii("Contact bob@example.com today")
    assert result.redacted_text == "Contact [EMAIL] today"
    assert result.redaction_count == 1
    assert result.redactions[0].type == "email"


def test_phone_redacted() -> None:
    result = redact_pii("Call 555-867-5309 now")
    assert "[PHONE]" in result.redacted_text
    assert "555" not in result.redacted_text


def test_ssn_redacted() -> None:
    result = redact_pii("SSN: 123-45-6789")
    assert result.redacted_text == "SSN: [SSN]"
    assert result.redactions[0].type == "ssn"


def test_credit_card_redacted() -> None:
    result = redact_pii("Card 4111 1111 1111 1111 on file")
    assert result.redacted_text == "Card [CREDIT_CARD] on file"


def test_ipv4_redacted() -> None:
    result = redact_pii("Server at 192.168.1.100 responded")
    assert result.redacted_text == "Server at [IP] responded"


@pytest.mark.parametrize(
    "secret",
    [
        "sk-abc123def456ghi789jkl",
        "AKIAIOSFODNN7EXAMPLE",
        "ghp_" + "a1B2" * 9,
    ],
)
def test_api_keys_redacted(secret: str) -> None:
    result = redact_pii(f"token={secret} ok")
    assert result.redacted_text == "token=[API_KEY] ok"
    assert secret not in result.redacted_text


def test_audit_trail_spans_reference_original_text() -> None:
    text = "Email bob@example.com and IP 10.0.0.1"
    result = redact_pii(text)
    assert result.redaction_count == 2
    for redaction in result.redactions:
        original = text[redaction.start : redaction.end]
        # the audit record itself never carries the original value
        assert original not in (
            redaction.type,
            redaction.placeholder,
        )
        assert original not in result.redacted_text


def test_pattern_subset_only_redacts_selected() -> None:
    text = "bob@example.com and 192.168.1.1"
    result = redact_pii(text, patterns=["email"])
    assert "[EMAIL]" in result.redacted_text
    assert "192.168.1.1" in result.redacted_text


def test_generic_placeholder_style() -> None:
    result = redact_pii("bob@example.com", placeholder_style="generic")
    assert result.redacted_text == "[REDACTED]"


def test_unknown_pattern_raises() -> None:
    with pytest.raises(RedactionError):
        redact_pii("hello", patterns=["names"])


def test_unknown_style_raises() -> None:
    with pytest.raises(RedactionError):
        redact_pii("hello", placeholder_style="rot13")


def test_no_pii_means_no_changes() -> None:
    text = "Nothing sensitive here."
    result = redact_pii(text)
    assert result.redacted_text == text
    assert result.redaction_count == 0


def test_builtin_patterns_exported() -> None:
    assert set(BUILTIN_PATTERNS) == {
        "api_key",
        "email",
        "ssn",
        "credit_card",
        "ipv4",
        "phone",
    }


def test_overlapping_matches_do_not_double_redact() -> None:
    # 16-digit card could also partially match phone; only one placeholder
    result = redact_pii("4111-1111-1111-1111")
    assert result.redacted_text == "[CREDIT_CARD]"
    assert result.redaction_count == 1
