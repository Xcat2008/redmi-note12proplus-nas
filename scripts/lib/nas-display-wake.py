"""Bridge missing compositor wake events on this Redmi port, without grabbing keys."""
import glob
import logging
import os
import re
import select
import struct
import subprocess
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(message)s")
USER = "nas"
UID = 32011
DISPLAY_DEST = "org.gnome.Mutter.DisplayConfig"
DISPLAY_PATH = "/org/gnome/Mutter/DisplayConfig"
BRIGHTNESS = "/sys/class/leds/lcd-backlight/brightness"


def call(destination, path, method, *args):
    return subprocess.run(
        ["runuser", "-u", USER, "--", "env", f"XDG_RUNTIME_DIR=/run/user/{UID}",
         f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{UID}/bus",
         "gdbus", "call", "--session", "--dest", destination,
         "--object-path", path, "--method", method, *args],
        text=True, capture_output=True, timeout=4, check=True,
    ).stdout


def screen_mode():
    text = call(DISPLAY_DEST, DISPLAY_PATH, "org.freedesktop.DBus.Properties.Get",
                DISPLAY_DEST, "PowerSaveMode")
    match = re.search(r"<(-?\d+)>", text)
    return int(match.group(1)) if match else None


def wake():
    call("org.gnome.ScreenSaver", "/org/gnome/ScreenSaver",
         "org.gnome.ScreenSaver.SetActive", "false")
    call(DISPLAY_DEST, DISPLAY_PATH, "org.freedesktop.DBus.Properties.Set",
         DISPLAY_DEST, "PowerSaveMode", "<0>")
    # The vendor AAL caches brightness across panel power cycles. Reapply it.
    with open(BRIGHTNESS) as file:
        previous = int(file.read()) or 2047
    with open(BRIGHTNESS, "w") as file:
        file.write("0\n")
    time.sleep(0.15)
    with open(BRIGHTNESS, "w") as file:
        file.write(f"{previous}\n")
    logging.info("Requested screen wake; previous brightness=%s", previous)


def keypad():
    for event in glob.glob("/sys/class/input/event*/device/name"):
        with open(event) as file:
            if file.read().strip() == "mtk-kpd":
                return "/dev/input/" + event.split("/")[-3]
    raise RuntimeError("mtk-kpd input device not found")


def main():
    if "--wake" in sys.argv:
        wake()
        return
    event_format = struct.Struct("llHHi")
    device = keypad()
    logging.info("Monitoring power key on %s without an exclusive grab", device)
    was_off = False
    # Cache power changes before key dispatch. A synchronous query after key-down
    # races Phosh's automatic unblank and incorrectly observes the already-lit state.
    mode = None
    waiting_logged = False
    while mode is None:
        try:
            mode = screen_mode()
        except (OSError, ValueError, subprocess.SubprocessError):
            if not waiting_logged:
                logging.info("Waiting for the desktop display service")
                waiting_logged = True
        if mode is None:
            time.sleep(5)
    recently_unblanked = 0.0
    monitor = subprocess.Popen(
        ["runuser", "-u", USER, "--", "env", f"XDG_RUNTIME_DIR=/run/user/{UID}",
         f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{UID}/bus",
         "gdbus", "monitor", "--session", "--dest", DISPLAY_DEST,
         "--object-path", DISPLAY_PATH],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0,
    )
    os.set_blocking(monitor.stdout.fileno(), False)
    lines = b""
    with open(device, "rb", buffering=0) as stream:
        while True:
            ready, _, _ = select.select([stream, monitor.stdout], [], [])
            if stream in ready:
                data = stream.read(event_format.size)
                if len(data) != event_format.size:
                    raise RuntimeError("Input device disconnected")
                _, _, event_type, code, value = event_format.unpack(data)
                if event_type == 1 and code == 116:
                    try:
                        if value == 1:
                            was_off = mode == 3 or time.monotonic() - recently_unblanked < 0.4
                            logging.info("Power pressed: cached mode=%s; wake=%s", mode, was_off)
                        elif value == 0 and was_off:
                            was_off = False
                            time.sleep(0.25)
                            wake()
                    except (OSError, ValueError, subprocess.SubprocessError) as error:
                        logging.warning("Screen wake unavailable: %s", error)
            if monitor.stdout in ready:
                chunk = os.read(monitor.stdout.fileno(), 16384)
                if not chunk:
                    raise RuntimeError("Display signal monitor disconnected")
                lines += chunk
                while b"\n" in lines:
                    line, lines = lines.split(b"\n", 1)
                    match = re.search(rb"PowerSaveMode[^<]*<(?:int32 )?(-?\d+)>", line)
                    if match:
                        new_mode = int(match.group(1))
                        if mode == 3 and new_mode == 0:
                            recently_unblanked = time.monotonic()
                        mode = new_mode
                        logging.info("Display power changed: %s", mode)


if __name__ == "__main__":
    main()
