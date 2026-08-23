from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

SCHEMA_VERSION = 2
DEFAULT_KEY_COUNT = 15


def new_id() -> str:
    return uuid4().hex


@dataclass(slots=True)
class KeyConfig:
    label: str = ""
    action_type: str = "none"
    action_value: str = ""
    trigger: str = "press"

    def to_dict(self) -> dict[str, str]:
        return {
            "label": self.label,
            "action_type": self.action_type,
            "action_value": self.action_value,
            "trigger": self.trigger,
        }

    @classmethod
    def from_dict(cls, data: object) -> KeyConfig:
        if not isinstance(data, dict):
            raise ValueError("Key configuration must be an object")
        trigger = str(data.get("trigger", "press"))
        if trigger not in {"press", "release", "both"}:
            raise ValueError(f"Unsupported key trigger: {trigger}")
        return cls(
            label=str(data.get("label", "")),
            action_type=str(data.get("action_type", "none")),
            action_value=str(data.get("action_value", "")),
            trigger=trigger,
        )


@dataclass(slots=True)
class PageConfig:
    name: str
    id: str = field(default_factory=new_id)
    keys: dict[int, KeyConfig] = field(default_factory=dict)

    def key(self, index: int) -> KeyConfig:
        if index < 0:
            raise ValueError("Key index cannot be negative")
        return self.keys.setdefault(index, KeyConfig())

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "keys": {str(index): key.to_dict() for index, key in sorted(self.keys.items())},
        }

    @classmethod
    def from_dict(cls, data: object) -> PageConfig:
        if not isinstance(data, dict):
            raise ValueError("Page configuration must be an object")
        page_id = str(data.get("id", ""))
        name = str(data.get("name", "")).strip()
        if not page_id or not name:
            raise ValueError("Pages require non-empty id and name values")
        raw_keys = data.get("keys", {})
        if not isinstance(raw_keys, dict):
            raise ValueError("Page keys must be an object")
        keys: dict[int, KeyConfig] = {}
        for raw_index, raw_key in raw_keys.items():
            index = int(raw_index)
            if index < 0:
                raise ValueError("Key index cannot be negative")
            keys[index] = KeyConfig.from_dict(raw_key)
        return cls(id=page_id, name=name, keys=keys)


@dataclass(slots=True)
class ProfileConfig:
    name: str
    id: str = field(default_factory=new_id)
    pages: list[PageConfig] = field(default_factory=list)
    active_page_id: str = ""

    def __post_init__(self) -> None:
        if not self.pages:
            self.pages.append(PageConfig(name="Page 1"))
        if not self.active_page_id or not any(
            page.id == self.active_page_id for page in self.pages
        ):
            self.active_page_id = self.pages[0].id

    @property
    def active_page(self) -> PageConfig:
        return next(page for page in self.pages if page.id == self.active_page_id)

    def page_by_id(self, page_id: str) -> PageConfig:
        try:
            return next(page for page in self.pages if page.id == page_id)
        except StopIteration as error:
            raise KeyError(page_id) from error

    def add_page(self, name: str | None = None) -> PageConfig:
        page = PageConfig(name=name or f"Page {len(self.pages) + 1}")
        self.pages.append(page)
        self.active_page_id = page.id
        return page

    def delete_page(self, page_id: str) -> None:
        if len(self.pages) == 1:
            raise ValueError("A profile must contain at least one page")
        self.pages = [page for page in self.pages if page.id != page_id]
        if self.active_page_id == page_id:
            self.active_page_id = self.pages[0].id

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "active_page_id": self.active_page_id,
            "pages": [page.to_dict() for page in self.pages],
        }

    @classmethod
    def from_dict(cls, data: object) -> ProfileConfig:
        if not isinstance(data, dict):
            raise ValueError("Profile configuration must be an object")
        profile_id = str(data.get("id", ""))
        name = str(data.get("name", "")).strip()
        if not profile_id or not name:
            raise ValueError("Profiles require non-empty id and name values")
        raw_pages = data.get("pages", [])
        if not isinstance(raw_pages, list) or not raw_pages:
            raise ValueError("Profiles require at least one page")
        return cls(
            id=profile_id,
            name=name,
            active_page_id=str(data.get("active_page_id", "")),
            pages=[PageConfig.from_dict(page) for page in raw_pages],
        )


@dataclass(slots=True)
class AppConfig:
    profiles: list[ProfileConfig] = field(default_factory=list)
    active_profile_id: str = ""
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.profiles:
            self.profiles.append(ProfileConfig(name="Desktop"))
        if not self.active_profile_id or not any(
            profile.id == self.active_profile_id for profile in self.profiles
        ):
            self.active_profile_id = self.profiles[0].id

    @property
    def active_profile(self) -> ProfileConfig:
        return next(profile for profile in self.profiles if profile.id == self.active_profile_id)

    def profile_by_id(self, profile_id: str) -> ProfileConfig:
        try:
            return next(profile for profile in self.profiles if profile.id == profile_id)
        except StopIteration as error:
            raise KeyError(profile_id) from error

    def add_profile(self, name: str) -> ProfileConfig:
        profile = ProfileConfig(name=name.strip() or f"Profile {len(self.profiles) + 1}")
        self.profiles.append(profile)
        self.active_profile_id = profile.id
        return profile

    def duplicate_profile(self, profile_id: str) -> ProfileConfig:
        source = self.profile_by_id(profile_id)
        pages = [
            PageConfig(
                name=page.name,
                keys={
                    index: KeyConfig.from_dict(key.to_dict())
                    for index, key in page.keys.items()
                },
            )
            for page in source.pages
        ]
        duplicate = ProfileConfig(name=f"{source.name} copy", pages=pages)
        self.profiles.append(duplicate)
        self.active_profile_id = duplicate.id
        return duplicate

    def delete_profile(self, profile_id: str) -> None:
        if len(self.profiles) == 1:
            raise ValueError("SmurfDeck must contain at least one profile")
        self.profiles = [profile for profile in self.profiles if profile.id != profile_id]
        if self.active_profile_id == profile_id:
            self.active_profile_id = self.profiles[0].id

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "active_profile_id": self.active_profile_id,
            "profiles": [profile.to_dict() for profile in self.profiles],
        }

    @classmethod
    def from_dict(cls, data: object) -> AppConfig:
        if not isinstance(data, dict):
            raise ValueError("Configuration root must be an object")
        version = data.get("schema_version")
        if version not in (1, SCHEMA_VERSION):
            raise ValueError(f"Unsupported configuration schema version: {version!r}")
        raw_profiles = data.get("profiles", [])
        if not isinstance(raw_profiles, list) or not raw_profiles:
            raise ValueError("Configuration requires at least one profile")
        return cls(
            schema_version=SCHEMA_VERSION,
            active_profile_id=str(data.get("active_profile_id", "")),
            profiles=[ProfileConfig.from_dict(profile) for profile in raw_profiles],
        )
