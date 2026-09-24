import json
import tempfile
import unittest
from pathlib import Path

from xiao_pantilt.core import ScanConfig, ScanController, ScanState
from xiao_pantilt.planner import plan_scan
from xiao_pantilt.registration import ZNCCRegistrar
from xiao_pantilt.scheduler import PhaseLockedScheduler
from xiao_pantilt.runtime import ScanService
from xiao_pantilt.sim import (DirectoryPhotoSink, SimCamera, SimClock, SimPanDrive,
                              TexturedWorld, run_simulation)
from xiao_pantilt.interfaces import Frame


class PlannerTests(unittest.TestCase):
    def test_overlap_endpoints_and_scene_coverage(self):
        plan = plan_scan()
        self.assertEqual(plan.anchors_deg, (0, 80, 160, 180))
        self.assertEqual(plan.scene_coverage_deg, 290)
        self.assertGreaterEqual(110 - (plan.anchors_deg[1] - plan.anchors_deg[0]), 30)
        self.assertGreaterEqual(110 - (plan.anchors_deg[-1] - plan.anchors_deg[-2]), 30)


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.world, self.clock = TexturedWorld(seed=13), SimClock()
        self.drive = SimPanDrive(self.clock, speed_bias=1.0, slip=0, backlash_deg=0)
        self.assertTrue(self.drive.home_to_stop(-1, 12))
        self.camera = SimCamera(self.world, self.drive, self.clock)
        self.registrar = ZNCCRegistrar(110)

    def test_known_yaw_both_directions_and_lighting(self):
        reference = self.camera.capture()
        for yaw in (37.0, -26.0):
            self.drive.yaw_deg = yaw
            result = self.registrar.register(reference, self.camera.capture(),
                                              min_delta_deg=yaw - 3, max_delta_deg=yaw + 3)
            self.assertGreater(result.confidence, .45)
            self.assertAlmostEqual(result.yaw_delta_deg, yaw, delta=2.0)

    def test_blank_frame_is_rejected(self):
        reference = self.camera.capture()
        blank = reference.__class__(reference.width, reference.height,
                                    bytes(reference.width * reference.height))
        self.assertLess(self.registrar.register(reference, blank).confidence, .40)

    def test_periodic_texture_is_ambiguous(self):
        w, h = 160, 72
        pixels = bytes((35 if (x % 16) < 8 else 220) for _ in range(h) for x in range(w))
        periodic = Frame(w, h, pixels)
        self.assertLess(self.registrar.register(periodic, periodic, min_delta_deg=-40,
                                                max_delta_deg=40).confidence, .40)


class ScanTests(unittest.TestCase):
    def _controller(self, fail_after=None):
        clock = SimClock(); drive = SimPanDrive(clock)
        camera = SimCamera(TexturedWorld(seed=7), drive, clock); camera.fail_after = fail_after
        sink = DirectoryPhotoSink(tempfile.mkdtemp(), actual_yaw_provider=lambda: drive.yaw_deg)
        return ScanController(camera, drive, sink, clock, ScanConfig()), drive, sink

    def test_transient_registration_failure_mechanically_homes_and_verifies_saved_home(self):
        clock = SimClock(); drive = SimPanDrive(clock)
        camera = SimCamera(TexturedWorld(seed=7), drive, clock)
        camera.fail_indices = {2, 3}  # motion frame plus its fresh-capture retry
        controller = ScanController(camera, drive, DirectoryPhotoSink(tempfile.mkdtemp()), clock, ScanConfig())
        report = controller.run_cycle()
        self.assertEqual(report.state, ScanState.ABORTED)
        self.assertTrue(report.home_verified)
        self.assertIn("low registration confidence", report.failure)
        self.assertTrue(any(e["event"] == "failure_home_command" for e in report.events))
        self.assertTrue(any(e["event"] == "failure_home_dock" for e in report.events))

    def test_second_cycle_reuses_verified_visual_home_without_hard_homing(self):
        clock = SimClock(); drive = SimPanDrive(clock); camera = SimCamera(TexturedWorld(seed=7), drive, clock)
        controller = ScanController(camera, drive, DirectoryPhotoSink(tempfile.mkdtemp()), clock, ScanConfig())
        first = controller.run_cycle()
        second = controller.run_cycle()
        self.assertEqual(first.state, ScanState.COMPLETE)
        self.assertEqual(second.state, ScanState.COMPLETE)
        self.assertEqual(len([e for e in first.events if e["event"] == "homed"]), 1)
        self.assertFalse(any(e["event"] == "homed" for e in second.events))
        self.assertTrue(any(e["event"] == "warm_home_check" for e in second.events))

    def test_camera_exception_after_motion_aborts_with_bounded_recovery(self):
        class ExplodingCamera(SimCamera):
            def capture_tracking(self):
                if self.capture_count >= 1:
                    raise RuntimeError("camera unplugged")
                return super().capture_tracking()
        clock = SimClock(); drive = SimPanDrive(clock)
        camera = ExplodingCamera(TexturedWorld(), drive, clock)
        controller = ScanController(camera, drive, DirectoryPhotoSink(tempfile.mkdtemp()), clock, ScanConfig())
        report = controller.run_cycle()
        self.assertEqual(report.state, ScanState.ABORTED)
        self.assertIn("adapter exception", report.failure)
        self.assertTrue(any(e["event"] == "failure_home_command" for e in report.events))
        self.assertTrue(any(e["event"] == "recovery_adapter_exception" for e in report.events))

    def test_sink_exception_aborts_and_attempts_bounded_home(self):
        class ExplodingSink:
            def save(self, photo, metadata):
                raise OSError("storage full")
        clock = SimClock(); drive = SimPanDrive(clock)
        controller = ScanController(SimCamera(TexturedWorld(), drive, clock), drive, ExplodingSink(), clock, ScanConfig())
        report = controller.run_cycle()
        self.assertEqual(report.state, ScanState.ABORTED)
        self.assertIn("adapter exception", report.failure)
        self.assertTrue(any(e["event"] == "failure_home_command" for e in report.events))

    def test_scan_reaches_end_and_returns_home_with_bias_slip_backlash(self):
        controller, drive, sink = self._controller()
        report = controller.run_cycle()
        self.assertEqual(report.state, ScanState.COMPLETE)
        self.assertTrue(report.home_verified)
        self.assertEqual([p["logical_yaw_deg"] for p in report.photos], [0, 80, 160, 180])
        self.assertLess(abs(drive.yaw_deg), 2.0)
        self.assertTrue(any(e.get("direction") == -1 for e in report.events if e["event"] == "pulse"))
        self.assertEqual(report.events[0]["event"], "homed")
        self.assertEqual(report.events[-1]["event"], "home_dock")
        self.assertEqual(len([e for e in report.events if e["event"] == "return_dock"]), 3)
        actual = [m["simulator_actual_yaw_deg"] for m in sink.saved]
        self.assertGreaterEqual(max(actual) - min(actual) + controller.config.horizontal_fov_deg, 286)
        self.assertTrue(all(controller.config.horizontal_fov_deg - abs(b - a) >= 25
                            for a, b in zip(actual, actual[1:])))
        events = report.events
        for i, event in enumerate(events):
            if event["event"] == "pulse" and event["reason"].endswith("-step"):
                self.assertEqual(events[i + 1]["event"], "registration")

    def test_registration_failure_aborts_and_only_uses_bounded_reverse_recovery(self):
        controller, _, _ = self._controller(fail_after=2)
        report = controller.run_cycle()
        self.assertEqual(report.state, ScanState.ABORTED)
        self.assertEqual(report.failure, "low registration confidence")
        failure_at = next(i for i, e in enumerate(report.events)
                          if e["event"] == "registration" and e["confidence"] < .45)
        later = [e for e in report.events[failure_at + 1:] if e["event"] == "pulse"]
        self.assertTrue(later)
        self.assertTrue(all(e["direction"] == -1 for e in later))
        self.assertLessEqual(len(later), controller.config.recovery_max_pulses)
        self.assertTrue(all(e["seconds"] <= controller.config.max_pulse_seconds for e in report.events if e["event"] == "pulse"))

    def test_impossible_timed_approach_is_rejected_before_motion(self):
        controller, _, _ = self._controller()
        controller.config = ScanConfig(nominal_speed_deg_s=1, max_move_seconds=2)
        report = controller.run_cycle()
        self.assertEqual(report.state, ScanState.ABORTED)
        self.assertEqual(report.failure, "motion time bound exceeded")
        self.assertFalse(any(e["event"] == "pulse" and e["direction"] == 1 for e in report.events))


class SchedulerAndSimulationTests(unittest.TestCase):
    def test_sim_homing_fails_when_time_bound_cannot_reach_stop(self):
        clock = SimClock(); drive = SimPanDrive(clock); drive.yaw_deg = 180
        self.assertFalse(drive.home_to_stop(-1, 1.0))
        self.assertGreater(drive.yaw_deg, 0)
        self.assertEqual(clock.monotonic(), 1.0)
    def test_scheduler_is_phase_locked_and_coalesces(self):
        schedule = PhaseLockedScheduler(180, epoch=0)
        self.assertTrue(schedule.due(0))
        self.assertFalse(schedule.due(180))
        self.assertEqual(schedule.coalesced, 1)
        schedule.complete()
        self.assertFalse(schedule.due(359.9))
        self.assertTrue(schedule.due(360))
        self.assertEqual(schedule.next_due, 540)

    def test_scheduler_coalesces_an_overrun_without_phase_drift(self):
        schedule = PhaseLockedScheduler(180, epoch=0)
        self.assertTrue(schedule.due(0))
        self.assertFalse(schedule.due(725))  # still running; 4 periods elapsed
        self.assertEqual(schedule.coalesced, 1)
        self.assertEqual(schedule.next_due, 900)
        schedule.complete()
        self.assertFalse(schedule.due(899.9))
        self.assertTrue(schedule.due(900))

    def test_service_runs_only_on_phase_locked_due_times(self):
        clock = SimClock(); drive = SimPanDrive(clock)
        controller = ScanController(SimCamera(TexturedWorld(), drive, clock), drive,
                                    DirectoryPhotoSink(tempfile.mkdtemp()), clock, ScanConfig())
        service = ScanService(controller, PhaseLockedScheduler(180, epoch=180))
        self.assertIsNone(service.poll())
        clock.now = 180
        self.assertEqual(service.poll().state, ScanState.COMPLETE)
        self.assertIsNone(service.poll())

    def test_service_synchronous_overrun_skips_stale_slots(self):
        clock = SimClock(); drive = SimPanDrive(clock)
        config = ScanConfig(period_seconds=1)
        controller = ScanController(SimCamera(TexturedWorld(), drive, clock), drive,
                                    DirectoryPhotoSink(tempfile.mkdtemp()), clock, config)
        service = ScanService(controller, PhaseLockedScheduler(1, epoch=0))
        self.assertEqual(service.poll().state, ScanState.COMPLETE)
        self.assertGreater(service.scheduler.next_due, clock.monotonic())
        self.assertIsNone(service.poll())

    def test_simulation_is_deterministic_and_writes_inspectable_artifacts(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            one, _ = run_simulation(a, seed=7)
            two, _ = run_simulation(b, seed=7)
            self.assertEqual(one["state"], "complete")
            self.assertEqual(one["events"], two["events"])
            summary = json.loads((Path(a) / "summary.json").read_text())
            self.assertEqual(summary["scene_coverage_deg"], 290)
            self.assertEqual(len(list(Path(a).glob("*.pgm"))), 4)

    def test_multiple_texture_seeds_reliably_complete(self):
        for seed in range(50):
            with tempfile.TemporaryDirectory() as out:
                result, _ = run_simulation(out, seed=seed)
                self.assertEqual(result["state"], "complete")


if __name__ == "__main__":
    unittest.main()
