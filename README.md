# mixxx-mcp

MCP (Model Context Protocol) server for [Mixxx](https://mixxx.org) DJ Software.
Lets AI agents (Codex, Claude, Claude Code, etc.) control Mixxx in real time — transport, mixing, EQ, loops, hotcues, effects.

---

## Architecture

```
AI Agent (Codex / Claude)
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

Create a local virtual environment first. This avoids Homebrew Python's
`externally-managed-environment` error on macOS and keeps dependencies scoped
to this repo.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .

# Optional, for running tests/development tooling:
.venv/bin/python -m pip install -e ".[dev]"
```

### 2. Install Mixxx controller script

Copy both files to your Mixxx controllers directory:

```bash
# macOS
cp mixxx-mcp.js mixxx-mcp.midi.xml \
  ~/Library/Containers/Mixxx/Data/Library/Application\ Support/Mixxx/controllers/

# macOS alternate container name used by some installs
cp mixxx-mcp.js mixxx-mcp.midi.xml \
  ~/Library/Containers/org.mixxx.mixxx/Data/Library/Application\ Support/Mixxx/controllers/

# Linux
cp mixxx-mcp.js mixxx-mcp.midi.xml ~/.mixxx/controllers/

# Windows
cp mixxx-mcp.js mixxx-mcp.midi.xml %LOCALAPPDATA%\Mixxx\controllers\
```

If you already have a custom controller mapping such as:

```text
~/Library/Containers/Mixxx/Data/Library/Application Support/Mixxx/controllers/Hercules DJControl Inpulse 200 custom3.midi.xml
```

then `~/Library/Containers/Mixxx/Data/Library/Application Support/Mixxx/controllers/` is the folder to copy `mixxx-mcp.js` and `mixxx-mcp.midi.xml` into. You do not need to overwrite your Hercules mapping.

### 3. Run the MCP server

Start the server before opening Mixxx's controller preferences. On macOS/Linux,
`python-rtmidi` creates the `mixxx-mcp` virtual MIDI port when the server starts,
and Mixxx only shows MIDI devices that currently exist.

```bash
# stdio mode (Codex / Claude Desktop / claude-code)
.venv/bin/python main.py

# HTTP mode (remote / multi-client)
.venv/bin/python main.py --http --port 8080
```

If `.venv/bin/python main.py` fails with missing packages, install the server dependencies
with the same Python interpreter:

```bash
.venv/bin/python -m pip install -e .
```

> **Note (Windows):** Virtual MIDI ports require [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html). Create a port named `mixxx-mcp` before starting the server.

### 4. Enable in Mixxx

1. Keep the Python server running.
2. Open **Mixxx → Preferences → Controllers**.
3. Select **mixxx-mcp** from the device list.
4. Check **Enable**.
5. Click **OK**.

If `mixxx-mcp` does not appear, restart Mixxx or reopen **Preferences → Controllers** while `.venv/bin/python main.py` is still running.

### 5. Configure Codex

Codex supports MCP servers in the CLI and IDE extension. Add this server to Codex with the CLI:

```bash
codex mcp add mixxx -- /path/to/mixxx-mcp/.venv/bin/python /path/to/mixxx-mcp/main.py
```

Or edit `~/.codex/config.toml` directly:

```toml
[mcp_servers.mixxx]
command = "/path/to/mixxx-mcp/.venv/bin/python"
args = ["/path/to/mixxx-mcp/main.py"]
```

For a repo-scoped setup, put the same block in `.codex/config.toml` inside a trusted project. In Codex, use `/mcp` to confirm the `mixxx` server is active.

### 6. Configure Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mixxx": {
      "command": "/path/to/mixxx-mcp/.venv/bin/python",
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
| `set_pitch_up(deck, percent)` | Tempo as pitch-up percent |
| `set_target_bpm(deck, bpm)` | Set tempo from current deck BPM to target BPM |
| `nudge_tempo(deck, direction, size)` | Tempo nudge up/down |
| `set_loop(deck, beats)` | Activate beat loop |
| `exit_loop(deck)` | Deactivate loop |
| `halve_loop(deck)` / `double_loop(deck)` | Resize loop |
| `set_hotcue(deck, slot)` | Set hotcue 1–8 |
| `goto_hotcue(deck, slot)` | Jump to hotcue |
| `clear_hotcue(deck, slot)` | Delete hotcue |
| `beatjump(deck, beats)` | Jump ±N beats |
| `load_selected_track(deck, play_now, target_bpm, pitch_up_percent, rate)` | Load highlighted Mixxx library track |
| `enqueue_songs(songs)` | Add conversational song requests to the queue |
| `request_song(song, artist, target_bpm, pitch_up_percent, rate)` | Add one song request |
| `prepare_next_selected(deck)` | Prepare highlighted library track for next queued request |
| `get_song_queue()` / `clear_song_queue()` | Inspect or clear the request queue |
| `set_queue_monitor(enabled)` | Toggle automatic deck handoff |
| `get_deck_state(deck)` | Read live deck state |
| `get_mixer_state()` | Read master mixer state |
| `get_all_state()` | Full OSC state dump |
| `send_control(group, key, value)` | Raw control escape hatch |
| `toggle_effect(unit, effect, enabled)` | Effect on/off |
| `set_effect_mix(unit, value)` | Effect wet/dry |

### Song Request Queue

The queue tools automate a two-deck handoff on decks 1 and 2:

1. Add requests with `enqueue_songs([...])` or `request_song(...)`.
2. Highlight the matching track in Mixxx's library.
3. Call `prepare_next_selected()` to load that highlighted track into an idle queue deck.
4. The queue monitor starts the prepared opposite deck after the active deck reaches the end.

Tempo can be specified per request:

```json
{
  "song": "Example Track",
  "artist": "Example Artist",
  "target_bpm": 128
}
```

Use `pitch_up_percent` instead of `target_bpm` when you want a fixed pitch/tempo change such as `4` for +4%.

Mixxx's controller API exposes `LoadSelectedTrack`, not a string/file-path track load command. For that reason, song names in the MCP queue are request metadata for the agent conversation; actual audio loading uses the track currently highlighted in Mixxx.

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
