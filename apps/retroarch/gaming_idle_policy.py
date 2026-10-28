# SPDX-License-Identifier: AGPL-3.0-only
"""Cooperative empty-menu sleep; streaming services and loaded games stay awake."""
import collections
import json
import os
from pathlib import Path
import re
import time

WEB_PORTS = {3000, 3001, 3300, 3443, 8082, 48010}
STREAM_UDP_PORTS = {47998, 47999, 48000}


def tcp_viewers(text):
    count = 0
    for line in text.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 4:
            raise ValueError('incomplete socket table')
        if fields[3] == '01' and int(fields[1].split(':')[1], 16) in WEB_PORTS:
            count += 1
    return count


def udp_streams(text):
    count = 0
    for line in text.splitlines():
        if 'udp' not in line.split()[:4]:
            continue
        ports = set(map(int, re.findall(r'\b(?:sport|dport)=(\d+)\b', line)))
        if ports & STREAM_UDP_PORTS:
            count += 1
    return count


class StatusReader:
    """Consume private stdin-command replies without retaining content names."""
    def __init__(self):
        self.buffer = b''
        self.state = 'unknown'

    def feed(self, data):
        self.buffer += data
        forwarded = bytearray()
        marker = b'GET_STATUS '
        while self.buffer:
            index = self.buffer.find(marker)
            if index < 0:
                # Preserve a possibly split reply prefix across reads.
                keep = 0
                for n in range(1, min(len(marker), len(self.buffer)) + 1):
                    if marker.startswith(self.buffer[-n:]):
                        keep = n
                end = len(self.buffer) - keep
                forwarded.extend(self.buffer[:end])
                self.buffer = self.buffer[end:]
                break
            forwarded.extend(self.buffer[:index])
            self.buffer = self.buffer[index:]
            if self.buffer.startswith(marker + b'CONTENTLESS'):
                self.state = 'empty'
                self.buffer = self.buffer[len(marker + b'CONTENTLESS'):]
                continue
            if self.buffer.startswith(marker + b'PLAYING') or self.buffer.startswith(marker + b'PAUSED'):
                self.state = 'content'
                end = self.buffer.find(b'\n')
                if end < 0:
                    if len(self.buffer) > 8192:
                        self.buffer = b''
                    break
                self.buffer = self.buffer[end + 1:]
                continue
            if len(self.buffer) < len(marker) + 12:
                break
            # Unexpected protocol response: preserve availability, not idle mode.
            self.state = 'unknown'
            self.buffer = b''
        return bytes(forwarded)


def native_child(parent):
    # Vendor kernels may omit /proc/PID/task/TID/children.
    children = collections.defaultdict(list)
    identities = {}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            status = (p / 'status').read_text()
            ppid = int(re.search(r'^PPid:\s*(\d+)', status, re.M)[1])
            uid = int(re.search(r'^Uid:\s*(\d+)', status, re.M)[1])
            pid = int(p.name)
            children[ppid].append(pid)
            identities[pid] = ((p / 'comm').read_text().strip(), uid)
        except (OSError, ValueError, TypeError):
            continue
    pending = collections.deque([(parent, 0)])
    while pending:
        pid, depth = pending.popleft()
        if identities.get(pid) == ('retroarch', 32011):
            return pid
        if depth < 4:
            for child in children[pid]:
                pending.append((child, depth + 1))
    return None


class GamingIdlePolicy:
    def __init__(self, runtime='/run/redmi-gaming', grace=15):
        self.runtime = Path(runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.grace = grace
        self.renderer = None
        self.native_pid = None
        self.container_pid = None
        self.reader = StatusReader()
        self.last_activity = time.monotonic()
        self.next_query = 0
        self.next_write = 0
        self.mode = -1
        self.last_reason = None

    def attach(self, renderer, container_pid):
        self.detach()
        self.renderer = renderer
        self.container_pid = container_pid
        self.reader = StatusReader()
        self.last_activity = time.monotonic()
        self.next_query = self.next_write = 0
        self.mode = -1
        self.last_reason = None
        os.set_blocking(renderer.stdout.fileno(), False)
        os.set_blocking(renderer.stdin.fileno(), False)

    def _write(self, fps, reason, tcp=0, udp=0):
        now = time.monotonic()
        if self.native_pid is not None:
            target = self.runtime / ('menu-rate-' + str(self.native_pid))
            temp = target.with_suffix('.new')
            temp.write_text(f'{fps} {now + 5:.6f}\n')
            temp.chmod(0o644)
            os.replace(temp, target)
        if reason != self.last_reason or now >= self.next_write:
            data = {'mode': 'sleeping-empty-menu' if fps == 0 else 'game' if fps < 0 else 'interactive-menu',
                    'reason': reason, 'native_pid': self.native_pid,
                    'content_state': self.reader.state, 'tcp_viewers': tcp,
                    'udp_stream_flows': udp, 'monotonic': now,
                    'streaming_services_kept_running': True}
            temp = self.runtime / 'gaming-idle-state.json.new'
            temp.write_text(json.dumps(data))
            temp.chmod(0o644)
            os.replace(temp, self.runtime / 'gaming-idle-state.json')
            self.next_write = now + 2
        self.mode = fps
        self.last_reason = reason

    def detach(self):
        if self.native_pid is not None:
            self._write(-1, 'renderer-stopping')
        self.renderer = None
        self.native_pid = None

    def release(self):
        if self.native_pid is not None:
            self._write(-1, 'renderer-stopping')

    def _drain(self):
        for _ in range(8):
            try:
                data = os.read(self.renderer.stdout.fileno(), 65536)
            except BlockingIOError:
                break
            if not data:
                break
            forwarded = self.reader.feed(data)
            if forwarded:
                os.write(1, forwarded)

    def poll(self):
        if self.renderer is None or self.renderer.poll() is not None:
            return
        try:
            if self.native_pid is None:
                self.native_pid = native_child(self.renderer.pid)
            self._drain()
            now = time.monotonic()
            tcp = 0
            # Include the host's TLS reverse proxy as well as container sockets;
            # a newly opened browser must wake before the proxy opens upstream.
            for namespace in (str(self.container_pid), 'self'):
                for family in ('tcp', 'tcp6'):
                    tcp += tcp_viewers(Path(f'/proc/{namespace}/net/{family}').read_text())
            # Root namespace tracks the container's NATed GameStream UDP flows.
            # Entries persist briefly after disconnect, which is conservative.
            udp = udp_streams(Path('/proc/net/nf_conntrack').read_text())
            viewers = tcp > 0 or udp > 0
            if viewers or self.reader.state == 'content':
                self.last_activity = now
            if self.reader.state == 'content':
                fps, reason = -1, 'content-running'
            elif self.reader.state != 'empty' or self.native_pid is None:
                fps, reason = -1, 'awaiting-content-status'
            elif viewers:
                fps, reason = 60, 'viewer-connected'
            elif now - self.last_activity < self.grace:
                fps, reason = 60, 'idle-grace'
            else:
                fps, reason = 0, 'no-content-or-viewer'
            self._write(fps, reason, tcp, udp)
            # A quiescent menu cannot poll stdin. Its cached empty state is
            # valid until a viewer wakes it; never fill a paused pipe.
            if fps != 0 and now >= self.next_query:
                self.renderer.stdin.write(b'GET_STATUS\n')
                self.renderer.stdin.flush()
                self.next_query = now + 1
        except (OSError, ValueError, RuntimeError):
            # Any uncertainty releases the rendering limit immediately.
            self.reader.state = 'unknown'
            self.last_activity = time.monotonic()
            try:
                self._write(-1, 'observer-unavailable')
            except OSError:
                pass
