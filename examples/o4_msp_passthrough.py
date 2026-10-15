#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bench-only reproduction of the unsolicited O4 battery/status experiment."""
import argparse
import math
import struct
import time


def make_reply(command, payload):
    checksum = len(payload) ^ command
    for value in payload:
        checksum ^= value
    return b"$M>" + bytes((len(payload), command)) + payload + bytes((checksum,))


def battery_reply(voltage):
    return make_reply(130, struct.pack("<BHBHHBH", 4, 2200,
                                      round(voltage * 10), 0, 0, 0,
                                      round(voltage * 100)))


def status_reply(armed):
    payload = struct.pack("<HHHIB", 125, 0, 0x21, int(armed), 0)
    payload += struct.pack("<HHBBIBHBBB", 0, 0, 0, 30, 0, 0, 40, 6, 3, 0)
    return make_reply(101, payload)


def sample(battery, elapsed):
    if battery:
        triangle = 1 - abs(2 * (elapsed % 8 / 8) - 1)
        voltage = 12 + 4.8 * triangle
        return battery_reply(voltage), f"Synthetic voltage: {voltage:.2f} V"
    armed = int(elapsed / 5) % 3 == 1
    return status_reply(armed), "Synthetic state: " + ("ARMED" if armed else "DISARMED")


def write_packet(port, packet):
    if port.write(packet) != len(packet):
        raise OSError("Incomplete serial write")
    port.flush()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--battery-state", action="store_true")
    group.add_argument("--status", action="store_true")
    parser.add_argument("--port", help="Flight controller USB port, e.g. COM6")
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error("--seconds must be finite and positive")
    if args.dry_run:
        for elapsed in (0, 4, 5, 10):
            packet, label = sample(args.battery_state, elapsed)
            print(f"{label}: {packet.hex(' ')}")
        return 0
    if not args.port:
        parser.error("--port is required for a live test")
    try:
        import serial
    except ImportError:
        parser.error("Install pyserial first: python -m pip install pyserial")
    print("Props removed. FC already in serialpassthrough. Keep the O4 ventilated.")
    print("These values are synthetic, not live flight-controller telemetry.")
    try:
        with serial.Serial(args.port, 115200, timeout=0.01, write_timeout=1) as port:
            input("Press Enter when ready, then connect the LiPo: ")
            print("Waiting five seconds for startup...")
            time.sleep(5)
            start = time.monotonic()
            last_display = -1
            try:
                while True:
                    elapsed = time.monotonic() - start
                    if elapsed >= args.seconds:
                        break
                    packet, label = sample(args.battery_state, elapsed)
                    write_packet(port, packet)
                    if int(elapsed) != last_display:
                        print(f"[+{elapsed:5.1f}s] {label}", flush=True)
                        last_display = int(elapsed)
                    time.sleep(0.1)
            finally:
                if args.status:
                    try:
                        write_packet(port, status_reply(False))
                    except (serial.SerialException, OSError):
                        print("Final disarmed reply could not be sent.")
    except KeyboardInterrupt:
        print("Stopped.")
    except (serial.SerialException, OSError, EOFError) as error:
        print(f"Test failed: {error}")
        return 1
    finally:
        print("Power-cycle the FC to exit passthrough.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
