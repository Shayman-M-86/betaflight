# DJI O4 shows 0 V or does not recognise arming

This guide is for you if:

- You have a picture in the goggles.
- Betaflight's on-screen display shows the correct battery voltage.
- DJI's own battery display stays at 0 V.
- The O4 does not recognise arming, stays in low-power mode, or does not start
  recording automatically when it should.

We have made a software workaround that may help this combination of symptoms.
It runs on the flight controller. You do not need to change the O4 firmware or
keep a computer connected after installation.

**Hardware tested:** on 15 October 2026, the owner reported that the custom
firmware worked on their O4/flight-controller setup and the original issues
were resolved. It is based on stable Betaflight 2026.6.2, but is a community
workaround rather than an official release. Other setups still need testing.

## 1. Get firmware for your flight controller

You need a custom **`.hex` firmware file made for your exact flight controller**,
with this O4 workaround included. It also needs your usual receiver and other
required features.

**There are no public ready-to-download firmware releases yet.** If you do not
already have a matching file, ask for a board-specific build in
[the workaround discussion](https://github.com/betaflight/betaflight/discussions/15847). Include:

- Your exact flight controller model.
- The output of `version` in Betaflight's CLI tab.
- Your receiver type, such as ELRS/CRSF, and required extras such as GPS.

Do not use a file made for somebody else's board. Selecting normal firmware
from Betaflight's online flasher does not include this workaround.

## 2. Back up your current settings

Before flashing:

1. Connect to Betaflight and open **CLI**.
2. Enter `diff all`.
3. Save the output in a text file.
4. Take a screenshot of the **Ports** tab and keep the original firmware
   version/board details so you can go back if needed.

## 3. Flash the custom firmware

Remove the propellers and disconnect the flight battery for flashing.

1. Open Betaflight's **Firmware Flasher**.
2. Choose **Load Firmware [Local]**.
3. Select the matching custom `.hex` file.
4. Flash it, reconnect, and restore the saved settings as appropriate for that
   board and firmware version. Save and reboot.

If you are unsure about restoring the backup or the board name does not match,
get help before proceeding.

## 4. Check the O4 connection

In **Ports**, check the UART wired to the O4:

- **MSP** is enabled.
- **VTX (MSP + DisplayPort)** is selected.

Keep your receiver settings and any VTX power-control settings as required by
your aircraft. There is no additional command to turn the workaround on: it is
already enabled in a correctly built custom file.

## 5. Try it on the bench

Keep the props off and provide airflow over the O4. Close Configurator and
disconnect USB. Turn on your radio and goggles, then connect the flight battery.
Check these separately:

- DJI's native battery display matches the real battery voltage.
- The O4 recognises real arm and disarm changes.
- It leaves low-power mode when armed.
- Recording starts when armed, if DJI automatic recording is enabled.
- Your normal Betaflight on-screen display still works.

A successful bench test does not establish flight reliability. If anything
behaves unexpectedly, stop testing and restore the original firmware and backup.

## If it does not work

Check that you used the correct custom file and restored the O4's UART settings.
Then reply in [the workaround discussion](https://github.com/betaflight/betaflight/discussions/15847)
with your FC, O4 and goggles models/firmware,
and which checks above passed or failed. Similar symptoms can have different
causes, so this will not fix every O4 problem or repair damaged hardware.

## How was this discovered?

Read [the short background story and test GIFs](O4_STORY.md).

## Want the technical details?

The [technical guide](O4_TELEMETRY_PUSH.md) contains the code changes, bench
experiment, build instructions and test results. You do not need to follow the
Python experiment just to install a matching custom firmware file.
