#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Run the Mali-backed NAS application in its Homeio virtual display."""
import json
import os
from pathlib import Path
import signal
import shutil
import socket
import subprocess
import time
import http.client
import sys
from gaming_idle_policy import GamingIdlePolicy

ROOT = Path('/DATA/AppData/custom-retroarch')
stopping = False
idle_policy = None


def stop_signal(_signum, _frame):
    global stopping
    stopping = True


def command(args, **kwargs):
    return subprocess.run(args, check=True, timeout=20, **kwargs)


def container_state():
    # Read the local engine directly; avoid starting the Docker CLI every poll.
    connection = http.client.HTTPConnection('localhost', timeout=3)
    connection.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.sock.settimeout(3)
    try:
        connection.sock.connect('/var/run/docker.sock')
        connection.request('GET', '/containers/retroarch/json')
        response = connection.getresponse()
        if response.status == 404:
            return 0
        if response.status != 200:
            raise RuntimeError('Local container status unavailable')
        data = response.read(2 * 1024 * 1024)
        state = json.loads(data)['State']
        return int(state['Pid']) if state['Running'] else 0
    finally:
        connection.close()


def terminate(process):
    monitored = idle_policy is not None and idle_policy.renderer is process
    if monitored:
        idle_policy.release()
    if process is None or process.poll() is not None:
        if monitored:
            idle_policy.detach()
        return
    try:
        os.killpg(process.pid, signal.SIGCONT)
        os.killpg(process.pid, signal.SIGTERM)
        deadline = time.monotonic() + 8
        while process.poll() is None and time.monotonic() < deadline:
            if monitored:
                idle_policy._drain()
            time.sleep(0.05)
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
    except ProcessLookupError:
        pass
    finally:
        if monitored:
            idle_policy.detach()


def prepare():
    native = ROOT / 'native'
    native.mkdir(parents=True, exist_ok=True)
    os.chown(native, 32011, 32011)
    config = native / 'retroarch.cfg'
    if not config.exists():
        shutil.copyfile('/usr/local/lib/redmi-nas/retroarch/retroarch-homeio.cfg', config)
        os.chown(config, 32011, 32011)
    (native / 'playlists').mkdir(exist_ok=True)
    os.chown(native / 'playlists', 32011, 32011)
    data = Path('/home/nas/.local/share/retroarch')
    data.mkdir(parents=True, exist_ok=True)
    for parent in (data, data.parent, data.parent.parent):
        os.chown(parent, 32011, 32011)
    for name in ('cores', 'info', 'autoconfig'):
        folder = data / name
        folder.mkdir(parents=True, exist_ok=True)
        os.chown(folder, 32011, 32011)
    for origin, target, pattern in (
            (Path('/usr/lib/aarch64-linux-gnu/libretro'), data / 'cores', '*_libretro.so'),
            (Path('/usr/local/share/redmi-nas/retroarch/cores'), data / 'cores', '*_libretro.so'),
            (Path('/usr/share/libretro/info'), data / 'info', '*.info')):
        for file in origin.glob(pattern):
            destination = target / file.name
            if not destination.exists():
                shutil.copyfile(file, destination)
                os.chown(destination, 32011, 32011)
    marker = data / '.homeio-controllers-initialized'
    if not marker.exists():
        for origin in (Path('/usr/share/libretro/autoconfig'),
                       Path('/usr/local/share/redmi-nas/retroarch/autoconfig')):
            for file in origin.rglob('*.cfg'):
                destination = data / 'autoconfig' / file.relative_to(origin)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    shutil.copyfile(file, destination)
                    os.chown(destination, 32011, 32011)
        marker.touch()
        os.chown(marker, 32011, 32011)
        for directory in (data / 'autoconfig').rglob('*'):
            if directory.is_dir():
                os.chown(directory, 32011, 32011)
    autostart = ROOT / 'config/.config/openbox/autostart'
    managed = '# Rendering is supervised by redmi-retroarch-homeio.service.\n'
    if autostart.exists() and autostart.read_text() != managed:
        autostart.write_text(managed)
        subprocess.run(['docker', 'exec', '-u', 'abc', 'retroarch',
                        'pkill', '-TERM', '-x', 'retroarch'], check=False, timeout=8)
    # A second authenticated local socket lets the native renderer feed the
    # container's audio capture without routing sound to the phone speakers.
    pulse = ROOT / 'config/.XDG/nas-pulse'
    modules = command(['docker', 'exec', '-u', 'abc', 'retroarch', 'pactl',
                       'list', 'short', 'modules'], capture_output=True, text=True).stdout
    if 'socket=/config/.XDG/nas-pulse' not in modules:
        if pulse.is_socket():
            pulse.unlink()
        command(['docker', 'exec', '-u', 'abc', 'retroarch', 'pactl',
                 'load-module', 'module-native-protocol-unix',
                 'socket=/config/.XDG/nas-pulse', 'auth-anonymous=false'])
    command(['docker', 'exec', 'retroarch', 'test', '-S', '/tmp/.X11-unix/X1'])
    # The shared transport is application-neutral; no RetroArch backdrop on Steam startup.
    subprocess.run(['docker', 'exec', '-u', 'abc', '-e', 'DISPLAY=:1', 'retroarch',
                    'xsetroot', '-solid', '#101827'], check=False, timeout=8)


def start_renderer(pid):
    # Only network and IPC namespaces are shared: X11's abstract socket and
    # MIT-SHM buffers then work, while the phone's native Mali/Android libraries
    # stay available. No phone Wayland session or lock-screen access is needed.
    args = ['nsenter', '-t', str(pid), '-n', '-i', 'runuser', '-u', 'nas', '--',
            'env', 'LD_LIBRARY_PATH=/usr/local/lib/redmi-nas/retroarch/vulkan',
            'NAS_VK_NATIVE_DRIVER=/usr/local/lib/redmi-nas/retroarch/vulkan/libvulkan_malisx2.so',
            'ARMSX2_RENDERER=Vulkan', 'DISPLAY=:1', 'HYBRIS_EGLPLATFORM=x11', 'EGL_PLATFORM=x11',
            'LD_PRELOAD=/usr/local/lib/redmi-nas/retroarch/x11-bgra.so:/usr/local/lib/redmi-nas/retroarch/udev-host-netlink.so',
            'WAYLAND_DISPLAY=redmi-nas-no-wayland',
            'XDG_RUNTIME_DIR=' + str(ROOT / 'config/.XDG'),
            'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/redmi-gaming/no-phone-bus',
            'PULSE_SERVER=unix:' + str(ROOT / 'config/.XDG/nas-pulse'),
            '/usr/bin/retroarch', '--verbose', '--config',
            str(ROOT / 'native/retroarch.cfg'), '--menu']
    # Create udev sockets before entering X11's network namespace. The scoped
    # preload hands them to libudev so gamepads still reconnect dynamically.
    monitors = [socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 15) for _ in range(8)]
    fds = tuple(monitor.fileno() for monitor in monitors)
    args.insert(args.index('/usr/bin/retroarch'),
                'REDMI_NAS_UDEV_FDS=' + ','.join(str(fd) for fd in fds))
    try:
        return subprocess.Popen(args, start_new_session=True, pass_fds=fds,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
    finally:
        for monitor in monitors:
            monitor.close()


def start_sunshine():
    return subprocess.Popen([
        'docker', 'exec', '-u', 'abc', '-e', 'DISPLAY=:1',
        '-e', 'PULSE_SERVER=unix:/defaults/native', 'retroarch',
        '/usr/bin/sunshine', '/config/.config/sunshine/sunshine.conf'
    ], start_new_session=True)


def stop_sunshine(process):
    if process is not None and process.poll() is None:
        try:
            subprocess.run(['docker', 'exec', 'retroarch', 'pkill', '-TERM', '-x',
                            'sunshine'], timeout=8, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.SubprocessError:
            pass
    terminate(process)


signal.signal(signal.SIGTERM, stop_signal)
signal.signal(signal.SIGINT, stop_signal)
renderer = sunshine = None
render_enabled = '--runtime-only' not in sys.argv
runtime_enabled = '--renderer-only' not in sys.argv
prepared_generation = 0
ready_file = Path('/run/redmi-gaming/runtime-ready')
generation = 0
checked_at = 0
pid = 0
idle_policy = GamingIdlePolicy()
try:
    while not stopping:
        try:
            if time.monotonic() - checked_at >= 4:
                pid = container_state()
                checked_at = time.monotonic()
            if pid != generation:
                terminate(renderer)
                stop_sunshine(sunshine)
                renderer = sunshine = None
                generation = pid
                prepared_generation = 0
            if pid:
                if runtime_enabled and prepared_generation != pid:
                    prepare()
                    ready_file.write_text(str(pid))
                    prepared_generation = pid
                ready = runtime_enabled or (ready_file.exists() and ready_file.read_text().strip() == str(pid))
                if render_enabled and ready and (renderer is None or renderer.poll() is not None):
                    renderer = start_renderer(pid)
                    idle_policy.attach(renderer, pid)
                if runtime_enabled and (sunshine is None or sunshine.poll() is not None):
                    sunshine = start_sunshine()
                if render_enabled:
                    idle_policy.poll()
        except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
            print('NAS gaming session: ' + str(exc), flush=True)
            terminate(renderer)
            stop_sunshine(sunshine)
            renderer = sunshine = None
            generation = 0
        time.sleep(0.25)
finally:
    terminate(renderer)
    stop_sunshine(sunshine)
