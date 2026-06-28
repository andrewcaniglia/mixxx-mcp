"""
queue_manager.py - lightweight two-deck request queue for Mixxx.

Mixxx controller scripts can load the currently highlighted library track into
a deck, but they do not expose a string/file-path load API. This queue keeps
the agent-facing song requests and automates deck handoff once tracks are
prepared from Mixxx's selected library row.
"""

import time
import threading
import uuid
from typing import Any, Dict, List, Optional

from .controls import resolve_channel
from .midi_bridge import MidiBridge
from .osc_listener import OscStateStore


QueueItem = Dict[str, Any]


class DeckQueue:
    def __init__(self, midi: MidiBridge, state: OscStateStore, decks: tuple[int, int] = (1, 2)):
        self.midi = midi
        self.state = state
        self.decks = decks
        self._items: List[QueueItem] = []
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def enqueue(self, songs: list[Any]) -> list[QueueItem]:
        items: list[QueueItem] = []
        with self._lock:
            for song in songs:
                item = self._normalize_song(song)
                self._items.append(item)
                items.append(dict(item))
        return items

    def clear(self) -> int:
        with self._lock:
            count = len(self._items)
            self._items.clear()
            return count

    def snapshot(self) -> list[QueueItem]:
        with self._lock:
            return [dict(item) for item in self._items]

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True, name="deck-queue")
            self._thread.start()

    def stop(self):
        with self._lock:
            self._running = False

    def prepare_next_selected(self, deck: Optional[int] = None) -> dict:
        with self._lock:
            item = self._next_item("queued")
            if item is None:
                return {"ok": False, "error": "queue is empty"}

            target_deck = deck or self._idle_deck_locked()
            if target_deck is None:
                return {"ok": False, "error": "no idle queue deck is available", "queue": self.snapshot()}

            if target_deck not in self.decks:
                return {"ok": False, "error": f"deck must be one of {self.decks}"}

            self._load_selected_locked(target_deck, item)
            return {"ok": True, "prepared": dict(item), "deck": target_deck}

    def apply_tempo(self, deck: int, item: QueueItem) -> dict:
        rate = item.get("rate")
        if rate is None and item.get("target_bpm") is not None:
            current_bpm = self.state.get(resolve_channel(deck), "bpm")
            try:
                current = float(current_bpm)
                if current > 0:
                    rate = (float(item["target_bpm"]) / current) - 1.0
            except (TypeError, ValueError):
                return {"ok": False, "error": "deck BPM is not available yet"}
        if rate is None and item.get("pitch_up_percent") is not None:
            rate = float(item["pitch_up_percent"]) / 100.0

        if rate is None:
            return {"ok": True, "deck": deck, "rate": None}
        if not -1.0 <= float(rate) <= 1.0:
            return {"ok": False, "error": "computed rate must be -1.0 to 1.0", "rate": rate}

        self.midi.send_control(resolve_channel(deck), "rate", float(rate))
        return {"ok": True, "deck": deck, "rate": float(rate)}

    def mark_done(self, item_id: str):
        with self._lock:
            for item in self._items:
                if item["id"] == item_id:
                    item["status"] = "done"
                    return

    def _run(self):
        while True:
            with self._lock:
                if not self._running:
                    return
                self._handoff_locked()
            time.sleep(0.5)

    def _handoff_locked(self):
        playing_decks = [deck for deck in self.decks if self._is_playing(deck)]
        if not playing_decks:
            self._mark_playing_finished_locked()
            prepared = self._next_item("prepared")
            if prepared is not None and prepared.get("deck") is not None:
                self._start_item_locked(prepared)
            return

        active_deck = playing_decks[0]
        if not self._is_finished(active_deck):
            return

        next_item = self._prepared_for_other_deck_locked(active_deck)
        if next_item is None:
            return

        self.midi.send_control(resolve_channel(active_deck), "play", 0.0)
        self._mark_playing_finished_locked(deck=active_deck)
        self._start_item_locked(next_item)

    def _start_item_locked(self, item: QueueItem):
        deck = item.get("deck")
        if deck is None:
            return
        self._mark_playing_finished_locked(deck=int(deck))
        self.apply_tempo(int(deck), item)
        self.midi.send_control(resolve_channel(int(deck)), "play", 1.0)
        item["status"] = "playing"
        item["started_at"] = time.time()

    def _load_selected_locked(self, deck: int, item: QueueItem):
        group = resolve_channel(deck)
        self.midi.send_control(group, "LoadSelectedTrack", 1.0)
        item["deck"] = deck
        item["status"] = "prepared"
        item["prepared_at"] = time.time()
        threading.Timer(1.0, lambda: self.apply_tempo(deck, item)).start()

    def _next_item(self, status: str) -> Optional[QueueItem]:
        for item in self._items:
            if item.get("status") == status:
                return item
        return None

    def _prepared_for_other_deck_locked(self, deck: int) -> Optional[QueueItem]:
        for item in self._items:
            if item.get("status") == "prepared" and item.get("deck") != deck:
                return item
        return None

    def _mark_playing_finished_locked(self, deck: Optional[int] = None):
        for item in self._items:
            if item.get("status") == "playing" and (deck is None or item.get("deck") == deck):
                item["status"] = "done"
                item["finished_at"] = time.time()

    def _idle_deck_locked(self) -> Optional[int]:
        for deck in self.decks:
            if self._is_playing(deck):
                continue
            has_prepared = any(
                item.get("status") == "prepared" and item.get("deck") == deck
                for item in self._items
            )
            if not has_prepared:
                return deck
        return None

    def _is_playing(self, deck: int) -> bool:
        return bool(self.state.get(resolve_channel(deck), "play") or 0)

    def _is_finished(self, deck: int) -> bool:
        group = resolve_channel(deck)
        playing = bool(self.state.get(group, "play") or 0)
        position = self.state.get(group, "playposition")
        try:
            pos = float(position)
        except (TypeError, ValueError):
            pos = 0.0
        return (not playing and pos >= 0.98) or pos >= 0.995

    def _normalize_song(self, song: Any) -> QueueItem:
        if isinstance(song, str):
            data: QueueItem = {"song": song}
        elif isinstance(song, dict):
            data = dict(song)
        else:
            raise ValueError("each song must be a string or object")

        item: QueueItem = {
            "id": data.get("id") or uuid.uuid4().hex,
            "song": data.get("song") or data.get("title") or data.get("query") or "selected track",
            "artist": data.get("artist"),
            "target_bpm": data.get("target_bpm") if data.get("target_bpm") is not None else data.get("bpm"),
            "pitch_up_percent": data.get("pitch_up_percent"),
            "rate": data.get("rate"),
            "status": "queued",
            "deck": data.get("deck"),
        }
        return item
