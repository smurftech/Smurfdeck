import json

from smurfdeck.models.config import AppConfig
from smurfdeck.persistence.config_store import ConfigStore


def test_store_saves_and_loads_configuration_atomically(tmp_path) -> None:
    path = tmp_path / "smurfdeck" / "config.json"
    store = ConfigStore(path)
    config = AppConfig()
    config.active_profile.active_page.key(0).label = "Terminal"
    config.active_profile.active_page.key(0).working_directory = "/tmp"
    store.save(config)
    restored = store.load().active_profile.active_page.key(0)
    assert restored.label == "Terminal"
    assert restored.working_directory == "/tmp"
    assert not list(path.parent.glob("*.tmp"))


def test_invalid_configuration_is_preserved_and_replaced_with_defaults(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text("not json", encoding="utf-8")
    store = ConfigStore(path)
    recovered = store.load()
    assert recovered.active_profile.name == "Desktop"
    assert store.recovery_path is not None
    assert store.recovery_path.read_text(encoding="utf-8") == "not json"


def test_unknown_schema_is_recovered_safely(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    store = ConfigStore(path)
    assert store.load().schema_version == 4
    assert store.recovery_path is not None
