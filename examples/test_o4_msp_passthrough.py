# SPDX-License-Identifier: GPL-3.0-or-later
import contextlib
import io
import struct
import unittest

from o4_msp_passthrough import battery_reply, main, sample, status_reply


class O4PacketTests(unittest.TestCase):
    def check_frame(self, frame, command, length):
        self.assertEqual(frame[:5], b"$M>" + bytes((length, command)))
        self.assertEqual(len(frame), length + 6)
        checksum = 0
        for value in frame[3:]:
            checksum ^= value
        self.assertEqual(checksum, 0)

    def test_battery_example_and_sweep(self):
        frame = battery_reply(15.5)
        self.check_frame(frame, 130, 11)
        self.assertEqual(frame.hex(), "244d3e0b820498089b00000000000e068e")
        for elapsed, voltage in ((0, 1200), (4, 1680), (8, 1200)):
            frame, _ = sample(True, elapsed)
            self.assertEqual(struct.unpack_from("<H", frame, 14)[0], voltage)

    def test_dry_run_needs_no_serial_port(self):
        for flag in ("--status", "--battery-state"):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main([flag, "--dry-run"]), 0)
            self.assertEqual(len(output.getvalue().splitlines()), 4)

    def test_status_layout_and_arm_sequence(self):
        for elapsed, armed in ((0, 0), (5, 1), (10, 0), (15, 0), (20, 1)):
            frame, _ = sample(False, elapsed)
            self.check_frame(frame, 101, 27)
            self.assertEqual(struct.unpack_from("<I", frame, 11)[0], armed)
        disarmed = status_reply(False)
        armed = status_reply(True)
        self.assertEqual([i for i, (a, b) in enumerate(zip(disarmed, armed)) if a != b],
                         [11, 32])


if __name__ == "__main__":
    unittest.main()
