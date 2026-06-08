"""
controls.py — Mixxx control group/key → MIDI CC mapping table

CC numbering scheme (0–127):
  CC 0–19   → Channel1 controls
  CC 20–39  → Channel2 controls
  CC 40–59  → Channel3 controls
  CC 60–79  → Channel4 controls
  CC 80–99  → Master controls
  CC 100–119 → Effect controls
  CC 120–127 → Reserved

The companion Mixxx JS script uses this same table to route
incoming CC messages → engine.setValue() calls.
"""

from typing import Dict, Tuple, Optional

# (group, key) → (cc_number, scale)
# scale: "binary" | "unipolar" | "bipolar" | "eq" | "raw"
MIDI_CC_MAP: Dict[Tuple[str, str], Tuple[int, str]] = {

    # ── Channel 1 ──────────────────────────────────────────────────────────
    ("[Channel1]", "play"):             (0,  "binary"),
    ("[Channel1]", "cue_default"):      (1,  "binary"),
    ("[Channel1]", "sync_enabled"):     (2,  "binary"),
    ("[Channel1]", "volume"):           (3,  "unipolar"),
    ("[Channel1]", "pregain"):          (4,  "eq"),
    ("[Channel1]", "rate"):             (5,  "bipolar"),
    ("[Channel1]", "filterLow"):        (6,  "eq"),
    ("[Channel1]", "filterMid"):        (7,  "eq"),
    ("[Channel1]", "filterHigh"):       (8,  "eq"),
    ("[Channel1]", "beatloop_size"):    (9,  "raw"),
    ("[Channel1]", "beatloop_activate"):(10, "binary"),
    ("[Channel1]", "reloop_toggle"):    (11, "binary"),
    ("[Channel1]", "loop_halve"):       (12, "binary"),
    ("[Channel1]", "loop_double"):      (13, "binary"),
    ("[Channel1]", "hotcue_1_set"):     (14, "binary"),
    ("[Channel1]", "hotcue_1_goto"):    (15, "binary"),
    ("[Channel1]", "hotcue_1_clear"):   (16, "binary"),
    ("[Channel1]", "hotcue_2_set"):     (17, "binary"),
    ("[Channel1]", "hotcue_2_goto"):    (18, "binary"),
    ("[Channel1]", "hotcue_2_clear"):   (19, "binary"),

    # ── Channel 2 ──────────────────────────────────────────────────────────
    ("[Channel2]", "play"):             (20, "binary"),
    ("[Channel2]", "cue_default"):      (21, "binary"),
    ("[Channel2]", "sync_enabled"):     (22, "binary"),
    ("[Channel2]", "volume"):           (23, "unipolar"),
    ("[Channel2]", "pregain"):          (24, "eq"),
    ("[Channel2]", "rate"):             (25, "bipolar"),
    ("[Channel2]", "filterLow"):        (26, "eq"),
    ("[Channel2]", "filterMid"):        (27, "eq"),
    ("[Channel2]", "filterHigh"):       (28, "eq"),
    ("[Channel2]", "beatloop_size"):    (29, "raw"),
    ("[Channel2]", "beatloop_activate"):(30, "binary"),
    ("[Channel2]", "reloop_toggle"):    (31, "binary"),
    ("[Channel2]", "loop_halve"):       (32, "binary"),
    ("[Channel2]", "loop_double"):      (33, "binary"),
    ("[Channel2]", "hotcue_1_set"):     (34, "binary"),
    ("[Channel2]", "hotcue_1_goto"):    (35, "binary"),
    ("[Channel2]", "hotcue_1_clear"):   (36, "binary"),
    ("[Channel2]", "hotcue_2_set"):     (37, "binary"),
    ("[Channel2]", "hotcue_2_goto"):    (38, "binary"),
    ("[Channel2]", "hotcue_2_clear"):   (39, "binary"),

    # ── Channel 3 ──────────────────────────────────────────────────────────
    ("[Channel3]", "play"):             (40, "binary"),
    ("[Channel3]", "cue_default"):      (41, "binary"),
    ("[Channel3]", "sync_enabled"):     (42, "binary"),
    ("[Channel3]", "volume"):           (43, "unipolar"),
    ("[Channel3]", "pregain"):          (44, "eq"),
    ("[Channel3]", "rate"):             (45, "bipolar"),
    ("[Channel3]", "filterLow"):        (46, "eq"),
    ("[Channel3]", "filterMid"):        (47, "eq"),
    ("[Channel3]", "filterHigh"):       (48, "eq"),
    ("[Channel3]", "beatloop_activate"):(49, "binary"),
    ("[Channel3]", "loop_halve"):       (50, "binary"),
    ("[Channel3]", "loop_double"):      (51, "binary"),

    # ── Channel 4 ──────────────────────────────────────────────────────────
    ("[Channel4]", "play"):             (60, "binary"),
    ("[Channel4]", "cue_default"):      (61, "binary"),
    ("[Channel4]", "sync_enabled"):     (62, "binary"),
    ("[Channel4]", "volume"):           (63, "unipolar"),
    ("[Channel4]", "pregain"):          (64, "eq"),
    ("[Channel4]", "rate"):             (65, "bipolar"),
    ("[Channel4]", "filterLow"):        (66, "eq"),
    ("[Channel4]", "filterMid"):        (67, "eq"),
    ("[Channel4]", "filterHigh"):       (68, "eq"),
    ("[Channel4]", "beatloop_activate"):(69, "binary"),
    ("[Channel4]", "loop_halve"):       (70, "binary"),
    ("[Channel4]", "loop_double"):      (71, "binary"),

    # ── Master ─────────────────────────────────────────────────────────────
    ("[Master]", "crossfader"):         (80, "bipolar"),
    ("[Master]", "volume"):             (81, "unipolar"),
    ("[Master]", "headVolume"):         (82, "unipolar"),
    ("[Master]", "headMix"):            (83, "bipolar"),
    ("[Master]", "balance"):            (84, "bipolar"),

    # ── Effects ────────────────────────────────────────────────────────────
    ("[EffectRack1_EffectUnit1]", "mix"):       (100, "unipolar"),
    ("[EffectRack1_EffectUnit2]", "mix"):       (101, "unipolar"),
    ("[EffectRack1_EffectUnit3]", "mix"):       (102, "unipolar"),
    ("[EffectRack1_EffectUnit4]", "mix"):       (103, "unipolar"),
    ("[EffectRack1_EffectUnit1_Effect1]", "enabled"): (104, "binary"),
    ("[EffectRack1_EffectUnit1_Effect2]", "enabled"): (105, "binary"),
    ("[EffectRack1_EffectUnit1_Effect3]", "enabled"): (106, "binary"),

    # ── Rate nudge (wildcard — same CC slot, different channel groups) ─────
    ("*", "rate_perm_up_small"):        (110, "binary"),
    ("*", "rate_perm_down_small"):      (111, "binary"),
    ("*", "rate_perm_up"):              (112, "binary"),
    ("*", "rate_perm_down"):            (113, "binary"),
    ("*", "beatjump_size"):             (114, "raw"),
    ("*", "beatjump_forward"):          (115, "binary"),
    ("*", "beatjump_backward"):         (116, "binary"),
}

# ── Hotcue slots 3–8 (auto-generated) ────────────────────────────────────────
_HOTCUE_BASE_CH1 = 17   # cc 17–28 for slots 2–8 on Ch1
_HOTCUE_BASE_CH2 = 37   # cc 37–48 for slots 2–8 on Ch2
_HOTCUE_STEP = 3        # set, goto, clear per slot

for _slot in range(3, 9):
    for _ch, _base in [(1, 14), (2, 34)]:
        _offset = (_slot - 1) * _HOTCUE_STEP
        # Note: slots 1–2 already mapped above; slot 3+ overflow into 120+ range
        # Use a separate CC block 50–79 for extended hotcues
        _cc = 50 + ((_ch - 1) * 18) + ((_slot - 3) * 3)
        MIDI_CC_MAP[(f"[Channel{_ch}]", f"hotcue_{_slot}_set")]   = (_cc,     "binary")
        MIDI_CC_MAP[(f"[Channel{_ch}]", f"hotcue_{_slot}_goto")]  = (_cc + 1, "binary")
        MIDI_CC_MAP[(f"[Channel{_ch}]", f"hotcue_{_slot}_clear")] = (_cc + 2, "binary")


# ── Reverse lookup: CC → (group, key) ────────────────────────────────────────
REVERSE_MAP: Dict[int, Tuple[str, str]] = {
    cc: (group, key)
    for (group, key), (cc, _) in MIDI_CC_MAP.items()
}

# ── Validation ────────────────────────────────────────────────────────────────
VALID_GROUP_PREFIXES = [
    "[Channel", "[Sampler", "[Master]", "[Playlist]",
    "[PreviewDeck", "[EffectRack", "[Microphone",
]

def validate_group(group: str):
    if not any(group.startswith(p) for p in VALID_GROUP_PREFIXES):
        raise ValueError(
            f"Unknown group '{group}'. Valid prefixes: {VALID_GROUP_PREFIXES}"
        )

def resolve_channel(deck: int) -> str:
    if not 1 <= deck <= 4:
        raise ValueError(f"Deck must be 1–4, got {deck}")
    return f"[Channel{deck}]"


# ── Full control reference (for discoverability) ───────────────────────────────
CONTROL_MAP = {
    "[ChannelN]": {
        "play":              "Binary. 1=play, 0=pause.",
        "cue_default":       "Binary. Trigger CUE action.",
        "sync_enabled":      "Binary. BPM sync on/off.",
        "volume":            "0.0–1.0. Channel fader.",
        "pregain":           "0.0–4.0. Pre-fader gain (trim).",
        "rate":              "-1.0–1.0. Tempo pitch slider.",
        "filterLow":         "0.0–4.0. EQ low band.",
        "filterMid":         "0.0–4.0. EQ mid band.",
        "filterHigh":        "0.0–4.0. EQ high band.",
        "beatloop_size":     "Float. Loop size in beats.",
        "beatloop_activate": "Binary. Activate/deactivate beat loop.",
        "reloop_toggle":     "Binary. Toggle loop on/off.",
        "loop_halve":        "Binary. Halve loop length (trigger).",
        "loop_double":       "Binary. Double loop length (trigger).",
        "hotcue_N_set":      "Binary. Set hotcue N (1–8) at current position.",
        "hotcue_N_goto":     "Binary. Jump to hotcue N.",
        "hotcue_N_clear":    "Binary. Clear hotcue N.",
        "beatjump_size":     "Float. Beatjump size in beats.",
        "beatjump_forward":  "Binary. Jump forward by beatjump_size.",
        "beatjump_backward": "Binary. Jump backward by beatjump_size.",
        "rate_perm_up_small":"Binary. Nudge tempo up small step.",
        "rate_perm_down_small":"Binary. Nudge tempo down small step.",
        "bpm":               "Read-only. Current BPM.",
        "playposition":      "0.0–1.0. Current playback position.",
        "duration":          "Read-only. Track duration in seconds.",
        "track_artist":      "Read-only. Loaded track artist.",
        "track_title":       "Read-only. Loaded track title.",
    },
    "[Master]": {
        "crossfader":  "-1.0–1.0. Crossfader position.",
        "volume":      "0.0–1.0. Master output volume.",
        "headVolume":  "0.0–5.0. Headphone output volume.",
        "headMix":     "-1.0–1.0. Headphone mix (cue vs master).",
        "balance":     "-1.0–1.0. Master balance.",
    },
    "[EffectRack1_EffectUnitN]": {
        "mix":         "0.0–1.0. Wet/dry mix for the effect unit.",
        "enabled":     "Binary. Enable/disable effect unit.",
    },
    "[EffectRack1_EffectUnitN_EffectM]": {
        "enabled":     "Binary. Enable/disable individual effect slot.",
    },
}
