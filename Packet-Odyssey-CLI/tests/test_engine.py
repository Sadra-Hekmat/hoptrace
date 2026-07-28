from __future__ import annotations

import unittest

from packet_odyssey.engine import SimulationConfigurationError, SimulationEngine
from packet_odyssey.models import FailureType, SimulationConfig, SimulationStage, SimulationStatus, StageStatus


class EngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = SimulationEngine()

    def test_successful_request_completes_all_stages(self) -> None:
        run = self.engine.run(SimulationConfig(url="https://example.com/path"))
        self.assertEqual(run.status, SimulationStatus.COMPLETED)
        self.assertEqual(len(run.stages), 8)
        self.assertEqual(len(run.events), 16)
        self.assertTrue(all(stage.status is StageStatus.SUCCESS for stage in run.stages))
        self.assertEqual(run.terminal_stage, SimulationStage.DATABASE)

    def test_expired_certificate_blocks_downstream_stages(self) -> None:
        run = self.engine.run(
            SimulationConfig(
                url="https://legacy.example/login",
                failure_type=FailureType.EXPIRED_CERTIFICATE,
            )
        )
        self.assertEqual(run.status, SimulationStatus.FAILED)
        self.assertEqual(run.terminal_stage, SimulationStage.TLS)
        self.assertEqual(run.stages[3].status, StageStatus.FAILED)
        self.assertTrue(all(stage.status is StageStatus.SKIPPED for stage in run.stages[4:]))

    def test_packet_loss_is_recoverable(self) -> None:
        run = self.engine.run(
            SimulationConfig(url="https://media.example/video", failure_type=FailureType.PACKET_LOSS)
        )
        self.assertEqual(run.status, SimulationStatus.COMPLETED)
        self.assertEqual(run.stages[2].status, StageStatus.WARNING)

    def test_probability_is_deterministic(self) -> None:
        config = SimulationConfig(
            url="https://example.com",
            failure_type=FailureType.DNS_TIMEOUT,
            probability=0.5,
            seed="same",
        )
        left = self.engine.run(config)
        right = self.engine.run(config)
        self.assertEqual(left.failure_triggered, right.failure_triggered)

    def test_invalid_url_is_rejected(self) -> None:
        with self.assertRaises(SimulationConfigurationError):
            self.engine.run(SimulationConfig(url="ftp://example.com"))


if __name__ == "__main__":
    unittest.main()
