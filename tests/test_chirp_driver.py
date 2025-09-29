from pathlib import Path

from rt950pro.chirp_driver import RT950ProRadio, _build_clone_payload
from rt950pro.channel import Bandwidth
from rt950pro.image import RadioImage
from rt950pro.settings_api import (
    get_dtmf_code_group,
    get_dtmf_ptt_mode,
    get_function_value,
)

TAIL_START = 0x7A80


def _setting_name(item):
    if hasattr(item, "get_name"):
        return item.get_name()
    return getattr(item, "name", None)


def _load_image():
    data = Path("dumps/clean.bin").read_bytes()
    return RadioImage.from_bytes(data)


def test_get_memory_mapping():
    driver = RT950ProRadio()
    driver._image = _load_image()

    mem = driver.get_memory(4)
    assert mem.number == 4
    assert not mem.empty
    assert mem.freq == 446_056_250
    assert mem.name == "MM PMR 05"
    assert mem.power == "High"
    assert mem.mode == "FM"

    empty_mem = driver.get_memory(100)
    assert empty_mem.empty


def test_set_memory_updates_image():
    driver = RT950ProRadio()
    driver._image = _load_image()

    mem = driver.get_memory(4)
    mem.name = "ABCDEF"
    driver.set_memory(mem)

    payload = _build_clone_payload(driver._image)
    baseline = Path("dumps/clean.bin").read_bytes()

    diffs = [idx for idx, (a, b) in enumerate(zip(baseline, payload)) if a != b]
    assert diffs
    channel_region = range(4 * 32, (4 + 1) * 32)
    for idx in diffs:
        assert idx in channel_region or idx >= TAIL_START


def test_set_memory_mode_updates_bandwidth_and_clears_scrambler():
    driver = RT950ProRadio()
    driver._image = _load_image()

    # Simulate garbage scrambler/encryption values in the raw image
    channel = driver._image.channels[4]
    channel.scrambler = 15
    channel.encryption = 3

    mem = driver.get_memory(4)
    mem.mode = "NFM"
    driver.set_memory(mem)

    channel = driver._image.channels[4]
    assert channel.bandwidth is Bandwidth.NARROW
    assert channel.scrambler == 0
    assert channel.encryption == 0
    roundtrip = driver.get_memory(4)
    assert roundtrip.mode == "NFM"
    assert roundtrip.extra["scrambler"] == 0
    assert roundtrip.extra["encryption"] == 0


def test_radio_settings_round_trip():
    driver = RT950ProRadio()
    driver._image = _load_image()

    settings = driver.get_settings()
    mapping = {}
    for item in settings.walk():
        name = _setting_name(item)
        if name:
            mapping[name] = item

    assert "function.sql" in mapping
    mapping["function.sql"].value.set_value(5)

    assert "function.sound_tx_end" in mapping
    mapping["function.sound_tx_end"].value.set_value(True)

    assert "aprs.call_sign" in mapping
    mapping["aprs.call_sign"].value.set_value("CALL99")

    assert "dtmf.current_id" in mapping
    mapping["dtmf.current_id"].value.set_value("12345")

    assert "dtmf.ptt_mode" in mapping
    mapping["dtmf.ptt_mode"].value.set_value(3)

    assert "dtmf.code_group_1" in mapping
    mapping["dtmf.code_group_1"].value.set_value("654321")

    driver.set_settings(settings)
    image = driver._image
    assert image is not None
    assert image.function is not None
    assert image.aprs is not None
    assert image.dtmf is not None

    assert image.function.values["sql"] == 5
    assert get_function_value(image.function, "sound_tx_end") is True
    assert image.aprs.fields["call_sign"] == "CALL99"
    assert image.dtmf.current_id == "12345"
    assert get_dtmf_ptt_mode(image.dtmf) == 3
    assert get_dtmf_code_group(image.dtmf, 0) == "654321"