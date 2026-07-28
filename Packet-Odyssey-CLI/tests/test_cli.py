from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest

from packet_odyssey.cli import main


class CliTests(unittest.TestCase):
    def test_json_success_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            previous = os.environ.get("PACKET_ODYSSEY_HISTORY")
            os.environ["PACKET_ODYSSEY_HISTORY"] = os.path.join(directory, "history.db")
            output = io.StringIO()
            try:
                with contextlib.redirect_stdout(output):
                    code = main(["--no-color", "run", "https://example.com", "--json", "--no-history"])
            finally:
                if previous is None:
                    os.environ.pop("PACKET_ODYSSEY_HISTORY", None)
                else:
                    os.environ["PACKET_ODYSSEY_HISTORY"] = previous
            payload = json.loads(output.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(payload["status"], "completed")

    def test_blocking_failure_returns_exit_code_two(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([
                "--no-color", "run", "https://example.com", "--failure", "dns_timeout",
                "--json", "--no-history",
            ])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
