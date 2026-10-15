# DJI O4 unsolicited battery and arming telemetry

This experimental patch lets Betaflight send battery and armed-state MSP replies
without waiting for requests from the air unit. It is intended for an O4 whose
video and DisplayPort OSD work but whose normal battery/arming telemetry does
not. It is disabled by default and is not an official Betaflight release.

**Base:** Betaflight 2026.6.2, `e0b7bb01b17b21351057e9ead2d1ab39dd44fa16`.
**Scope:** MSP_BATTERY_STATE (130) and MSP_STATUS (101), on the configured MSP
DisplayPort port, at up to 10 Hz each. No board-specific UART or build profile
is required by the patch.

## Start here

This guide matches a specific symptom combination: video works, the Betaflight
DisplayPort OSD displays live values, but DJI's separate native battery indicator
shows 0 V and the O4 does not recognize arming. A missing OSD or an FC that itself
reports zero battery voltage needs normal setup/hardware troubleshooting first.
The same visible symptoms can have different causes.

1. Back up the FC configuration and identify the exact FC board, firmware,
   goggles and O4 firmware. Check the normal MSP/DisplayPort UART setup and
   wiring before considering a custom firmware workaround.
2. [Get this branch](#get-the-source). The fork's default `master` branch does
   not contain the workaround; select `codex/o4-unsolicited-telemetry`.
3. [Run the passthrough experiment](#reproduce-the-passthrough-experiment),
   with props removed and O4 ventilation. This tests whether your O4 accepts
   the responses without changing its FC firmware.
4. If the synthetic battery and status replies produce the expected native
   UI changes, [build the workaround](#build) for your exact FC board with
   `USE_DJI_O4_TELEMETRY_PUSH` added to your normal build options.
5. Load that local HEX, restore the required configuration, then run the
   [physical validation](#automated-and-physical-validation) with real FC
   values and passthrough disabled. Keep the original firmware for rollback.
6. Share the results using the [report template](#report-results), including
   failures and partial successes. Passing one experiment is not a universal fix.

No stock-firmware CLI setting installs this patch. The code must be built from
this branch. Adding its custom define to an upstream cloud build alone does not
supply the code. Do not flash a firmware image made for somebody else's board.

## Get the source

```bash
git clone --depth 1 --single-branch --branch codex/o4-unsolicited-telemetry https://github.com/Shayman-M-86/betaflight.git betaflight-o4-workaround
cd betaflight-o4-workaround
```

For the build toolchain and host dependencies, follow the
[Betaflight development instructions](https://betaflight.com/docs/development).
Use the complete guide below rather than copying only a build define.

## Exactly what changed

- [Original implementation commit and complete diff](https://github.com/Shayman-M-86/betaflight/commit/0d11aff655704b10cabeb7457b37c0de28bf4fc8): a stable link to the code, tests, and original guide.
- [Current workaround branch](https://github.com/Shayman-M-86/betaflight/tree/codex/o4-unsolicited-telemetry): the maintained guide and source.
- [Serial task hook](src/main/fc/tasks.c): calls the opt-in timer.
- [DisplayPort timer](src/main/io/displayport_msp.c): selects the configured port and schedules the two responses.
- [MSP response helper](src/main/msp/msp_serial.c): reuses the live serializer and existing frame encoder with TX-space checks.
- [Regression tests](src/test/unit/msp_serial_unittest.cc) and [bench reproduction helper](examples/o4_msp_passthrough.py).

## Evidence and limits

The reported bench setup was a DJI O4 Air Unit Lite connected to a NewBeeDrone
Hummingbird AIO255. The O4 had physical PCB damage near a mounting hole.
Video and Betaflight DisplayPort OSD worked, but DJI native voltage stayed at
zero and armed-state behavior was missing. The symptoms also occurred with a
second FC. Damage to the O4-to-FC transmit path is a working diagnosis, not a
confirmed electrical measurement.

The FC was placed in serial passthrough. Python then transmitted unsolicited
MSP v1 responses through FC TX to O4 RX:

```text
PC --USB--> FC serial passthrough --UART TX--> O4 RX
```

The operator reported that `MSP_BATTERY_STATE` updated the DJI native voltage
and `MSP_STATUS` conveyed armed/disarmed state. Other tested commands did not
produce a visible effect. That does not establish that those commands were
rejected, nor that these two commands suffice for every DJI device/firmware.

This demonstrates acceptance of the tested unsolicited replies. Compilation
and automated tests also passed for the firmware implementation, but successful
operation of the custom firmware on the physical FC/O4 has not been confirmed
in the published evidence. Low-power exit and automatic recording must be
checked explicitly on the installed firmware. Flight validation is not claimed.

## Implementation

Builds with `USE_DJI_O4_TELEMETRY_PUSH` do the following:

1. The existing serial task calls `displayPortMspPushTelemetry(millis())`.
2. A rollover-aware 100 ms timer selects `displayPortMspGetSerial()`. This uses
   the port already configured for MSP plus VTX/MSP DisplayPort.
3. `mspSerialPushTelemetry()` selects that allocated MSP port and descriptor.
   It accepts only the two read-only command IDs listed above.
4. An empty synthetic request goes through `mspFcProcessCommand()`. The normal
   serializers produce the current battery measurements and actual armed state.
5. `mspSerialPush()` frames each payload as an MSP v1 response (`$M>`), including
   its length and checksum.

No firmware payload layouts are duplicated, and no receiver, motor, GPS or
flight-control algorithm is changed. The 64-byte scratch buffer covers the
allowed 2026.6.2 replies: 11 bytes for BATTERY_STATE and at most 42 for STATUS,
including extended mode flags. This bound must be reviewed when porting to
another release or expanding the command allowlist.

Pushes are skipped in CLI mode, for missing/unallocated ports, USB VCP, and
broadcast identifiers. A response is dropped when the target UART lacks room
for the whole frame, rather than blocking to wait for space. Normal requested
MSP replies and DisplayPort traffic remain in their existing paths. The timer
runs independently of OSD redraws. At nominal rate the payloads add roughly
500 bytes/s before any extended mode flags, about 4.4% of a 115200-baud 8N1 link.

The option applies to whichever device is attached to the configured DisplayPort
port; it does not probe for DJI hardware. There is currently no runtime CLI
switch for it. Omit the build define to remove the workaround.

## Build

Start from this fork's `codex/o4-unsolicited-telemetry` branch. Keep the existing
board configuration and choose your normal receiver, motor and optional hardware
features separately. Add `USE_DJI_O4_TELEMETRY_PUSH` to the build's `OPTIONS`.
For example, from the repository directory on a supported build environment:

```bash
make arm_sdk_install
make CONFIG=HUMMINGBIRD_AIO255 OPTIONS=USE_DJI_O4_TELEMETRY_PUSH
```

This example uses Betaflight's broad default feature set. It does not prescribe
settings for another aircraft. With a selective `CLOUD_BUILD` profile, include
MSP DisplayPort/digital OSD support and preserve all dependencies of your normal
features, then add the workaround define to that profile.

The target build writes the HEX into `obj/`. Back up `diff all` and retain the
original firmware before using Firmware Flasher -> Load Firmware [Local]. Use
an image built for the exact board and restore the required configuration.
MSP and VTX/MSP DisplayPort must be enabled on the connected O4 UART. This patch
does not configure that UART or power-control pins for you.

## Reproduce the passthrough experiment

The small [Python example](examples/o4_msp_passthrough.py) reproduces the packet
formats and animations used by the successful experiments. Its packet framing
and payloads have automated checks; the original hardware observations came
from the earlier experiment script, not from a new hardware run of this helper.

Remove props and ventilate the O4. Enter serial passthrough in the FC CLI using
the correct identifier for your UART. On the reported board, this was:

```text
serialpassthrough UART4 115200 rxtx
```

Close Configurator to release the FC USB port, then run one test at a time:

```bash
python -m pip install pyserial
python examples/o4_msp_passthrough.py --port COM6 --battery-state
python examples/o4_msp_passthrough.py --port COM6 --status
```

Replace COM6 with your FC USB port. Press Enter at the startup prompt and then
connect the LiPo. The helper sends at approximately 10 Hz for 30 seconds:

- Battery state: synthetic four-cell battery, 2200 mAh capacity, voltage
  sweeping 12.0 -> 16.8 -> 12.0 V with both voltage fields updated.
- Status: synthetic DISARMED / ARMED / DISARMED, five seconds per phase,
  repeated. Adjacent disarmed phases last ten seconds together. A final
  disarmed reply is attempted on completion or interruption.

These are synthetic telemetry replies, not commands to arm the FC. Watch the
DJI native indicators rather than the separate Betaflight DisplayPort OSD.
For the STATUS experiment, note low-power exit, automatic recording, and any
native armed-state UI change separately. Power-cycle the FC to exit passthrough
and between independent experiments. Do not use fake telemetry for flight.

Inspect packets without hardware with `--dry-run`, for example:

```bash
python examples/o4_msp_passthrough.py --status --dry-run
```

MSP v1 response shape:

```text
24 4D 3E | payload length | command | payload bytes | XOR checksum
 $  M  >       uint8        uint8
```

Multi-byte fields are little-endian. The XOR includes the length, command, and
all payload bytes, excluding the three-byte header.

| Reply | Test payload shape | Significant fields |
| --- | --- | --- |
| BATTERY_STATE, 130 | 11 bytes; Python `<BHBHHBH` | Cells; capacity; legacy voltage (0.1 V); consumed mAh; current (0.01 A); battery state; precise voltage (0.01 V) |
| STATUS, 101 | 27 bytes in the synthetic example | Mode flags are uint32 at payload offset 6; ARM is bit 0. The helper sends ACC+GYRO sensor mask 0x21 and no arming-disable flags. |

The firmware uses the full live serializers, including extended status flags
when present; it does not use the example's fake values.

## Automated and physical validation

Run the focused tests:

```bash
make -C src/test CC=gcc CXX=g++ test_msp_serial_unittest
python -m unittest discover -s examples -p 'test_o4_msp_passthrough.py' -v
```

The C/C++ tests mock the serializer and UART while compiling the real serial
encoder and DisplayPort timer. They cover live serializer invocation, framing
and checksum, exact buffer capacity, TX backpressure, unavailable/wrong ports,
CLI/USB exclusions, rejected commands, serializer errors, and timer rollover.
The Python tests check the reproduction helper's payloads and state sequence.
All 11 focused C/C++ tests and 3 Python tests passed for this branch. The three
modified production C files also passed Arm compiler syntax checks using the
HUMMINGBIRD_AIO255 build flags. Earlier HUMMINGBIRD_AIO255 firmware builds linked
the implementation against the actual serializers; the custom firmware's
physical FC/O4 behavior remains to be confirmed.

For physical validation, use real FC telemetry with passthrough disabled and
confirm native voltage matches the battery, real arm/disarm is recognized,
low-power behavior and auto-record work, and DisplayPort OSD remains functional.
Record the exact FC build/board, O4 model/firmware, goggles model/firmware,
serial configuration and observations. A short recording that shows the
native indicators and actual arm switch would make the results easier to review.

## Upstream discussion

This is an experimental opt-in capability for a device-side telemetry failure,
not evidence of a Betaflight regression. Before proposing it upstream, discuss
whether maintainers want this capability and whether compile-time or runtime
selection is appropriate. An upstream PR should be ported and tested against
current master; this branch remains pinned to the release used in the experiment.
The existing Betaflight license and contribution guidance apply.

## Report results

Reply in the public community discussion where this guide was shared. Include
this information so people can distinguish similar symptoms with different
causes. A video of the native battery/arming indicators is useful if available.

```text
Source commit / Betaflight version:
FC board and MCU:
O4 model and firmware:
Goggles model and firmware:
Receiver system:
MSP/DisplayPort UART and baud rate:
Original symptom (include whether Betaflight OSD worked):
Passthrough BATTERY_STATE result:
Passthrough STATUS result:
Custom firmware tested? Which board build/options?
Native voltage matches the real battery:
Real arm/disarm recognized:
Low-power exit on arm:
Automatic recording starts/stops as expected:
DisplayPort OSD still works:
Other behavior / rollback result:
```

State whether a result came from synthetic passthrough replies or real telemetry
on the custom firmware. Keep those observations separate. The
[existing Betaflight O4 discussion](https://github.com/betaflight/betaflight/discussions/15412)
reports similar symptoms, but its underlying fault has not been established as
the same one. General hardware/setup support belongs in the community rather
than a firmware bug report; see [Betaflight's contribution guidance](https://github.com/betaflight/betaflight/blob/master/CONTRIBUTING.md).
