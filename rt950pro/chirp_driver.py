"""CHIRP driver integration for the Radtel RT-950 Pro."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from .channel import Bandwidth, ChannelRecord, Modulation, PowerLevel, ToneMode
from .image import CHANNEL_COUNT, CHANNEL_SECTION_BYTES, RadioImage
from .settings_api import (
    SettingsError,
    aprs_keys,
    function_keys,
    get_aprs_value,
    get_dtmf_code_group,
    get_dtmf_current_id,
    get_dtmf_ptt_mode,
    get_function_value,
    set_aprs_value,
    set_dtmf_code_group,
    set_dtmf_current_id,
    set_dtmf_ptt_mode,
    set_function_value,
)
from .transport import CloneSerialTransport, DEFAULT_SEGMENTS

LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CHIRP compatibility layer -------------------------------------------------

# ---------------------------------------------------------------------------

try:  # pragma: no cover - executed when real CHIRP is available
    from chirp import chirp_common, directory, errors, memmap  # type: ignore
    from chirp.settings import (
        RadioSetting,
        RadioSettingGroup,
        RadioSettingValueBoolean,
        RadioSettingValueInteger,
        RadioSettingValueList,
        RadioSettingValueString,
        RadioSettings,
    )

except ImportError:  # pragma: no cover - fallback for local development

    class _Memory:
        def __init__(self) -> None:
            self.number = 0
            self.freq = 0
            self.offset = 0
            self.duplex = ""
            self.tmode = ""
            self.rtone = 0.0
            self.ctone = 0.0
            self.dtcs = 0
            self.dtcs_pol = "N"
            self.mode = "FM"
            self.power = ""
            self.skip = ""
            self.name = ""
            self.empty = False
            self.extra = {}

    class _RadioFeatures:
        def __init__(self) -> None:
            self.has_bank = False
            self.has_bank_names = False
            self.has_name = True
            self.has_ctone = True
            self.has_dtcs = True
            self.has_dtcs_polarity = True
            self.has_mode = True
            self.has_offset = True
            self.has_tuning_step = False
            self.can_delete = True
            self.can_odd_split = True
            self.memory_bounds = (0, 0)
            self.valid_bands = []
            self.valid_duplexes = ["", "+", "-", "split"]
            self.valid_tmodes = ["", "Tone", "TSQL", "DTCS"]
            self.valid_modes = ["FM", "NFM", "AM"]
            self.valid_power_levels = ["Low", "Medium", "High"]
            self.valid_skips = ["", "S"]
            self.valid_name_length = 12

    class _CloneModeRadio:
        VENDOR = ""
        MODEL = ""
        BAUD_RATE = 115200

        def __init__(self, *args, **kwargs) -> None:
            self.pipe = kwargs.get("pipe")

    class _Directory:
        @staticmethod
        def register(cls):
            return cls

    class _Errors:

        class RadioError(Exception):
            pass

    class _MemoryMapBytes(bytearray):
        def get_packed(self):
            return bytes(self)

    class memmap:  # type: ignore
        MemoryMapBytes = _MemoryMapBytes

    class _PowerLevel(str):
        def __new__(cls, label, watts=0.0):
            obj = str.__new__(cls, label)
            obj.watts = watts
            return obj

    class _RadioSettingValue:
        def __init__(self, value=None):
            self._value = value

        def initialize(self):
            pass

        def set_value(self, value):
            self._value = value

        def get_value(self):
            return self._value

        def queue_current(self, value):
            self._value = value

        def __int__(self):
            return int(self._value)

        def __bool__(self):
            return bool(self._value)

        def __str__(self):
            return str(self._value)

    class RadioSettingValueBoolean(_RadioSettingValue):
        def __init__(self, current, mem_vals=(0, 1)):
            super().__init__(bool(current))

        def set_value(self, value):
            super().set_value(bool(value))

    class RadioSettingValueInteger(_RadioSettingValue):
        def __init__(self, minval, maxval, current, step=1):
            self._min = minval
            self._max = maxval
            super().__init__(int(current))

        def set_value(self, value):
            value = int(value)
            if value < self._min or value > self._max:
                raise ValueError
            super().set_value(value)

    class RadioSettingValueList(_RadioSettingValue):
        def __init__(self, choices, current_index=0):
            self.choices = list(choices)
            index = int(current_index) if self.choices else 0
            super().__init__(self.choices[index] if self.choices else None)

        def set_value(self, value):
            if isinstance(value, int):
                if value < 0 or value >= len(self.choices):
                    raise ValueError
                self._value = self.choices[value]
            else:
                if value not in self.choices:
                    raise ValueError
                self._value = value

        def __int__(self):
            if self._value in self.choices:
                return self.choices.index(self._value)
            raise ValueError

    class RadioSettingValueString(_RadioSettingValue):
        def __init__(self, minlength, maxlength, current, autopad=True, charset=None, mem_pad_char=' '):
            self.maxlength = maxlength
            self.autopad = autopad
            self.mem_pad_char = mem_pad_char
            super().__init__(current or "")

        def set_value(self, value):
            value = str(value)
            if len(value) > self.maxlength:
                raise ValueError
            super().set_value(value)

    class RadioSettingGroup:
        def __init__(self, name, label, *elements):
            self.name = name
            self.label = label
            self._children = []
            for element in elements:
                self.append(element)

        def append(self, element):
            self._children.append(element)

        def __iter__(self):
            return iter(self._children)

        def walk(self):
            for child in self._children:
                if isinstance(child, RadioSetting):
                    yield child
                elif isinstance(child, RadioSettingGroup):
                    yield from child.walk()

    class RadioSetting(RadioSettingGroup):
        def __init__(self, name, label, value):
            super().__init__(name, label, value)
            self._value = value
            self._apply = None
        @property
        def value(self):
            return self._value

        def set_apply_callback(self, callback, *args):
            self._apply = lambda: callback(self, *args)

        def has_apply_callback(self):
            return self._apply is not None

        def run_apply_callback(self):
            if self._apply:
                self._apply()

    class RadioSettings(RadioSettingGroup):
        def __init__(self, *groups):
            super().__init__('root', 'root', *groups)

    class chirp_common:  # type: ignore
        Memory = _Memory
        RadioFeatures = _RadioFeatures
        CloneModeRadio = _CloneModeRadio
        PowerLevel = _PowerLevel
    directory = _Directory()  # type: ignore
    errors = _Errors()  # type: ignore

    class settings:  # type: ignore
        RadioSettings = RadioSettings
        RadioSettingGroup = RadioSettingGroup
        RadioSetting = RadioSetting
        RadioSettingValueBoolean = RadioSettingValueBoolean
        RadioSettingValueInteger = RadioSettingValueInteger
        RadioSettingValueList = RadioSettingValueList
        RadioSettingValueString = RadioSettingValueString
    RadioSettings = RadioSettings
    RadioSettingGroup = RadioSettingGroup
    RadioSetting = RadioSetting
    RadioSettingValueBoolean = RadioSettingValueBoolean
    RadioSettingValueInteger = RadioSettingValueInteger
    RadioSettingValueList = RadioSettingValueList
    RadioSettingValueString = RadioSettingValueString

# ---------------------------------------------------------------------------
# Helper utilities ----------------------------------------------------------

# ---------------------------------------------------------------------------

_SEGMENT_LENGTH = sum(segment.length for segment in DEFAULT_SEGMENTS)

_CHIRP_POWER_LEVELS = [
    chirp_common.PowerLevel('Low', watts=1.0),
    chirp_common.PowerLevel('Medium', watts=5.0),
    chirp_common.PowerLevel('High', watts=10.0),
]

_POWER_ENUM_TO_CHIRP = {
    PowerLevel.LOW: _CHIRP_POWER_LEVELS[0],
    PowerLevel.MEDIUM: _CHIRP_POWER_LEVELS[1],
    PowerLevel.HIGH: _CHIRP_POWER_LEVELS[2],
}

_POWER_LABEL_TO_ENUM = {str(level).upper(): enum for enum, level in _POWER_ENUM_TO_CHIRP.items()}

_FUNCTION_UI = {
    'sql': {'label': 'Squelch Level', 'type': 'int', 'min': 0, 'max': 9},
    'save_mode': {'label': 'Battery Save', 'type': 'int', 'min': 0, 'max': 3},
    'vox': {'label': 'VOX Gain', 'type': 'int', 'min': 0, 'max': 9},
    'vox_delay': {'label': 'VOX Delay', 'type': 'int', 'min': 0, 'max': 9},
    'auto_backlight': {'label': 'Auto Backlight', 'type': 'int', 'min': 0, 'max': 9},
    'tot': {'label': 'Time-out Timer', 'type': 'int', 'min': 0, 'max': 9},
    'beep_prompt': {'label': 'Key Beep', 'type': 'bool'},
    'voice_prompt': {'label': 'Voice Prompt', 'type': 'enum', 'choices': [('Off', 0), ('Chinese', 1), ('English', 2)]},
    'language': {'label': 'Menu Language', 'type': 'enum', 'choices': [('Chinese', 0), ('English', 1), ('Other', 2)]},
    'dtmf_mode': {'label': 'DTMF Mode', 'type': 'enum', 'choices': [('Off', 0), ('DT-ST', 1), ('ANI-ID', 2), ('DTMF', 3)]},
    'scan_mode': {'label': 'Scan Mode', 'type': 'enum', 'choices': [('Time', 0), ('Carrier', 1), ('Search', 2)]},
    'ptt_id': {'label': 'PTT ID', 'type': 'enum', 'choices': [('Off', 0), ('BOT', 1), ('EOT', 2), ('Both', 3)]},
    'auto_key_lock': {'label': 'Auto Key Lock', 'type': 'bool'},
    'alarm_mode': {'label': 'Alarm Mode', 'type': 'enum', 'choices': [('Local', 0), ('Remote', 1), ('Tone', 2)]},
    'alarm_sound': {'label': 'Alarm Sound', 'type': 'enum', 'choices': [('Off', 0), ('Type 1', 1), ('Type 2', 2)]},
    'tail_noise_clear': {'label': 'Tail Noise Clear', 'type': 'bool'},
    'pass_repeater_noise_clear': {'label': 'Repeater Noise Clear', 'type': 'bool'},
    'sound_tx_end': {'label': 'Roger Beep', 'type': 'bool'},
    'fm_radio': {'label': 'FM Radio', 'type': 'bool'},
    'lock_keyboard': {'label': 'Keypad Lock', 'type': 'bool'},
    'power_on_message': {'label': 'Power-on Message', 'type': 'enum', 'choices': [('Full', 0), ('Message', 1), ('Voltage', 2)]},
    'bt_write_switch': {'label': 'Bluetooth Enable', 'type': 'bool'},
    'vox_switch': {'label': 'VOX Enable', 'type': 'bool'},
}

_APRS_UI = {
    'aprs_switch': {'label': 'APRS Enable', 'type': 'bool'},
    'gps_switch': {'label': 'GPS Enable', 'type': 'bool'},
    'call_sign': {'label': 'Callsign', 'type': 'string', 'length': 6},
    'ssid': {'label': 'SSID', 'type': 'enum', 'choices': [(str(i), i) for i in range(16)]},
    'aprs_priority': {'label': 'Priority', 'type': 'enum', 'choices': [('Low', 0), ('Normal', 1), ('High', 2)]},
    'data_tx_delay': {'label': 'Data TX Delay', 'type': 'int', 'min': 0, 'max': 9},
    'aprs_decode_prompt_tone': {'label': 'RX Prompt Tone', 'type': 'bool'},
    'aprs_rx_auto_popup': {'label': 'RX Auto Popup', 'type': 'bool'},
    'aprs_forward_channel': {'label': 'Forward Channel', 'type': 'enum', 'choices': [(str(i), i) for i in range(16)]},
    'aprs_wait_forward': {'label': 'Forward Wait', 'type': 'int', 'min': 0, 'max': 9},
    'custom_messages': {'label': 'Custom Message', 'type': 'string', 'length': 40},
}

_DTMF_GROUP_LIMIT = 5

_DTMF_ID_MAXLEN = 5

_DTMF_CODE_MAXLEN = 6

_DTMF_MODE_CHOICES = [('Off', 0), ('BOT', 1), ('EOT', 2), ('Both', 3)]

def _build_setting_value(meta, current):
    kind = meta['type']
    if kind == 'bool':
        return RadioSettingValueBoolean(bool(current))
    if kind == 'int':
        minimum = meta.get('min', 0)
        maximum = meta.get('max', minimum)
        active = minimum if current is None else int(current)
        return RadioSettingValueInteger(minimum, maximum, active)
    if kind == 'enum':
        choices = meta['choices']
        labels = [label for label, _ in choices]
        values = [value for _, value in choices]
        active = values[0]
        if current in values:
            active = current
        index = values.index(active)
        return RadioSettingValueList(labels, current_index=index)
    if kind == 'string':
        length = meta['length']
        return RadioSettingValueString(0, length, (current or ''), autopad=False)
    raise SettingsError(f"Unsupported setting type: {kind}")

def _value_as_bool(value_obj):
    if hasattr(value_obj, 'get_value'):
        return bool(value_obj.get_value())
    return bool(value_obj)

def _value_as_int(value_obj, default=0):
    try:
        if hasattr(value_obj, 'get_value'):
            raw = value_obj.get_value()
        else:
            raw = value_obj
        return int(raw)
    except Exception:
        return default

def _value_as_index(value_obj, choices):
    try:
        return int(value_obj)
    except Exception:
        if hasattr(value_obj, 'get_value'):
            raw = value_obj.get_value()
        else:
            raw = value_obj
        labels = [label for label, _ in choices]
        try:
            return labels.index(raw)
        except ValueError:
            return 0

def _value_as_string(value_obj):
    if hasattr(value_obj, 'get_value'):
        raw = value_obj.get_value()
    else:
        raw = value_obj
    return str(raw)

def _create_function_setting(func_settings, key, meta):
    try:
        current = get_function_value(func_settings, key)
    except KeyError:
        LOG.debug('Skipping unknown function key %s', key)
        return None
    value_obj = _build_setting_value(meta, current)
    rsetting = RadioSetting(f'function.{key}', meta['label'], value_obj)
    rsetting.set_apply_callback(_apply_function_setting, func_settings, key, meta)
    return rsetting

def _create_aprs_setting(aprs_settings, key, meta):
    try:
        current = get_aprs_value(aprs_settings, key)
    except KeyError:
        LOG.debug('Skipping unknown APRS key %s', key)
        return None
    value_obj = _build_setting_value(meta, current)
    rsetting = RadioSetting(f'aprs.{key}', meta['label'], value_obj)
    rsetting.set_apply_callback(_apply_aprs_setting, aprs_settings, key, meta)
    return rsetting

def _build_function_group(func_settings):
    group = RadioSettingGroup('function', 'Function Settings')
    for key, meta in _FUNCTION_UI.items():
        setting = _create_function_setting(func_settings, key, meta)
        if setting is not None:
            group.append(setting)
    return group

def _build_aprs_group(aprs_settings):
    group = RadioSettingGroup('aprs', 'APRS Settings')
    for key, meta in _APRS_UI.items():
        setting = _create_aprs_setting(aprs_settings, key, meta)
        if setting is not None:
            group.append(setting)
    return group

def _build_dtmf_group(dtmf_settings):
    group = RadioSettingGroup('dtmf', 'DTMF Settings')
    current_id = get_dtmf_current_id(dtmf_settings)
    value_id = RadioSettingValueString(0, _DTMF_ID_MAXLEN, current_id or '', autopad=False)
    rset_id = RadioSetting('dtmf.current_id', 'Current ID', value_id)
    rset_id.set_apply_callback(_apply_dtmf_id, dtmf_settings)
    group.append(rset_id)
    mode = get_dtmf_ptt_mode(dtmf_settings)
    labels = [label for label, _ in _DTMF_MODE_CHOICES]
    values = [value for _, value in _DTMF_MODE_CHOICES]
    index = values.index(mode) if mode in values else 0
    mode_value = RadioSettingValueList(labels, current_index=index)
    rset_mode = RadioSetting('dtmf.ptt_mode', 'PTT ID Mode', mode_value)
    rset_mode.set_apply_callback(_apply_dtmf_mode, dtmf_settings)
    group.append(rset_mode)
    for idx in range(_DTMF_GROUP_LIMIT):
        try:
            code = get_dtmf_code_group(dtmf_settings, idx)
        except IndexError:
            code = ''
        code_value = RadioSettingValueString(0, _DTMF_CODE_MAXLEN, code or '', autopad=False)
        rset_code = RadioSetting(f'dtmf.code_group_{idx + 1}', f'Code Group {idx + 1}', code_value)
        rset_code.set_apply_callback(_apply_dtmf_group, dtmf_settings, idx)
        group.append(rset_code)
    return group

def _apply_function_setting(rsetting, func_settings, key, meta):
    try:
        kind = meta['type']
        if kind == 'bool':
            set_function_value(func_settings, key, _value_as_bool(rsetting.value))
        elif kind == 'int':
            set_function_value(func_settings, key, _value_as_int(rsetting.value))
        elif kind == 'enum':
            index = _value_as_index(rsetting.value, meta['choices'])
            set_function_value(func_settings, key, meta['choices'][index][1])
        else:
            raise SettingsError(f"Unsupported function setting type {kind}")
    except (SettingsError, KeyError, IndexError, ValueError) as exc:
        raise errors.RadioError(str(exc)) from exc

def _apply_aprs_setting(rsetting, aprs_settings, key, meta):
    try:
        kind = meta['type']
        if kind == 'bool':
            set_aprs_value(aprs_settings, key, _value_as_bool(rsetting.value))
        elif kind == 'int':
            set_aprs_value(aprs_settings, key, _value_as_int(rsetting.value))
        elif kind == 'enum':
            index = _value_as_index(rsetting.value, meta['choices'])
            set_aprs_value(aprs_settings, key, meta['choices'][index][1])
        elif kind == 'string':
            set_aprs_value(aprs_settings, key, _value_as_string(rsetting.value).strip())
        else:
            raise SettingsError(f"Unsupported APRS setting type {kind}")
    except (SettingsError, KeyError, IndexError, ValueError) as exc:
        raise errors.RadioError(str(exc)) from exc

def _apply_dtmf_id(rsetting, dtmf_settings):
    try:
        set_dtmf_current_id(dtmf_settings, _value_as_string(rsetting.value).strip())
    except SettingsError as exc:
        raise errors.RadioError(str(exc)) from exc

def _apply_dtmf_mode(rsetting, dtmf_settings):
    try:
        index = _value_as_index(rsetting.value, _DTMF_MODE_CHOICES)
        set_dtmf_ptt_mode(dtmf_settings, _DTMF_MODE_CHOICES[index][1])
    except SettingsError as exc:
        raise errors.RadioError(str(exc)) from exc

def _apply_dtmf_group(rsetting, dtmf_settings, index):
    try:
        set_dtmf_code_group(dtmf_settings, index, _value_as_string(rsetting.value).strip())
    except (SettingsError, IndexError) as exc:
        raise errors.RadioError(str(exc)) from exc

def _build_clone_payload(image: RadioImage) -> bytes:
    """Compose the raw buffer expected by the radio from ``image``."""
    buffer = image.to_bytes()
    payload = bytearray()
    payload.extend(buffer[:CHANNEL_SECTION_BYTES])
    cursor = CHANNEL_SECTION_BYTES
    for segment in DEFAULT_SEGMENTS[1:]:
        end = cursor + segment.length
        payload.extend(buffer[cursor:end])
        cursor = end
    if len(payload) != _SEGMENT_LENGTH:
        raise ValueError(
            f"Composed payload length {len(payload)} does not match expected {_SEGMENT_LENGTH}"
        )
    return bytes(payload)

@dataclass
class _ToneInfo:
    mode: str = ""
    rtone: float = 0.0
    ctone: float = 0.0
    dtcs: int = 0
    polarity: str = "N"

# ---------------------------------------------------------------------------
# Driver implementation -----------------------------------------------------

# ---------------------------------------------------------------------------

class RT950ProRadio(chirp_common.CloneModeRadio):
    _memsize = 33152
    """RT-950 Pro CHIRP driver."""
    VENDOR = "Radtel"
    MODEL = "RT-950 Pro"
    BAUD_RATE = 115200

    def __init__(self, *args, **kwargs) -> None:
        self._image: Optional[RadioImage] = None
        self._memory_cache: dict[int, chirp_common.Memory] = {}
        super().__init__(*args, **kwargs)
    # ------------------------------------------------------------------
    # CHIRP hooks
    # ------------------------------------------------------------------

    def get_features(self):  # type: ignore[override]
        rf = chirp_common.RadioFeatures()
        rf.memory_bounds = (0, CHANNEL_COUNT - 1)
        rf.valid_bands = [
            (136_000_000, 174_000_000),
            (400_000_000, 480_000_000),
        ]
        rf.has_bank = False
        rf.has_bank_names = False
        rf.has_name = True
        rf.has_ctone = True
        rf.has_dtcs = True
        rf.has_dtcs_polarity = True
        rf.has_mode = True
        rf.has_offset = True
        rf.has_tuning_step = False
        rf.can_delete = True
        rf.can_odd_split = True
        rf.valid_tmodes = ["", "Tone", "TSQL", "DTCS"]
        rf.valid_duplexes = ["", "+", "-", "split"]
        rf.valid_modes = ["FM", "NFM", "AM"]
        rf.valid_power_levels = _CHIRP_POWER_LEVELS
        rf.valid_skips = ["", "S"]
        rf.valid_dtcs_pols = ["NN", "NR", "RN", "RR"]
        rf.valid_dtcs_codes = [0] + [code for code in chirp_common.DTCS_CODES if code != 0]
        rf.valid_tuning_steps = [2.5, 5.0, 6.25, 10.0, 12.5, 25.0]
        rf.valid_characters = chirp_common.CHARSET_ASCII
        rf.valid_name_length = 12
        return rf

    def process_mmap(self):  # type: ignore[override]
        mmap_obj = getattr(self, '_mmap', None)
        if mmap_obj is None:
            self._image = None
            return
        if hasattr(mmap_obj, 'get_packed'):
            data = mmap_obj.get_packed()
        else:
            data = bytes(mmap_obj)
        if not data:
            self._image = None
            return
        try:
            self._image = RadioImage.from_bytes(data)
        except ValueError as exc:
            raise errors.RadioError(f'Failed to parse memory map: {exc}') from exc
        self._memory_cache.clear()

    def sync_in(self):  # type: ignore[override]
        if self.pipe is None:
            raise errors.RadioError("Serial pipe not initialised")
        transport = CloneSerialTransport(self.pipe, logger=LOG)
        try:
            raw = transport.read_clone()
        except Exception as exc:
            raise errors.RadioError(f'Clone read failed: {exc}') from exc
        self._image = RadioImage.from_bytes(raw)
        self._mmap = memmap.MemoryMapBytes(raw)
        self._metadata = {}
        self._memory_cache.clear()

    def sync_out(self):  # type: ignore[override]
        if self.pipe is None:
            raise errors.RadioError("Serial pipe not initialised")
        if self._image is None:
            raise errors.RadioError("No image loaded")
        payload = _build_clone_payload(self._image)
        transport = CloneSerialTransport(self.pipe, logger=LOG)
        try:
            transport.write_clone(payload)
        except Exception as exc:
            raise errors.RadioError(f'Clone write failed: {exc}') from exc
        self._mmap = memmap.MemoryMapBytes(payload)
        self._metadata = {}
    # ------------------------------------------------------------------
    # Settings integration
    # ------------------------------------------------------------------

    def get_settings(self):  # type: ignore[override]
        image = self._require_image()
        groups = []
        if getattr(image, 'function', None) is not None:
            groups.append(_build_function_group(image.function))
        if getattr(image, 'aprs', None) is not None:
            groups.append(_build_aprs_group(image.aprs))
        if getattr(image, 'dtmf', None) is not None:
            groups.append(_build_dtmf_group(image.dtmf))
        if not groups:
            return RadioSettings()
        return RadioSettings(*groups)

    def set_settings(self, settings):  # type: ignore[override]
        self._require_image()
        if not isinstance(settings, RadioSettings):
            raise errors.RadioError('Unexpected settings container')
        walker = getattr(settings, 'walk', None)
        if walker is None:
            raise errors.RadioError('Settings container missing walk()')
        for element in walker():
            if isinstance(element, RadioSetting) and element.has_apply_callback():
                element.run_apply_callback()
        self._memory_cache.clear()
    # ------------------------------------------------------------------
    # Memory translation helpers
    # ------------------------------------------------------------------

    def _require_image(self) -> RadioImage:
        if self._image is None:
            raise errors.RadioError("Memory image not loaded")
        return self._image

    def get_memory(self, number: int):  # type: ignore[override]
        image = self._require_image()
        if not (0 <= number < len(image.channels)):
            raise errors.RadioError(f"Memory index {number} out of range")
        if number in self._memory_cache:
            return self._memory_cache[number]
        channel = image.channels[number]
        mem = self._channel_to_memory(number, channel)
        self._memory_cache[number] = mem
        return mem

    def set_memory(self, mem):  # type: ignore[override]
        image = self._require_image()
        if not (0 <= mem.number < len(image.channels)):
            raise errors.RadioError(f"Memory index {mem.number} out of range")
        channel = image.channels[mem.number]
        self._apply_memory_to_channel(mem, channel)
        sanitized = self._channel_to_memory(mem.number, channel)
        for attr, value in sanitized.__dict__.items():
            if attr.startswith('_'):
                continue
            object.__setattr__(mem, attr, value)
        self._memory_cache[mem.number] = sanitized
    # ------------------------------------------------------------------
    # Conversion routines
    # ------------------------------------------------------------------

    def _channel_to_memory(self, number: int, channel: ChannelRecord):
        mem = chirp_common.Memory()
        mem.number = number
        if channel.rx_hz is None:
            mem.empty = True
            return mem
        mem.freq = channel.rx_hz
        mem.empty = False
        mem.name = (channel.name or "").strip()
        self._apply_offset(mem, channel)
        self._apply_tones(mem, channel)
        if channel.rx_modulation is Modulation.AM:
            mem.mode = "AM"
        else:
            mem.mode = "NFM" if channel.bandwidth is Bandwidth.NARROW else "FM"
        mem.power = _POWER_ENUM_TO_CHIRP.get(channel.power, _CHIRP_POWER_LEVELS[0])
        mem.skip = "" if channel.scan_add else "S"
        mem.extra = {"scrambler": channel.scrambler, "encryption": channel.encryption}
        return mem

    def _apply_offset(self, mem, channel: ChannelRecord) -> None:
        if channel.tx_hz is None or channel.tx_hz == channel.rx_hz:
            mem.duplex = ""
            mem.offset = 0
            return
        diff = channel.tx_hz - channel.rx_hz
        if diff > 0 and channel.tx_hz == channel.rx_hz + diff:
            mem.duplex = "+"
            mem.offset = abs(diff)
        elif diff < 0 and channel.tx_hz == channel.rx_hz + diff:
            mem.duplex = "-"
            mem.offset = abs(diff)
        else:
            mem.duplex = "split"
            mem.offset = channel.tx_hz

    def _apply_tones(self, mem, channel: ChannelRecord) -> None:
        tx = channel.tx_tone
        rx = channel.rx_tone
        mem.dtcs = 0
        mem.rx_dtcs = 0
        mem.dtcs_polarity = "NN"
        if tx.is_off and rx.is_off:
            mem.tmode = ""
            return
        if tx.mode is ToneMode.CTCSS and rx.is_off:
            mem.tmode = "Tone"
            mem.rtone = tx.ctcss_hz or 0.0
            return
        if tx.mode is ToneMode.CTCSS and rx.mode is ToneMode.CTCSS:
            mem.tmode = "TSQL"
            tone = tx.ctcss_hz or rx.ctcss_hz or 0.0
            mem.rtone = tone
            mem.ctone = tone
            return
        if tx.mode is ToneMode.DCS and tx.dcs_code is not None:
            tx_pol = (tx.dcs_polarity or "N").upper()
            if rx.mode is ToneMode.DCS and rx.dcs_code is not None:
                mem.tmode = "DTCS"
                mem.dtcs = tx.dcs_code
                mem.rx_dtcs = rx.dcs_code
                rx_pol = (rx.dcs_polarity or "N").upper()
            else:
                mem.tmode = "DTCS"
                mem.dtcs = tx.dcs_code
                mem.rx_dtcs = tx.dcs_code
                rx_pol = "N"
            mem.dtcs_polarity = tx_pol + rx_pol
            return
        if rx.mode is ToneMode.DCS and rx.dcs_code is not None:
            mem.tmode = "DTCS"
            mem.dtcs = rx.dcs_code
            mem.rx_dtcs = rx.dcs_code
            mem.dtcs_polarity = "N" + (rx.dcs_polarity or "N").upper()
            return
        mem.tmode = ""

    def _apply_memory_to_channel(self, mem, channel: ChannelRecord) -> None:
        if getattr(mem, "empty", False):
            channel.rx_hz = None
            channel.tx_hz = None
            channel.name = ""
            return
        channel.rx_hz = mem.freq
        if mem.duplex == "+":
            channel.tx_hz = mem.freq + mem.offset
        elif mem.duplex == "-":
            channel.tx_hz = mem.freq - mem.offset
        elif mem.duplex == "split":
            channel.tx_hz = mem.offset
        else:
            channel.tx_hz = mem.freq
        channel.name = (mem.name or "").strip()
        self._update_tones_from_memory(mem, channel)

        extras = getattr(mem, "extra", None) or {}
        scrambler = extras.get("scrambler") if isinstance(extras, dict) else None
        encryption = extras.get("encryption") if isinstance(extras, dict) else None
        channel.scrambler = scrambler if isinstance(scrambler, int) else None
        if channel.scrambler is None or channel.scrambler < 0 or channel.scrambler > 8:
            channel.scrambler = 0
        channel.encryption = encryption if isinstance(encryption, int) else None
        if channel.encryption not in (0, 1):
            channel.encryption = 0
        channel.learn_fhss = False
        channel.fhss_code = None

        mode = (mem.mode or "").upper()
        if mode not in {"AM", "FM", "NFM"}:
            mode = "AM" if channel.rx_modulation is Modulation.AM else "FM"
        if mode == "AM":
            channel.rx_modulation = Modulation.AM
            channel.bandwidth = Bandwidth.WIDE
        else:
            channel.rx_modulation = Modulation.FM
            channel.bandwidth = Bandwidth.NARROW if mode == "NFM" else Bandwidth.WIDE
        if isinstance(mem.power, chirp_common.PowerLevel):
            key = str(mem.power).upper()
        elif isinstance(mem.power, str) and mem.power:
            key = mem.power.upper()
        else:
            key = None
        if key and key in _POWER_LABEL_TO_ENUM:
            channel.power = _POWER_LABEL_TO_ENUM[key]
        channel.scan_add = mem.skip != "S"

    def _update_tones_from_memory(self, mem, channel: ChannelRecord) -> None:
        if mem.tmode == "":
            channel.tx_tone = channel.tx_tone.__class__.off()
            channel.rx_tone = channel.rx_tone.__class__.off()
        elif mem.tmode == "Tone":
            channel.tx_tone = channel.tx_tone.__class__.ctcss(mem.rtone)
            channel.rx_tone = channel.rx_tone.__class__.off()
        elif mem.tmode == "TSQL":
            tone = mem.ctone or mem.rtone
            channel.tx_tone = channel.tx_tone.__class__.ctcss(mem.rtone or tone)
            channel.rx_tone = channel.rx_tone.__class__.ctcss(mem.ctone or tone)
        elif mem.tmode == "DTCS":
            polarity = getattr(mem, "dtcs_polarity", "NN") or "NN"
            tx_pol = polarity[0] if len(polarity) >= 1 else "N"
            rx_pol = polarity[1] if len(polarity) >= 2 else tx_pol
            tx_code = getattr(mem, "dtcs", 0) or 0
            rx_code = getattr(mem, "rx_dtcs", tx_code) or tx_code
            if tx_code:
                channel.tx_tone = channel.tx_tone.__class__.dcs(tx_code, tx_pol)
            else:
                channel.tx_tone = channel.tx_tone.__class__.off()
            if rx_code:
                channel.rx_tone = channel.rx_tone.__class__.dcs(rx_code, rx_pol)
            else:
                channel.rx_tone = channel.rx_tone.__class__.off()

__all__ = ["RT950ProRadio"]
