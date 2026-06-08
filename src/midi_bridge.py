"""
midi_bridge.py — Virtual MIDI → Mixxx Control Object bridge

Mixxx listens on a virtual MIDI port for CC messages.
We maintain a lookup table: (group, key) → (channel, cc).
For controls Mixxx doesn't expose via standard MIDI CC,
we build a synthetic controller script that maps the CC to engine.setValue().

Architecture:
  MidiBridge.send_control(group, key, value)
    → normalizes value to 0–127
    → sends rtmidi CC on the virtual port
    → Mixxx controller script receives CC → calls engine.setValue(group, key, normalized_val)
"""

import logging
import os
from typing import Optional

log = logging.getLogger("mixxx-mcp.midi")

# Lazy import — rtmidi optional if using HTTP/OSC-only mode
try:
    import rtmidi
    HAS_RTMIDI = True
except ImportError:
    HAS_RTMIDI = False
    log.warning("python-rtmidi not installed — MIDI bridge disabled. Install: pip install python-rtmidi")


class MidiBridge:
    """
    Manages a virtual MIDI output port.
    Translates (group, key, value) → MIDI CC messages.
    
    The companion Mixxx JS script (mixxx-mcp.js) must be loaded in Mixxx
    → Preferences → Controllers to receive and route these messages.
    """

    PORT_NAME = "mixxx-mcp"
    CHANNEL = 0  # MIDI channel 1 (0-indexed)

    def __init__(self):
        self._out: Optional[object] = None
        self.port_name = self.PORT_NAME
        self._connected = False

    def connect(self):
        if not HAS_RTMIDI:
            log.warning("MIDI bridge unavailable — running in state-read-only mode")
            return
        try:
            self._out = rtmidi.MidiOut()
            # Check if our virtual port already exists
            ports = self._out.get_ports()
            for i, name in enumerate(ports):
                if self.PORT_NAME in name:
                    self._out.open_port(i)
                    self._connected = True
                    self.port_name = name
                    log.info("MIDI: opened existing port '%s'", name)
                    return
            # Create virtual port (macOS/Linux only; Windows needs loopMIDI)
            self._out.open_virtual_port(self.PORT_NAME)
            self._connected = True
            log.info("MIDI: created virtual port '%s'", self.PORT_NAME)
        except Exception as e:
            log.error("MIDI connect failed: %s", e)

    def send_control(self, group: str, key: str, value: float):
        """
        Translate a Mixxx control → MIDI CC and send.
        
        Encoding:
          - Binary controls (play, sync_enabled, etc.): value 0 or 127
          - Float 0.0–1.0 → 0–127
          - Float -1.0–1.0 (crossfader, rate) → 0–127 (center = 64)
          - Float 0.0–4.0 (EQ, pregain) → 0–127 (unity 1.0 = 32)
        """
        from .controls import MIDI_CC_MAP
        
        mapping = MIDI_CC_MAP.get((group, key)) or MIDI_CC_MAP.get(("*", key))
        if mapping is None:
            log.debug("No CC mapping for (%s, %s) — skipped", group, key)
            return

        cc, scale = mapping
        midi_val = _encode(value, scale)
        
        if not self._connected:
            log.debug("[DRY-RUN] MIDI CC %d val %d → (%s, %s = %s)", cc, midi_val, group, key, value)
            return

        try:
            # Control Change: status=0xB0+channel, cc, value
            self._out.send_message([0xB0 | self.CHANNEL, cc, midi_val])
            log.debug("MIDI CC %d val %d → (%s, %s = %s)", cc, midi_val, group, key, value)
        except Exception as e:
            log.error("MIDI send error: %s", e)

    def close(self):
        if self._out:
            self._out.close_port()
            self._connected = False


def _encode(value: float, scale: str) -> int:
    """Normalize float value to 0–127 based on scale type."""
    if scale == "binary":
        return 127 if value else 0
    elif scale == "unipolar":     # 0.0–1.0
        return int(max(0, min(1.0, value)) * 127)
    elif scale == "bipolar":      # -1.0–1.0
        return int((value + 1.0) / 2.0 * 127)
    elif scale == "eq":           # 0.0–4.0, unity=1.0 maps to 32
        return int(max(0, min(4.0, value)) / 4.0 * 127)
    elif scale == "raw":          # pass through 0–127
        return int(max(0, min(127, value)))
    else:
        return int(max(0, min(127, value * 127)))
