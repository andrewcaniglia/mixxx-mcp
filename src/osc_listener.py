"""
osc_listener.py — OSC server that receives live state from Mixxx

Mixxx acts as an OSC CLIENT — it broadcasts control changes to:
  /mixxx/<group>/<key>  → float value

We run a lightweight UDP server that caches everything into OscStateStore.
The MCP tools query this store to answer state questions instantly (no round-trip).

Setup in Mixxx:
  Preferences → Live Broadcasting → (not available natively yet)
  Use the companion mixxx-mcp.js controller script which calls:
    engine.makeConnection(group, key, (val) => osc.send(...))
  OR configure the OSC client plugin if available in your Mixxx build.

Default bind: 0.0.0.0:57121
"""

import logging
import threading
import time
import copy
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger("mixxx-mcp.osc")

try:
    from pythonosc import dispatcher as osc_dispatcher
    from pythonosc import osc_server
    HAS_OSC = True
except ImportError:
    HAS_OSC = False
    log.warning("python-osc not installed. Install: pip install python-osc")


class OscStateStore:
    """
    Thread-safe KV cache for Mixxx control state received via OSC.
    
    Key scheme: (group, key) → float
    Example: ("[Channel1]", "play") → 1.0
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 57121):
        self.host = host
        self.port = port
        self._state: Dict[Tuple[str, str], Any] = {}
        self._lock = threading.RLock()
        self._server_thread: Optional[threading.Thread] = None

    # ── Public API ─────────────────────────────────────────────────────────

    def get(self, group: str, key: str) -> Optional[Any]:
        with self._lock:
            return self._state.get((group, key))

    def set(self, group: str, key: str, value: Any):
        with self._lock:
            self._state[(group, key)] = value

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        """Return all state grouped by control group."""
        with self._lock:
            result: Dict[str, Dict[str, Any]] = {}
            for (grp, key), val in self._state.items():
                result.setdefault(grp, {})[key] = val
            return copy.deepcopy(result)

    # ── OSC server ─────────────────────────────────────────────────────────

    def start(self):
        if not HAS_OSC:
            log.warning("OSC server not started — python-osc unavailable")
            return
        self._server_thread = threading.Thread(
            target=self._run_server, daemon=True, name="osc-listener"
        )
        self._server_thread.start()
        log.info("OSC state listener started on %s:%d", self.host, self.port)

    def _run_server(self):
        try:
            d = osc_dispatcher.Dispatcher()
            # /mixxx/[Channel1]/play  → (group, key, value)
            d.set_default_handler(self._handle_message)
            server = osc_server.ThreadingOSCUDPServer((self.host, self.port), d)
            server.serve_forever()
        except Exception as e:
            log.error("OSC server error: %s", e)

    def _handle_message(self, address: str, *args):
        """
        Parse OSC address: /mixxx/[Group]/key
        Example: /mixxx/[Channel1]/play  0  1.0
        """
        try:
            parts = address.strip("/").split("/")
            if len(parts) < 3 or parts[0] != "mixxx":
                return
            # parts[1] is the group (e.g. "[Channel1]")
            # parts[2] is the key
            group = parts[1]
            key = "/".join(parts[2:])  # keys can theoretically have sub-paths
            value = args[0] if args else None
            if value is not None:
                self.set(group, key, value)
                log.debug("OSC ← %s = %s", address, value)
        except Exception as e:
            log.warning("OSC parse error %s: %s", address, e)
