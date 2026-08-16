"""设置模块测试:默认值 / 往返读写 / 损坏文件恢复 / 校验。"""

from __future__ import annotations

import json

from app.settings.models import AppSettings
from app.settings.store import SettingsStore


def test_defaults_when_missing(tmp_path):
    store = SettingsStore(tmp_path / "config.json")
    s = store.settings
    assert s.capture_hotkey == "ctrl+alt+t"
    assert s.target_lang == "zho_Hans"
    assert s.auto_save_vocab is True


def test_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    store = SettingsStore(path)
    new = AppSettings(capture_hotkey="ctrl+alt+f1", target_lang="eng_Latn")
    assert store.save(new) == []
    assert json.loads(path.read_text(encoding="utf-8")) == new.to_dict()

    reloaded = SettingsStore(path)
    assert reloaded.settings == new


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not valid json", encoding="utf-8")
    store = SettingsStore(path)
    assert store.settings == AppSettings()
    assert path.with_suffix(".json.bak").exists()


def test_validate_rejects_bad_values():
    s = AppSettings(capture_hotkey="t", query_hotkey="t", target_lang="xx_XX")
    errors = s.validate()
    assert any("快捷键" in e for e in errors)
    assert any("目标语言" in e for e in errors)


def test_changed_signal_emitted(tmp_path):
    store = SettingsStore(tmp_path / "config.json")
    got: list = []
    store.changed.connect(lambda s: got.append(s))
    store.save(AppSettings(target_lang="jpn_Jpan"))
    assert len(got) == 1 and got[0].target_lang == "jpn_Jpan"
