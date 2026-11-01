#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 José Miranda (Xcat2008)
"""Finish the NAS user's desktop setup and avoid an unused background store.

The phone shell and applications remain installed. OS update services are not
changed. Default: check only. Backups and restore state remain on the device.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import pwd

FILES = {
    'gnome-initial-setup-done': b'yes\n',
    'autostart/org.gnome.Software.desktop': (
        b'[Desktop Entry]\nType=Application\nName=Software\nHidden=true\n'
        b'Comment=Open the local software store manually on the NAS profile.\n'),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_path(home, relative):
    config = home / '.config'
    path = config / relative
    for item in (path, *path.parents):
        if item == home:
            break
        if item.is_symlink():
            raise ValueError('Desktop configuration symlinks need explicit review.')
    path.resolve().relative_to(home.resolve())
    if path.exists() and not path.is_file():
        raise ValueError('Expected a regular desktop configuration file.')
    return path


def configure(home, uid, gid, state_path, apply=False, restore=False):
    home = Path(home).resolve()
    state_path = Path(state_path)
    paths = {name: checked_path(home, name) for name in FILES}
    if state_path.is_symlink():
        raise ValueError('Refusing a symlink as the backup state.')
    state = json.loads(state_path.read_text()) if state_path.exists() else None
    if state and (state['home'] != str(home) or state['uid'] != uid or set(state['files']) != set(FILES)):
        raise ValueError('Backup belongs to a different desktop profile.')
    if restore:
        if not state:
            raise ValueError('No managed desktop backup exists.')
        # Validate the whole operation before changing any file.
        for name, path in paths.items():
            if not path.is_file() or digest(path.read_bytes()) != state['files'][name]['managedSha256']:
                raise ValueError('Desktop configuration changed since setup; preserving it.')
        if apply:
            for name, path in paths.items():
                old = state['files'][name]['originalBase64']
                if old is None:
                    path.unlink()
                else:
                    path.write_bytes(base64.b64decode(old, validate=True))
                    os.chown(path, uid, gid)
                    os.chmod(path, state['files'][name]['mode'])
            state_path.unlink()
        return {'action': 'restore', 'applied': apply, 'files': len(paths)}
    if state:
        for name, path in paths.items():
            if not path.is_file() or digest(path.read_bytes()) != state['files'][name]['managedSha256']:
                raise ValueError('Desktop configuration changed since setup; preserving it.')
        return {'action': 'configure', 'applied': False, 'alreadyConfigured': True, 'files': len(paths)}
    payloads = dict(FILES)
    # A completed existing GNOME setup marker must retain its original contents.
    marker = paths['gnome-initial-setup-done']
    if marker.exists():
        payloads['gnome-initial-setup-done'] = marker.read_bytes()
    state = {'schema': 1, 'home': str(home), 'uid': uid, 'files': {}}
    for name, path in paths.items():
        state['files'][name] = {
            'originalBase64': base64.b64encode(path.read_bytes()).decode() if path.exists() else None,
            'mode': path.stat().st_mode & 0o777 if path.exists() else 0o644,
            'managedSha256': digest(payloads[name]),
        }
    if apply:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        # Save recovery information before modifying user configuration.
        descriptor = os.open(state_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as handle:
            json.dump(state, handle)
        for name, path in paths.items():
            for directory in (home / '.config', home / '.config/autostart'):
                if not directory.exists():
                    directory.mkdir(mode=0o700)
                    os.chown(directory, uid, gid)
            path.write_bytes(payloads[name])
            os.chown(path, uid, gid)
            os.chmod(path, 0o644)
    return {'action': 'configure', 'applied': apply, 'alreadyConfigured': False, 'files': len(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user', required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Run with sudo.')
    if Path('/etc/homeio/hardware-profile').read_text().strip() != 'redmi-ruby-nas':
        parser.error('The explicit Redmi NAS hardware profile is required.')
    account = pwd.getpwnam(args.user)
    if account.pw_uid < 1000 or account.pw_dir in ('/', '/root', '/nonexistent'):
        parser.error('Use the normal desktop account.')
    state_path = Path('/var/lib/redmi-nas/desktop-profile') / (str(account.pw_uid) + '.json')
    print(json.dumps(configure(account.pw_dir, account.pw_uid, account.pw_gid, state_path,
                               apply=args.apply, restore=args.restore)))


if __name__ == '__main__':
    main()
