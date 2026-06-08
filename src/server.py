"""
mixxx-mcp — MCP server for Mixxx DJ Software
Transport: stdio (local) | Streamable HTTP (remote)

Mixxx integration layers:
  1. MIDI (rtmidi virtual port)  → send control messages to Mixxx
  2. OSC  (python-osc server)    → receive live state from Mixxx

Control Object anatomy:
  group  → "[Channel1]", "[Channel2]", "[Master]", "[Playlist]", ...
  key    → "play", "volume", "rate", "cue_default", "crossfader", ...
"""

import asyncio
import json
import threading
import time
import logging
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

from mcp.server.fastmcp import FastMCP
from .midi_bridge import MidiBridge
from .osc_listener import OscStateStore
from .controls import CONTROL_MAP, MIDI_CC_MAP, validate_group, resolve_channel

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
log = logging.getLogger("mixxx-mcp")

# ─── Global singletons ────────────────────────────────────────────────────────
midi = MidiBridge()
state = OscStateStore()

mcp = FastMCP(
    name="mixxx-mcp",
    instructions=(
        "Control and monitor Mixxx DJ Software. "
        "Supports deck transport, mixing, EQ, effects, loops, hotcues, and library."
    ),
)


# ══════════════════════════════════════════════════════════════════════════════
# TRANSPORT — Deck playback
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
def play(deck: int) -> dict:
    """
    Start playback on a deck.
    Args:
        deck: Deck number (1-4).
    """
    group = resolve_channel(deck)
    midi.send_control(group, "play", 1.0)
    return {"ok": True, "deck": deck, "action": "play"}


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
def stop(deck: int) -> dict:
    """
    Stop playback on a deck.
    Args:
        deck: Deck number (1-4).
    """
    group = resolve_channel(deck)
    midi.send_control(group, "play", 0.0)
    return {"ok": True, "deck": deck, "action": "stop"}


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
def cue(deck: int) -> dict:
    """
    Trigger CUE on a deck (jumps to cue point if stopped, or sets cue if playing).
    Args:
        deck: Deck number (1-4).
    """
    group = resolve_channel(deck)
    midi.send_control(group, "cue_default", 1.0)
    return {"ok": True, "deck": deck, "action": "cue"}


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
)
def sync(deck: int) -> dict:
    """
    Toggle sync mode on a deck (BPM sync to sync leader).
    Args:
        deck: Deck number (1-4).
    """
    group = resolve_channel(deck)
    current = state.get(group, "sync_enabled") or 0.0
    midi.send_control(group, "sync_enabled", 0.0 if current else 1.0)
    return {"ok": True, "deck": deck, "sync_enabled": not bool(current)}


# ══════════════════════════════════════════════════════════════════════════════
# MIXING — Volume, crossfader, EQ, gain
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
def set_volume(deck: int, value: float) -> dict:
    """
    Set the channel fader volume for a deck.
    Args:
        deck: Deck number (1-4).
        value: Volume level 0.0 (off) to 1.0 (unity). Default 1.0.
    """
    if not 0.0 <= value <= 1.0:
        return {"ok": False, "error": "value must be 0.0–1.0"}
    group = resolve_channel(deck)
    midi.send_control(group, "volume", value)
    return {"ok": True, "deck": deck, "volume": value}


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
def set_crossfader(value: float) -> dict:
    """
    Set the crossfader position.
    Args:
        value: -1.0 (full left / Deck 1) to 1.0 (full right / Deck 2). 0.0 = center.
    """
    if not -1.0 <= value <= 1.0:
        return {"ok": False, "error": "value must be -1.0–1.0"}
    midi.send_control("[Master]", "crossfader", value)
    return {"ok": True, "crossfader": value}


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
def set_eq(deck: int, low: Optional[float] = None, mid: Optional[float] = None, high: Optional[float] = None) -> dict:
    """
    Set EQ bands for a deck. Pass only the bands you want to change.
    Args:
        deck: Deck number (1-4).
        low: Low band gain, 0.0–4.0, 1.0 = unity.
        mid: Mid band gain, 0.0–4.0.
        high: High band gain, 0.0–4.0.
    """
    group = resolve_channel(deck)
    result = {"ok": True, "deck": deck}
    for band, val in [("filterLow", low), ("filterMid", mid), ("filterHigh", high)]:
        if val is not None:
            if not 0.0 <= val <= 4.0:
                return {"ok": False, "error": f"{band} must be 0.0–4.0"}
            midi.send_control(group, band, val)
            result[band] = val
    return result


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
def set_pregain(deck: int, value: float) -> dict:
    """
    Set pre-gain (trim) on a deck. 1.0 = unity.
    Args:
        deck: Deck number (1-4).
        value: 0.0–4.0
    """
    if not 0.0 <= value <= 4.0:
        return {"ok": False, "error": "value must be 0.0–4.0"}
    group = resolve_channel(deck)
    midi.send_control(group, "pregain", value)
    return {"ok": True, "deck": deck, "pregain": value}


# ══════════════════════════════════════════════════════════════════════════════
# RATE / PITCH
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
def set_rate(deck: int, value: float) -> dict:
    """
    Set the tempo pitch slider (-1.0 to 1.0). 0.0 = original tempo.
    Actual BPM change depends on rateRange setting in Mixxx preferences.
    Args:
        deck: Deck number (1-4).
        value: -1.0 (slowest) to 1.0 (fastest).
    """
    if not -1.0 <= value <= 1.0:
        return {"ok": False, "error": "value must be -1.0 to 1.0"}
    group = resolve_channel(deck)
    midi.send_control(group, "rate", value)
    return {"ok": True, "deck": deck, "rate": value}


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
)
def nudge_tempo(deck: int, direction: str, size: str = "small") -> dict:
    """
    Nudge tempo up or down by a step.
    Args:
        deck: Deck number (1-4).
        direction: "up" or "down"
        size: "small" or "large" (default "small", roughly 0.5% vs 2%)
    """
    if direction not in ("up", "down"):
        return {"ok": False, "error": "direction must be 'up' or 'down'"}
    if size not in ("small", "large"):
        return {"ok": False, "error": "size must be 'small' or 'large'"}
    group = resolve_channel(deck)
    key = f"rate_perm_{direction}_{size}" if size == "small" else f"rate_perm_{direction}"
    midi.send_control(group, key, 1.0)
    return {"ok": True, "deck": deck, "nudge": f"{direction}_{size}"}


# ══════════════════════════════════════════════════════════════════════════════
# LOOPS
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
)
def set_loop(deck: int, beats: float) -> dict:
    """
    Activate a beat loop of the specified length.
    Args:
        deck: Deck number (1-4).
        beats: Loop size in beats. Common: 0.125, 0.25, 0.5, 1, 2, 4, 8, 16, 32.
    """
    group = resolve_channel(deck)
    midi.send_control(group, "beatloop_size", beats)
    midi.send_control(group, "beatloop_activate", 1.0)
    return {"ok": True, "deck": deck, "loop_beats": beats}


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
def exit_loop(deck: int) -> dict:
    """
    Deactivate any active loop on a deck.
    Args:
        deck: Deck number (1-4).
    """
    group = resolve_channel(deck)
    midi.send_control(group, "reloop_toggle", 0.0)
    return {"ok": True, "deck": deck, "action": "exit_loop"}


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
)
def halve_loop(deck: int) -> dict:
    """Halve the current loop length."""
    group = resolve_channel(deck)
    midi.send_control(group, "loop_halve", 1.0)
    return {"ok": True, "deck": deck, "action": "loop_halve"}


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
)
def double_loop(deck: int) -> dict:
    """Double the current loop length."""
    group = resolve_channel(deck)
    midi.send_control(group, "loop_double", 1.0)
    return {"ok": True, "deck": deck, "action": "loop_double"}


# ══════════════════════════════════════════════════════════════════════════════
# HOTCUES
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
def set_hotcue(deck: int, slot: int) -> dict:
    """
    Set a hotcue at the current playback position.
    Args:
        deck: Deck number (1-4).
        slot: Hotcue slot number (1-8).
    """
    if not 1 <= slot <= 8:
        return {"ok": False, "error": "slot must be 1–8"}
    group = resolve_channel(deck)
    midi.send_control(group, f"hotcue_{slot}_set", 1.0)
    return {"ok": True, "deck": deck, "hotcue": slot, "action": "set"}


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
)
def goto_hotcue(deck: int, slot: int) -> dict:
    """
    Jump to a hotcue position.
    Args:
        deck: Deck number (1-4).
        slot: Hotcue slot number (1-8).
    """
    if not 1 <= slot <= 8:
        return {"ok": False, "error": "slot must be 1–8"}
    group = resolve_channel(deck)
    midi.send_control(group, f"hotcue_{slot}_goto", 1.0)
    return {"ok": True, "deck": deck, "hotcue": slot, "action": "goto"}


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True}
)
def clear_hotcue(deck: int, slot: int) -> dict:
    """
    Clear a hotcue slot.
    Args:
        deck: Deck number (1-4).
        slot: Hotcue slot number (1-8).
    """
    if not 1 <= slot <= 8:
        return {"ok": False, "error": "slot must be 1–8"}
    group = resolve_channel(deck)
    midi.send_control(group, f"hotcue_{slot}_clear", 1.0)
    return {"ok": True, "deck": deck, "hotcue": slot, "action": "clear"}


# ══════════════════════════════════════════════════════════════════════════════
# BEATJUMP
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
)
def beatjump(deck: int, beats: float) -> dict:
    """
    Jump forward or backward by N beats.
    Args:
        deck: Deck number (1-4).
        beats: Number of beats. Positive = forward, negative = backward.
               Common values: ±1, ±2, ±4, ±8, ±16, ±32.
    """
    group = resolve_channel(deck)
    midi.send_control(group, "beatjump_size", abs(beats))
    key = "beatjump_forward" if beats > 0 else "beatjump_backward"
    midi.send_control(group, key, 1.0)
    return {"ok": True, "deck": deck, "beatjump": beats}


# ══════════════════════════════════════════════════════════════════════════════
# STATE / READ
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
def get_deck_state(deck: int) -> dict:
    """
    Read all known live state for a deck from OSC telemetry.
    Returns playing, BPM, position, volume, loop, sync, and loaded track info.
    Args:
        deck: Deck number (1-4).
    """
    group = resolve_channel(deck)
    keys = [
        "play", "bpm", "playposition", "volume", "pregain",
        "filterLow", "filterMid", "filterHigh",
        "rate", "sync_enabled", "loop_enabled", "beatloop_size",
        "track_artist", "track_title", "duration", "track_samplerate",
    ]
    result = {"deck": deck, "group": group, "state": {}}
    for k in keys:
        v = state.get(group, k)
        if v is not None:
            result["state"][k] = v
    result["_source"] = "osc" if result["state"] else "no_data"
    return result


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
def get_mixer_state() -> dict:
    """
    Read master mixer state: crossfader, master volume, headphone volume, BPM.
    """
    keys = ["crossfader", "volume", "headVolume", "headMix", "latency"]
    result = {}
    for k in keys:
        v = state.get("[Master]", k)
        if v is not None:
            result[k] = v
    return {"ok": True, "master": result}


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
def get_all_state() -> dict:
    """
    Dump the entire cached OSC state for all groups. Useful for debugging.
    """
    return {"ok": True, "state": state.snapshot()}


# ══════════════════════════════════════════════════════════════════════════════
# RAW CONTROL — escape hatch for any Mixxx control
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
)
def send_control(group: str, key: str, value: float) -> dict:
    """
    Send any Mixxx control object value directly.
    Use this for controls not covered by dedicated tools.
    Reference: https://manual.mixxx.org/latest/en/chapters/appendix/mixxx_controls.html
    Args:
        group: Control group e.g. "[Channel1]", "[Master]", "[EffectRack1_EffectUnit1]"
        key: Control key e.g. "play", "volume", "crossfader"
        value: Float value to set.
    """
    try:
        validate_group(group)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    midi.send_control(group, key, value)
    return {"ok": True, "group": group, "key": key, "value": value}


# ══════════════════════════════════════════════════════════════════════════════
# EFFECTS
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
def toggle_effect(unit: int, effect: int, enabled: bool) -> dict:
    """
    Enable or disable a specific effect within an effect unit.
    Args:
        unit: Effect unit number (1-4).
        effect: Effect slot number (1-3).
        enabled: True to enable, False to disable.
    """
    if not 1 <= unit <= 4:
        return {"ok": False, "error": "unit must be 1–4"}
    if not 1 <= effect <= 3:
        return {"ok": False, "error": "effect must be 1–3"}
    group = f"[EffectRack1_EffectUnit{unit}_Effect{effect}]"
    midi.send_control(group, "enabled", 1.0 if enabled else 0.0)
    return {"ok": True, "unit": unit, "effect": effect, "enabled": enabled}


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True}
)
def set_effect_mix(unit: int, value: float) -> dict:
    """
    Set the wet/dry mix for an effect unit.
    Args:
        unit: Effect unit number (1-4).
        value: 0.0 (dry) to 1.0 (full wet).
    """
    if not 0.0 <= value <= 1.0:
        return {"ok": False, "error": "value must be 0.0–1.0"}
    group = f"[EffectRack1_EffectUnit{unit}]"
    midi.send_control(group, "mix", value)
    return {"ok": True, "unit": unit, "mix": value}


# ══════════════════════════════════════════════════════════════════════════════
# Startup
# ══════════════════════════════════════════════════════════════════════════════

def startup():
    midi.connect()
    state.start()
    log.info("mixxx-mcp ready — MIDI connected: %s | OSC listening on %s:%d",
             midi.port_name, state.host, state.port)
