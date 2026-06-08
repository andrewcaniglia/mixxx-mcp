# mixxx-mcp

MCP (Model Context Protocol) server for [Mixxx](https://mixxx.org) DJ Software.
Lets AI agents (Claude, Claude Code, etc.) control Mixxx in real time — transport, mixing, EQ, loops, hotcues, effects.

---

## Architecture

```
AI Agent (Claude)
      │
      ▼ MCP tools
mixxx-mcp Python Server
      │                     ┌─────────────────────┐
      ├─ MIDI CC out ───────▶│ Virtual MIDI port   │
      │                     │ "mixxx-mcp"          │
      │                     └────────┬────────────┘
      │                              ▼ CC → engine.setValue()
      │                     ┌────────────────────┐
      │                     │ Mixxx + mixxx-mcp  │
      │                     │ .js controller      │
      │                     │ script              │
      ◀── OSC UDP ──────────┤ broadcasts state    │
   OscStateStore            └────────────────────┘
```

**Write path:** `mcp.tool → MidiBridge → rtmidi CC → Mixxx JS script → engine.setValue()`  
**Read path:** `Mixxx JS → OSC UDP → OscStateStore → mcp.tool → AI`

---

## Setup

### 1. Install Python server

```bash
pip install -e ".[dev]"
# or without dev deps:
pip install mcp python-osc python-rtmidi
```

### 2. Install Mixxx controller script

Copy both files to your Mixxx controllers directory:

```bash
# macOS
cp mixxx-mcp.js mixxx-mcp.midi.xml \
  ~/Library/Containers/org.mixxx.mixxx/Data/Library/Application\ Support/Mixxx/controllers/

# Linux
cp mixxx-mcp.js mixxx-mcp.midi.xml ~/.mixxx/controllers/

# Windows
cp mixxx-mcp.js mixxx-mcp.midi.xml %LOCALAPPDATA%\Mixxx\controllers\
```

### 3. Enable in Mixxx

1. Open **Mixxx → Preferences → Controllers**
2. Select **mixxx-mcp** from the device list
3. Check **Enable**
4. Click **OK**

> **Note (Windows):** Virtual MIDI ports require [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html). Create a port named `mixxx-mcp` before starting the server.

### 4. Run the MCP server

```bash
# stdio mode (Claude Desktop / claude-code)
python main.py

# HTTP mode (remote / multi-client)
python main.py --http --port 8080
```

### 5. Configure Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mixxx": {
      "command": "python",
      "args": ["/path/to/mixxx-mcp/main.py"],
      "env": {}
    }
  }
}
```

---

## Available Tools

| Tool | Description |
|------|-------------|
| `play(deck)` | Start playback |
| `stop(deck)` | Stop playback |
| `cue(deck)` | Trigger CUE |
| `sync(deck)` | Toggle BPM sync |
| `set_volume(deck, value)` | Channel fader 0.0–1.0 |
| `set_crossfader(value)` | Crossfader -1.0–1.0 |
| `set_eq(deck, low, mid, high)` | EQ bands 0.0–4.0 |
| `set_pregain(deck, value)` | Trim 0.0–4.0 |
| `set_rate(deck, value)` | Tempo pitch -1.0–1.0 |
| `nudge_tempo(deck, direction, size)` | Tempo nudge up/down |
| `set_loop(deck, beats)` | Activate beat loop |
| `exit_loop(deck)` | Deactivate loop |
| `halve_loop(deck)` / `double_loop(deck)` | Resize loop |
| `set_hotcue(deck, slot)` | Set hotcue 1–8 |
| `goto_hotcue(deck, slot)` | Jump to hotcue |
| `clear_hotcue(deck, slot)` | Delete hotcue |
| `beatjump(deck, beats)` | Jump ±N beats |
| `get_deck_state(deck)` | Read live deck state |
| `get_mixer_state()` | Read master mixer state |
| `get_all_state()` | Full OSC state dump |
| `send_control(group, key, value)` | Raw control escape hatch |
| `toggle_effect(unit, effect, enabled)` | Effect on/off |
| `set_effect_mix(unit, value)` | Effect wet/dry |

---

## OSC State

Mixxx broadcasts control changes via the JS script's `engine.makeConnection()` callbacks.
The Python server listens on **UDP 57121** at path `/mixxx/<group>/<key>`.

To fully enable OSC push (vs poll), the JS callbacks in `mixxx-mcp.js` need to forward
values via a UDP socket. This requires a Mixxx build with liblo, or you can extend
the JS script to use XMLHttpRequest to POST state to a local HTTP endpoint.

---

## Mixxx Controls Reference

Full control list: https://manual.mixxx.org/latest/en/chapters/appendix/mixxx_controls.html

Key groups:
- `[Channel1]` – `[Channel4]` — Decks
- `[Master]` — Mixer master
- `[Sampler1]` – `[Sampler64]` — Samplers
- `[EffectRack1_EffectUnit1]` – `[_EffectUnit4]` — Effect units
- `[EffectRack1_EffectUnit1_Effect1]` – `[_Effect3]` — Individual effects
- `[Playlist]` — Library navigation

---

## License

MIT
