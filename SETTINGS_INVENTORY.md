# RT-950 Pro Settings Inventory

This document captures the tunable fields we can surface in a CHIRP driver. Byte offsets are relative to the start of the corresponding clone segment (see `RADIO_PROTOCOL_WIP.md`). Sentinel `0xFF` always means "factory default / unset".

## Function Configuration Block (96 bytes @ segment 0x9000)
| Setting Key | Offset & Bits | Value Notes | Suggested CHIRP Control |
|-------------|---------------|-------------|---------------------------|
| sql | 0x00 | 0–9 (nibble) | `RadioSettingValueInteger(0,9)` |
| save_mode | 0x01 | 0–3 battery-save level | Integer list |
| vox | 0x02 | 0–9 VOX gain | Integer list |
| auto_backlight | 0x03 | 0–9 timeout | Integer list |
| tdr | 0x04 | 0/1 dual-watch | Boolean |
| tot | 0x05 | 0–9 TOT step | Integer list |
| beep_prompt | 0x06 | 0/1 | Boolean |
| voice_prompt | 0x07 | 0 (off) / 1 (Chinese) / 2 (English) | Enum list |
| language | 0x08 | matches CPS language selector | Enum list |
| dtmf_mode | 0x09 | 0–3 | Enum list |
| scan_mode | 0x0A | 0–2 (Time / Carrier / Search) | Enum list |
| ptt_id | 0x0B | 0–3 | Enum list |
| send_id_delay | 0x0C | 0–9 | Integer |
| display_mode_a/b/c | 0x0D/0x0E/0x0F | 0–2 (Channel/Freq/Name) | Enum list |
| auto_key_lock | 0x10 | 0/1 | Boolean |
| alarm_mode | 0x11 | 0–2 | Enum list |
| alarm_sound | 0x12 | 0–2 | Enum list |
| tail_noise_clear | 0x14 | 0/1 | Boolean |
| pass_repeater_noise_clear | 0x15 | 0/1 | Boolean |
| pass_repeater_noise_detect | 0x16 | 0/1 | Boolean |
| sound_tx_end | 0x17 | 0/1 (roger beep) | Boolean |
| current_work_mode | 0x18 | 0–2 (A/B/C) | Enum |
| fm_radio | 0x19 | 0/1 | Boolean |
| work_mode_a/b/c | 0x1A (bits 0-1,2-3,4-5) | 0–3 (Channel/Freq/Name/VFO) | Enum |
| lock_keyboard | 0x1B | 0/1 | Boolean |
| power_on_message | 0x1C | 0–2 | Enum |
| bt_write_switch | 0x1D | 0/1 (BT active) | Boolean |
| rtone | 0x1E | 0–2 (Pilot tone) | Enum |
| vox_delay | 0x20 | 0–9 | Integer |
| timer_menu_quit | 0x21 | 0–9 | Integer |
| weather_channel | 0x25 | channel index | Enum |
| divide_channel | 0x26 | 0/1 | Boolean |
| subaudio_scan_save | 0x27 | 0/1 | Boolean |
| vox_switch | 0x28 | 0/1 | Boolean |
| key_side1_short / long | 0x29 / 0x2A | 0–n (key functions) | Enum |
| key_side2_short / long | 0x2B / 0x2C | 0–n | Enum |
| current_work_area_a/b/c | 0x2D / 0x2E / 0x2F | Zone/bank index | Enum |
| ab_uv_transfer | 0x39 | 0/1 (sync AB display) | Boolean |
| sound_transfer | 0x3A | 0/1 | Boolean |
| key0_long ... key4_long | 0x3B–0x3F | 0–31 key function code | Enum |
| key5_long ... key9_long | 0x40–0x44 | 0–31 key function code | Enum |

> Remaining bytes (0x13, 0x1F, 0x22–0x24, 0x30–0x38) are unused or currently mapped to `None` in our parser.

## DTMF Settings Block (384 bytes @ 0xA000)
| Field | Bytes | Description | Suggested Control |
|-------|-------|-------------|-------------------|
| current_id | 0x00–0x04 | Active DTMF ID (5 digits) | Text (0123456789ABCD*#) |
| ptt_id_mode | 0x06 (low nibble) | 0–3 mode | Enum |
| last_time_send, last_time_stop | 0x07/0x08 (nibble) | Historical; probably informational | Read-only? |
| code_groups[0..22] | 16 bytes each | Stored sequences (up to 6 digits) | Table editor |

## VFO Profiles (3 × 32 bytes @ 0x8000)
Per VFO entry we have:
- `rx_hz`, `offset_hz`
- `rx_tone`, `tx_tone` (ToneSetting)
- `busy_lockout`
- `offset_direction` (0=off,+,-)
- `signalling_group` (scode 0–15)
- `tx_power` (High/Med/Low)
- `scrambler` (0–9)
- `learn_fhss` (bool)
- `bandwidth` (Narrow/Wide)
- `encryption` (0–3)
- `rx_modulation` (FM/AM)
- `freq_band` (0–15 band index)
- `step_freq_index` (0–7 step table)

These can be exposed like the RT-900 driver’s VFO tab (frequency, tone, power, bandwidth, scrambler, offset, modulation).

## Modulation Tables (params 256 bytes @ 0xB000, names 768 bytes @ 0xD000)
Top-level fields:
- `fm_current_channel` (0–15)
- `work_mode` (0/1) – FM vs AM/SSB focus
- `am_current_channel`
- `modulation_mode`
- `am_step_index`, `am_rx_gain`
- `ssb_current_channel`, `ssb_step_index`, `ssb_rx_gain`

Per-channel fields (16 entries):
- FM name + frequency (uint16)
- AM name + frequency
- SSB name + frequency, bandwidth, beat offset (int16)

UI idea: mirror RT-900 “Broadcast/Modulation” editor—list of channels with editable names/frequencies plus global dropdowns for work mode/gain.

## APRS Block (128 bytes @ 0x0000 of APRS segment)
| Field | Offset | Notes |
|-------|--------|-------|
| aprs_switch | 0x00 | 0/1 enable |
| gps_switch | 0x01 | 0/1 |
| latlon_unit | 0x02 | 0=Degrees/min/sec, etc. |
| speed_unit | 0x03 | 0=km/h,1=mph |
| distance_unit | 0x04 | 0=km,1=mi |
| altitude_unit | 0x05 | 0=meters,1=feet |
| time_zone | 0x06 (0–23) |
| north_south | 0x07 (`'N'`/`'S'`) |
| latitude_minute/degree/second | 0x08–0x0A |
| east_west | 0x0B (`'E'`/`'W'`) |
| longitude_minute/degree/second | 0x0C–0x0E |
| altitude | 0x0F–0x10 (signed) |
| call_sign | 0x11–0x16 (ASCII) |
| ssid | 0x17 |
| routing_select | 0x18 |
| my_position | 0x19 |
| radio_symbol | 0x1A |
| user_defined_icon | 0x1B (0–127) |
| aprs_priority | 0x1D |
| data_tx_delay | 0x1E |
| aprs_decode_prompt_tone | 0x20 |
| aprs_rx_auto_popup | 0x21 |
| beacon_tx_type | 0x22 |
| timed_beacon_time | 0x24 |
| mice_type | 0x26 |
| tnc_data_type | 0x27 |
| aprs_forward_channel | 0x28 |
| aprs_forward_routing | 0x29 |
| aprs_wait_forward | 0x2A |
| custom_routing_one | 0x2B–0x30 (ASCII) |
| custom_routing_one_ssid | 0x31 |
| custom_routing_two | 0x32–0x37 |
| custom_routing_two_ssid | 0x38 |
| send_custom_messages | 0x4E |
| custom_messages | 0x4F–0x76 (GB2312 string) |

Many APRS fields align with drop-downs or text inputs already present in the CPS. We can reuse those semantics when defining CHIRP widgets.

## Other Data
- **Channel Records** already cover per-memory power, bandwidth, scrambler, tones, etc.
- **DTMF code groups** may need a specialised editor if we mirror RT-900’s DTMF page.
- **Unknown fields** in function/APRS segments currently remain `None`; decide later whether to expose them or leave hidden.

## Next Steps
1. Confirm ranges/enumerations against CPS UI (screenshots or BinaryFormatter dump).
2. Decide which settings are in-scope for the first monolith release (likely all Function + APRS toggles, plus DTMF ID table and VFO editor).
3. Use this table to implement helper accessors in Phase 2.
