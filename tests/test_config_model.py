import pytest

from smurfdeck.models.config import AppConfig


def test_default_config_has_one_profile_and_page() -> None:
    config = AppConfig()
    assert config.active_profile.name == "Desktop"
    assert config.active_profile.active_page.name == "Page 1"


def test_profiles_and_pages_keep_at_least_one_item() -> None:
    config = AppConfig()
    with pytest.raises(ValueError, match="at least one profile"):
        config.delete_profile(config.active_profile_id)
    with pytest.raises(ValueError, match="at least one page"):
        config.active_profile.delete_page(config.active_profile.active_page_id)


def test_duplicate_profile_has_independent_keys() -> None:
    config = AppConfig()
    config.active_profile.active_page.key(2).label = "Play"
    duplicate = config.duplicate_profile(config.active_profile_id)
    duplicate.active_page.key(2).label = "Pause"
    assert config.profiles[0].active_page.key(2).label == "Play"
    assert duplicate.active_page.key(2).label == "Pause"


def test_round_trip_preserves_active_profile_page_and_key() -> None:
    config = AppConfig()
    second_profile = config.add_profile("Development")
    second_page = second_profile.add_page("Commands")
    second_page.key(4).label = "Tests"
    restored = AppConfig.from_dict(config.to_dict())
    assert restored.active_profile.name == "Development"
    assert restored.active_profile.active_page.name == "Commands"
    assert restored.active_profile.active_page.key(4).label == "Tests"


def test_version_one_configuration_migrates_with_press_trigger() -> None:
    config = AppConfig()
    legacy_key = config.active_profile.active_page.key(0)
    legacy_key.action_type = "keyboard"
    legacy_key.action_value = "Ctrl+S"
    legacy = config.to_dict()
    legacy["schema_version"] = 1
    legacy["profiles"][0]["pages"][0]["keys"]["0"].pop("trigger")
    restored = AppConfig.from_dict(legacy)
    assert restored.schema_version == 2
    assert restored.active_profile.active_page.key(0).trigger == "press"
