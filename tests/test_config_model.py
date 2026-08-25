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
    assert restored.schema_version == 5
    assert restored.active_profile.active_page.key(0).working_directory == ""
    assert restored.active_profile.active_page.key(0).trigger == "press"


def test_key_visuals_round_trip_and_legacy_defaults() -> None:
    config = AppConfig()
    key = config.active_profile.active_page.key(1)
    key.icon = "VOL"
    key.foreground_color = "#E6F0FF"
    key.background_color = "#0D6EFD"
    restored = AppConfig.from_dict(config.to_dict()).active_profile.active_page.key(1)
    assert (restored.icon, restored.foreground_color, restored.background_color) == (
        "VOL",
        "#E6F0FF",
        "#0D6EFD",
    )


def test_key_visuals_reject_invalid_colours() -> None:
    data = AppConfig().to_dict()
    data["profiles"][0]["pages"][0]["keys"] = {
        "0": {"background_color": "blue"}
    }
    with pytest.raises(ValueError, match="colours"):
        AppConfig.from_dict(data)


def test_desktop_device_preferences_round_trip() -> None:
    config = AppConfig(
        preferred_device_serial="ABC-123", brightness=50, close_to_tray=False
    )
    restored = AppConfig.from_dict(config.to_dict())
    assert restored.preferred_device_serial == "ABC-123"
    assert restored.brightness == 50
    assert restored.close_to_tray is False


def test_brightness_rejects_out_of_range_values() -> None:
    data = AppConfig().to_dict()
    data["brightness"] = 101
    with pytest.raises(ValueError, match="Brightness"):
        AppConfig.from_dict(data)
