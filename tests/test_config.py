from galaxis_hub.config import VALID_SECTIONS, is_valid_section


def test_valid_sections_constant_is_complete():
    assert VALID_SECTIONS == (
        "kyc",
        "avatar",
        "combined",
        "keywords",
        "google_adcopy",
        "fb_adcopy",
        "meta_audience",
        "google_audience_1",
        "google_audience_2",
        "customer_journey",
        "competitors",
        "seasonality",
    )


def test_is_valid_section_accepts_known():
    assert is_valid_section("keywords") is True


def test_is_valid_section_rejects_unknown():
    assert is_valid_section("not-a-section") is False
