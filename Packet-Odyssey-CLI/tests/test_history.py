from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from packet_odyssey.engine import SimulationEngine
from packet_odyssey.history import HistoryStore
from packet_odyssey.models import SimulationConfig


class HistoryTests(unittest.TestCase):
    def test_save_list_get_and_clear(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / "history.db")
            run = SimulationEngine().run(SimulationConfig(url="https://example.com"))
            store.save(run)
            self.assertEqual(len(store.list()), 1)
            loaded = store.get(run.id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["status"], "completed")
            self.assertEqual(store.clear(), 1)
            self.assertEqual(store.list(), [])


if __name__ == "__main__":
    unittest.main()
