/**
 * mixxx-mcp.js — Mixxx Controller Script v1.1.0
 *
 * Bridges Mixxx ControlObjects ↔ mixxx-mcp Python server via:
 *   WRITE:  Python → MIDI CC → this script → engine.setValue()
 *   READ:   engine.makeConnection() → XHR POST → Python state server
 *
 * Compatible: Mixxx 2.4+ (ES7, QJSEngine, XMLHttpRequest available)
 *
 * Install: %LOCALAPPDATA%\Mixxx\controllers\  (Windows)
 *          ~/.mixxx/controllers/               (Linux)
 *          ~/Library/.../Mixxx/controllers/   (macOS)
 */

"use strict";

// ── Config ────────────────────────────────────────────────────────────────
const MCP_STATE_URL = "http://127.0.0.1:57121/state";
const MCP_DEBOUNCE_MS = 50; // min ms between XHR pushes per control

// ── CC → (group, key, scale) routing table ────────────────────────────────
const CC_ROUTE = {
    // Channel 1
    0:  { group: "[Channel1]", key: "play",              scale: "binary"   },
    1:  { group: "[Channel1]", key: "cue_default",       scale: "binary"   },
    2:  { group: "[Channel1]", key: "sync_enabled",      scale: "binary"   },
    3:  { group: "[Channel1]", key: "volume",            scale: "unipolar" },
    4:  { group: "[Channel1]", key: "pregain",           scale: "eq"       },
    5:  { group: "[Channel1]", key: "rate",              scale: "bipolar"  },
    6:  { group: "[Channel1]", key: "filterLow",         scale: "eq"       },
    7:  { group: "[Channel1]", key: "filterMid",         scale: "eq"       },
    8:  { group: "[Channel1]", key: "filterHigh",        scale: "eq"       },
    9:  { group: "[Channel1]", key: "beatloop_size",     scale: "beatloop" },
    10: { group: "[Channel1]", key: "beatloop_activate", scale: "binary"   },
    11: { group: "[Channel1]", key: "reloop_toggle",     scale: "binary"   },
    12: { group: "[Channel1]", key: "loop_halve",        scale: "binary"   },
    13: { group: "[Channel1]", key: "loop_double",       scale: "binary"   },
    14: { group: "[Channel1]", key: "hotcue_1_set",      scale: "binary"   },
    15: { group: "[Channel1]", key: "hotcue_1_goto",     scale: "binary"   },
    16: { group: "[Channel1]", key: "hotcue_1_clear",    scale: "binary"   },
    17: { group: "[Channel1]", key: "hotcue_2_set",      scale: "binary"   },
    18: { group: "[Channel1]", key: "hotcue_2_goto",     scale: "binary"   },
    19: { group: "[Channel1]", key: "hotcue_2_clear",    scale: "binary"   },
    // Channel 2
    20: { group: "[Channel2]", key: "play",              scale: "binary"   },
    21: { group: "[Channel2]", key: "cue_default",       scale: "binary"   },
    22: { group: "[Channel2]", key: "sync_enabled",      scale: "binary"   },
    23: { group: "[Channel2]", key: "volume",            scale: "unipolar" },
    24: { group: "[Channel2]", key: "pregain",           scale: "eq"       },
    25: { group: "[Channel2]", key: "rate",              scale: "bipolar"  },
    26: { group: "[Channel2]", key: "filterLow",         scale: "eq"       },
    27: { group: "[Channel2]", key: "filterMid",         scale: "eq"       },
    28: { group: "[Channel2]", key: "filterHigh",        scale: "eq"       },
    29: { group: "[Channel2]", key: "beatloop_size",     scale: "beatloop" },
    30: { group: "[Channel2]", key: "beatloop_activate", scale: "binary"   },
    31: { group: "[Channel2]", key: "reloop_toggle",     scale: "binary"   },
    32: { group: "[Channel2]", key: "loop_halve",        scale: "binary"   },
    33: { group: "[Channel2]", key: "loop_double",       scale: "binary"   },
    34: { group: "[Channel2]", key: "hotcue_1_set",      scale: "binary"   },
    35: { group: "[Channel2]", key: "hotcue_1_goto",     scale: "binary"   },
    36: { group: "[Channel2]", key: "hotcue_1_clear",    scale: "binary"   },
    37: { group: "[Channel2]", key: "hotcue_2_set",      scale: "binary"   },
    38: { group: "[Channel2]", key: "hotcue_2_goto",     scale: "binary"   },
    39: { group: "[Channel2]", key: "hotcue_2_clear",    scale: "binary"   },
    // Channel 3
    40: { group: "[Channel3]", key: "play",              scale: "binary"   },
    41: { group: "[Channel3]", key: "cue_default",       scale: "binary"   },
    42: { group: "[Channel3]", key: "sync_enabled",      scale: "binary"   },
    43: { group: "[Channel3]", key: "volume",            scale: "unipolar" },
    44: { group: "[Channel3]", key: "pregain",           scale: "eq"       },
    45: { group: "[Channel3]", key: "rate",              scale: "bipolar"  },
    46: { group: "[Channel3]", key: "filterLow",         scale: "eq"       },
    47: { group: "[Channel3]", key: "filterMid",         scale: "eq"       },
    48: { group: "[Channel3]", key: "filterHigh",        scale: "eq"       },
    49: { group: "[Channel3]", key: "beatloop_activate", scale: "binary"   },
    50: { group: "[Channel3]", key: "loop_halve",        scale: "binary"   },
    51: { group: "[Channel3]", key: "loop_double",       scale: "binary"   },
    // Channel 4
    60: { group: "[Channel4]", key: "play",              scale: "binary"   },
    61: { group: "[Channel4]", key: "cue_default",       scale: "binary"   },
    62: { group: "[Channel4]", key: "sync_enabled",      scale: "binary"   },
    63: { group: "[Channel4]", key: "volume",            scale: "unipolar" },
    64: { group: "[Channel4]", key: "pregain",           scale: "eq"       },
    65: { group: "[Channel4]", key: "rate",              scale: "bipolar"  },
    66: { group: "[Channel4]", key: "filterLow",         scale: "eq"       },
    67: { group: "[Channel4]", key: "filterMid",         scale: "eq"       },
    68: { group: "[Channel4]", key: "filterHigh",        scale: "eq"       },
    69: { group: "[Channel4]", key: "beatloop_activate", scale: "binary"   },
    70: { group: "[Channel4]", key: "loop_halve",        scale: "binary"   },
    71: { group: "[Channel4]", key: "loop_double",       scale: "binary"   },
    // Master
    80: { group: "[Master]",   key: "crossfader",        scale: "bipolar"  },
    81: { group: "[Master]",   key: "volume",            scale: "unipolar" },
    82: { group: "[Master]",   key: "headVolume",        scale: "unipolar" },
    83: { group: "[Master]",   key: "headMix",           scale: "bipolar"  },
    84: { group: "[Master]",   key: "balance",           scale: "bipolar"  },
    // Effects
    100: { group: "[EffectRack1_EffectUnit1]", key: "mix",     scale: "unipolar" },
    101: { group: "[EffectRack1_EffectUnit2]", key: "mix",     scale: "unipolar" },
    102: { group: "[EffectRack1_EffectUnit3]", key: "mix",     scale: "unipolar" },
    103: { group: "[EffectRack1_EffectUnit4]", key: "mix",     scale: "unipolar" },
    104: { group: "[EffectRack1_EffectUnit1_Effect1]", key: "enabled", scale: "binary" },
    105: { group: "[EffectRack1_EffectUnit1_Effect2]", key: "enabled", scale: "binary" },
    106: { group: "[EffectRack1_EffectUnit1_Effect3]", key: "enabled", scale: "binary" },
    // Rate nudge (deck-relative — uses _activeDeck)
    110: { group: null, key: "rate_perm_up_small",   scale: "binary", deckRelative: true },
    111: { group: null, key: "rate_perm_down_small", scale: "binary", deckRelative: true },
    112: { group: null, key: "rate_perm_up",         scale: "binary", deckRelative: true },
    113: { group: null, key: "rate_perm_down",       scale: "binary", deckRelative: true },
    114: { group: null, key: "beatjump_size",        scale: "raw",    deckRelative: true },
    115: { group: null, key: "beatjump_forward",     scale: "binary", deckRelative: true },
    116: { group: null, key: "beatjump_backward",    scale: "binary", deckRelative: true },
    // Library/deck loading
    117: { group: "[Channel1]", key: "LoadSelectedTrack",        scale: "binary" },
    118: { group: "[Channel2]", key: "LoadSelectedTrack",        scale: "binary" },
    119: { group: "[Channel3]", key: "LoadSelectedTrack",        scale: "binary" },
    120: { group: "[Channel4]", key: "LoadSelectedTrack",        scale: "binary" },
    121: { group: "[Channel1]", key: "LoadSelectedTrackAndPlay", scale: "binary" },
    122: { group: "[Channel2]", key: "LoadSelectedTrackAndPlay", scale: "binary" },
    123: { group: "[Channel3]", key: "LoadSelectedTrackAndPlay", scale: "binary" },
    124: { group: "[Channel4]", key: "LoadSelectedTrackAndPlay", scale: "binary" },
};

// Hotcue slots 3–8 for channels 1–2
(function buildHotcueRoutes() {
    const actions = ["set", "goto", "clear"];
    for (let ch = 1; ch <= 2; ch++) {
        for (let slot = 3; slot <= 8; slot++) {
            const base = 50 + ((ch - 1) * 18) + ((slot - 3) * 3);
            actions.forEach((action, i) => {
                CC_ROUTE[base + i] = {
                    group: `[Channel${ch}]`,
                    key: `hotcue_${slot}_${action}`,
                    scale: "binary"
                };
            });
        }
    }
})();

// ── Controls to watch (state push to Python) ──────────────────────────────
const WATCH = {
    "[Channel1]": ["play","bpm","playposition","volume","pregain","rate",
                   "sync_enabled","loop_enabled","beatloop_size",
                   "filterLow","filterMid","filterHigh",
                   "track_artist","track_title","duration","track_samplerate",
                   "hotcue_1_position","hotcue_2_position","hotcue_3_position",
                   "hotcue_4_position"],
    "[Channel2]": ["play","bpm","playposition","volume","pregain","rate",
                   "sync_enabled","loop_enabled","beatloop_size",
                   "filterLow","filterMid","filterHigh",
                   "track_artist","track_title","duration","track_samplerate"],
    "[Channel3]": ["play","bpm","playposition","volume","rate","sync_enabled"],
    "[Channel4]": ["play","bpm","playposition","volume","rate","sync_enabled"],
    "[Master]":   ["crossfader","volume","headVolume","headMix","balance"],
    "[EffectRack1_EffectUnit1]": ["mix","enabled"],
    "[EffectRack1_EffectUnit2]": ["mix","enabled"],
};

// ── Scale decode (MIDI 0–127 → Mixxx float) ───────────────────────────────
function decode(midiVal, scale) {
    switch (scale) {
        case "binary":   return midiVal >= 64 ? 1.0 : 0.0;
        case "unipolar": return midiVal / 127.0;
        case "bipolar":  return (midiVal / 127.0) * 2.0 - 1.0;
        case "eq":       return (midiVal / 127.0) * 4.0;
        case "beatloop": {
            const sizes = [0.03125,0.0625,0.125,0.25,0.5,1,2,4,8,16,32,64];
            return sizes[Math.round((midiVal / 127.0) * (sizes.length - 1))] || 4;
        }
        case "raw": return midiVal;
        default:    return midiVal / 127.0;
    }
}

// ── XHR state push (fire-and-forget, debounced) ───────────────────────────
const _lastPush = {};

function pushState(group, key, value) {
    const ck = `${group}/${key}`;
    const now = Date.now();
    if (_lastPush[ck] && (now - _lastPush[ck]) < MCP_DEBOUNCE_MS) return;
    _lastPush[ck] = now;

    try {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", MCP_STATE_URL, true); // async
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.send(JSON.stringify({ group, key, value }));
        // no response handling — fire and forget
    } catch (e) {
        // Python server not running — fail silently, MIDI still works
    }
}

// ── Trigger keys (use triggerControl, not setValue) ───────────────────────
const TRIGGER_KEYS = new Set([
    "cue_default","beatloop_activate","reloop_toggle",
    "loop_halve","loop_double","beatjump_forward","beatjump_backward",
    "rate_perm_up_small","rate_perm_down_small","rate_perm_up","rate_perm_down",
    "LoadSelectedTrack","LoadSelectedTrackAndPlay",
]);

// ── Main controller object ────────────────────────────────────────────────
const MixxxMCP = {
    _activeDeck: 1,
    _connections: [],

    getActiveGroup() {
        return `[Channel${this._activeDeck}]`;
    },

    // ── Mixxx lifecycle ──────────────────────────────────────────────────
    init(id, debug) {
        console.log("[mixxx-mcp] init — wiring state connections");

        // Wire live state push for all watched controls
        for (const [grp, keys] of Object.entries(WATCH)) {
            for (const key of keys) {
                try {
                    const conn = engine.makeConnection(grp, key, function(val, g, k) {
                        pushState(g, k, val);
                    });
                    this._connections.push(conn);
                } catch(e) {
                    // Control may not exist in this Mixxx version — skip silently
                }
            }
        }

        // Push initial state snapshot so Python has values immediately
        setTimeout(() => {
            for (const [grp, keys] of Object.entries(WATCH)) {
                for (const key of keys) {
                    try {
                        const val = engine.getValue(grp, key);
                        if (val !== undefined && val !== null) {
                            pushState(grp, key, val);
                        }
                    } catch(e) {}
                }
            }
            console.log("[mixxx-mcp] initial state snapshot pushed");
        }, 1000);

        console.log(`[mixxx-mcp] ready — ${this._connections.length} connections active`);
    },

    shutdown(id) {
        this._connections.forEach(c => { try { c.disconnect(); } catch(e) {} });
        this._connections = [];
        console.log("[mixxx-mcp] shutdown");
    },

    // ── MIDI CC handler ──────────────────────────────────────────────────
    handleCC(channel, control, value, status, group) {
        const route = CC_ROUTE[control];
        if (!route) {
            console.log(`[mixxx-mcp] Unknown CC ${control} — ignored`);
            return;
        }

        const grp = route.deckRelative ? this.getActiveGroup() : route.group;
        const val  = decode(value, route.scale);

        // Hotcue triggers
        if (route.key && /^hotcue_\d+_(set|goto|clear)$/.test(route.key)) {
            if (val === 1.0) script.triggerControl(grp, route.key, 100);
            return;
        }

        // Pulse triggers
        if (TRIGGER_KEYS.has(route.key)) {
            if (val === 1.0) script.triggerControl(grp, route.key, 100);
            return;
        }

        engine.setValue(grp, route.key, val);
        console.log(`[mixxx-mcp] SET ${grp}.${route.key} = ${val}`);
    },
};
