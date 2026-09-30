import json
import os
from io import BytesIO

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from evdev import ecodes
from PIL import Image
from PySide6.QtCore import QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from smurfdeck.actions.engine import ActionEngine, ActionResult
from smurfdeck.actions.presets import SHORTCUT_PRESETS
from smurfdeck.actions.sequences import parse_sequence
from smurfdeck.actions.shortcuts import parse_shortcut
from smurfdeck.devices.base import DeckKeyEvent
from smurfdeck.input.uinput import UInputEmitter
from smurfdeck.models.config import AppConfig, KeyConfig
from smurfdeck.persistence.config_store import ConfigStore
from smurfdeck.rendering.images import import_image, load_animation
from smurfdeck.rendering.keys import key_preview, labeled_key_image
from smurfdeck.ui.main_window import MainWindow
from smurfdeck.ui.sequence_editor import SequenceEditor, SequenceRunner


class Emitter:
    def __init__(self):
        self.chords = []

    def send_chord(self, keys):
        self.chords.append(keys)

    def close(self):
        pass


@pytest.fixture
def window(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("smurfdeck.ui.main_window.StreamDeckDevice.discover", lambda: [])
    win = MainWindow(ConfigStore(tmp_path / "config.json"))
    yield win
    win._quit_requested = True
    win.close()
    app.processEvents()


def test_all_fifty_presets_dispatch_distinct_editable_configs():
    assert len(SHORTCUT_PRESETS) == len({p.id for p in SHORTCUT_PRESETS}) == 50
    emitter = Emitter()
    engine = ActionEngine(emitter)
    for index, preset in enumerate(SHORTCUT_PRESETS):
        key = preset.key_config()
        assert engine.handle_key(index, key, True).success
        assert emitter.chords[-1] == parse_shortcut(preset.shortcut)
        key.label = "Custom"
        assert preset.key_config().label != "Custom"
    by_id = {p.id: p for p in SHORTCUT_PRESETS}
    assert by_id["desktop.copy"].shortcut == "Ctrl+C"
    assert by_id["konsole.copy"].shortcut == "Ctrl+Shift+C"
    assert by_id["konsole.paste"].shortcut == "Ctrl+Shift+V"


def test_release_uses_original_press_configuration():
    emitter = Emitter()
    engine = ActionEngine(emitter)
    first = KeyConfig(action_type="keyboard", action_value="Ctrl+C", trigger="release")
    second = KeyConfig(action_type="keyboard", action_value="Ctrl+V", trigger="release")
    engine.handle_key(0, first, True)
    first.action_value = "Ctrl+X"
    engine.handle_key(0, second, False)
    assert emitter.chords == [parse_shortcut("Ctrl+C")]
    engine.reset_key_states()
    assert engine.handle_key(0, second, False).executed is False


def test_duplicate_profile_remaps_links_and_preserves_active_page():
    config = AppConfig()
    first = config.active_profile.active_page
    second = config.active_profile.add_page("Other")
    first.keys[0] = KeyConfig(action_type="page", action_value=f"page:{second.id}")
    copied = config.duplicate_profile(config.active_profile_id)
    assert copied.pages[0].keys[0].action_value == f"page:{copied.pages[1].id}"
    assert copied.active_page_id == copied.pages[1].id
    copied.pages[0].keys[0].label = "Changed"
    assert first.keys[0].label == ""


def test_undo_is_scoped_to_page(window):
    first = window.config.active_profile.active_page
    window._drop_action(0, "preset:desktop.copy")
    second = window.config.active_profile.add_page("Other")
    window._refresh_page_combo()
    window._undo()
    assert not second.keys
    window._drop_action(1, "preset:konsole.copy")
    window._navigate_page(f"page:{first.id}")
    window._undo()
    assert not first.keys
    assert second.keys[1].action_value == "Ctrl+Shift+C"
    window._redo()
    assert first.keys[0].action_value == "Ctrl+C"


def test_presets_search_by_chord_and_category_and_drag(window):
    window._category_filter.setCurrentText("Konsole")
    window._action_search.setText("Ctrl+Shift+C")
    shown = [window._action_list.item(i) for i in range(window._action_list.count())
             if not window._action_list.item(i).isHidden()]
    assert len(shown) == 1
    window._on_action_activated(shown[0])
    window._apply_key_edits()
    assert window.config.active_profile.active_page.keys[0].action_value == "Ctrl+Shift+C"
    window._drop_action(1, "preset:desktop.paste")
    assert window.config.active_profile.active_page.keys[1].action_value == "Ctrl+V"


def test_hardware_press_does_not_replace_editor_draft(window):
    window._label_edit.setText("Unapplied edit")
    window._on_key_event(DeckKeyEvent(2, True))
    assert window._label_edit.text() == "Unapplied edit"
    assert window._selected_key == 0


def test_custom_colors_survive_unrelated_label_edit(window):
    key = window.config.active_profile.active_page.key(0)
    key.background_color, key.foreground_color = "#123456", "#ABCDEF"
    window._refresh_canvas()
    window._label_edit.setText("Renamed")
    window._apply_key_edits()
    assert key.background_color == "#123456"
    assert key.foreground_color == "#ABCDEF"


def test_copy_paste_between_pages_is_independent_and_undoable(window):
    window._drop_action(0, "preset:desktop.copy")
    window._copy_key(0)
    page = window.config.active_profile.add_page("Other")
    window._refresh_page_combo()
    window._paste_key(2)
    assert page.keys[2].action_value == "Ctrl+C"
    window._clear_key(2)
    window._undo()
    assert page.keys[2].action_value == "Ctrl+C"


def test_small_window_editor_controls_fit_without_clipping(window):
    window.resize(900, 600)
    window.show()
    QApplication.processEvents()
    viewport = window._quick_scroll.viewport()
    for widget in (window._apply_key_button, window._foreground_combo, window._redo_button):
        point = widget.mapTo(viewport, QPoint(widget.width(), widget.height()))
        assert point.x() <= viewport.width()
        assert point.y() <= viewport.height()
    frame = window._deck_canvas.frame
    assert frame.y() + frame.height() <= window._deck_canvas.height()


def test_imported_animation_is_owned_and_renders_different_frames(tmp_path):
    source = tmp_path / "original.gif"
    red, blue = Image.new("RGB", (72, 72), "red"), Image.new("RGB", (72, 72), "blue")
    red.save(source, save_all=True, append_images=[blue], duration=[100, 200], loop=0)
    imported = import_image(source, tmp_path / "assets")
    source.unlink()
    animation = load_animation(imported)
    assert len(animation.frames) == 2
    assert animation.frame_index(0) == 0
    assert animation.frame_index(100) == 1
    assert animation.frame_index(300) == 0
    first = key_preview((72, 72), "", image_path=imported, elapsed_ms=0)
    second = key_preview((72, 72), "", image_path=imported, elapsed_ms=100)
    assert first.getpixel((36, 36)) == (255, 0, 0)
    assert second.getpixel((36, 36)) == (0, 0, 255)
    class Deck:
        def key_image_format(self):
            return dict(size=(72, 72), rotation=0, flip=(False, False), format="JPEG")
    native = labeled_key_image(Deck(), "", image_path=imported, elapsed_ms=100)
    with Image.open(BytesIO(native)) as decoded:
        assert decoded.size == (72, 72)
        assert decoded.getpixel((36, 36))[2] > 200


def test_missing_image_falls_back_and_oversized_image_is_rejected(tmp_path):
    assert key_preview((72, 72), "Copy", image_path=str(tmp_path / "missing")).size == (72, 72)
    large = tmp_path / "large.png"
    Image.new("RGB", (2100, 2100)).save(large)
    with pytest.raises(ValueError, match="4 million"):
        load_animation(str(large))


def test_schema_six_migration_keeps_original_backup(tmp_path):
    path = tmp_path / "config.json"
    old = AppConfig().to_dict()
    old["schema_version"] = 6
    path.write_text(json.dumps(old))
    store = ConfigStore(path)
    config = store.load()
    store.save(config)
    backup = tmp_path / "config.schema-6.backup.json"
    assert json.loads(backup.read_text()) == old
    store.save(config)
    assert json.loads(backup.read_text()) == old
    assert store.load().schema_version == 7


@pytest.mark.parametrize("value", ["[]", '[{"type":"sequence","value":"[]"}]',
                                  '[{"type":"delay","value":"-1"}]',
                                  '[{"type":"keyboard","value":"Ctrl+Unknown"}]'])
def test_invalid_sequences_rejected(value):
    with pytest.raises(ValueError):
        parse_sequence(value)


def test_sequence_is_ordered_nonblocking_cancellable_and_disallows_overlap(window):
    emitter, results = Emitter(), []
    runner = SequenceRunner(ActionEngine(emitter), lambda *args: results.append(args), window)
    value = json.dumps([{"type": "keyboard", "value": "Ctrl+C"},
                        {"type": "delay", "value": "50"},
                        {"type": "keyboard", "value": "Ctrl+V"}])
    assert runner.start(0, value).success
    assert not emitter.chords  # Scheduled, not synchronously executed.
    assert not runner.start(1, value).success
    QTest.qWait(350)
    assert emitter.chords == [parse_shortcut("Ctrl+C"), parse_shortcut("Ctrl+V")]
    assert results[-1][1].success
    assert runner.start(0, value).success
    runner.cancel()
    QTest.qWait(30)
    assert len(emitter.chords) == 2


def test_sequence_failure_stops_later_steps(window):
    class Broken(Emitter):
        def send_chord(self, keys):
            raise PermissionError("uinput denied")
    results = []
    runner = SequenceRunner(ActionEngine(Broken()), lambda *args: results.append(args), window)
    runner.start(0, '[{"type":"keyboard","value":"Ctrl+C"},'
                    '{"type":"keyboard","value":"Ctrl+V"}]')
    QTest.qWait(30)
    assert not runner.running
    assert "Step 1" in results[-1][1].message
    assert not results[-1][1].success


def test_sequence_editor_reorders_and_round_trips(window):
    editor = SequenceEditor('[{"type":"keyboard","value":"Ctrl+C"},'
                            '{"type":"delay","value":"500"}]', window)
    editor.table.setCurrentCell(1, 0)
    editor.move_step(-1)
    editor.save()
    assert parse_sequence(editor.value)[0].action_type == "delay"


def test_partial_uinput_failure_releases_pressed_modifier():
    class Device:
        def __init__(self):
            self.events = []
        def write(self, event_type, code, value):
            if code == ecodes.KEY_C and value == 1:
                raise OSError("write failed")
            self.events.append((code, value))
        def syn(self):
            pass
    device = Device()
    emitter = UInputEmitter([ecodes.KEY_LEFTCTRL, ecodes.KEY_C], device)
    with pytest.raises(OSError):
        emitter.send_chord((ecodes.KEY_LEFTCTRL, ecodes.KEY_C))
    assert device.events == [(ecodes.KEY_LEFTCTRL, 1), (ecodes.KEY_LEFTCTRL, 0)]


def test_old_command_feedback_is_ignored_after_page_switch():
    class Desktop:
        def run_command(self, value, directory, callback, timeout, environment):
            self.callback = callback
            return ActionResult(True, True, "Command running")
    desktop, results = Desktop(), []
    engine = ActionEngine(Emitter(), desktop, feedback=lambda *args: results.append(args))
    engine.execute(0, KeyConfig(action_type="command", action_value="echo hi"))
    engine.invalidate_feedback()
    desktop.callback(ActionResult(True, True, "Done"))
    assert results == []


def test_animation_tick_updates_device_and_stops_for_static_page(window, tmp_path, monkeypatch):
    from smurfdeck.devices.base import DeckGeometry, DeckInfo
    QApplication.processEvents()
    image = tmp_path / "key.gif"
    Image.new("RGB", (72, 72), "red").save(
        image, save_all=True, append_images=[Image.new("RGB", (72, 72), "blue")],
        duration=100, loop=0,
    )
    class Device:
        info = DeckInfo("Test", DeckGeometry(5, 3, 72, 72))
        def __init__(self):
            self.frames = []
        def render_key_config(self, index, config, state="", elapsed_ms=0):
            if config.image_path:
                self.frames.append(load_animation(config.image_path).frame_index(elapsed_ms))
        def close(self):
            pass
    device = Device()
    window._device = device
    window.config.active_profile.active_page.keys[0] = KeyConfig(image_path=str(image))
    window._refresh_canvas()
    monkeypatch.setattr("smurfdeck.ui.main_window.monotonic",
                        lambda: window._animation_start + .150)
    window._animate_keys()
    assert device.frames[0] == 0 and device.frames[-1] == 1
    window.config.active_profile.add_page("Static")
    window._refresh_page_combo()
    assert not window._animation_timer.isActive()
