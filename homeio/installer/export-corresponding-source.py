#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 José Miranda (Xcat2008)
"""Export the installed Homeio source, never its environment or runtime data.

Run after applying the project patches and before creating .env/building.
The upstream tracked paths plus this project's explicit source overlay are the
only inputs. Never archive the installation directory recursively.
"""
import argparse
import io
from pathlib import Path, PurePosixPath
import subprocess
import tarfile


def safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(p in ('..', '.', '') for p in path.parts):
        raise ValueError('Unsafe source path')
    if any(p in ('.git', 'node_modules', '.next', 'data', 'logs', '__pycache__') for p in path.parts):
        return False
    if any(p.startswith('.env') for p in path.parts):
        return False
    if path.suffix.lower() in ('.pem', '.key', '.db', '.sqlite', '.sqlite3', '.log'):
        return False
    return str(path) != 'public/homeio-corresponding-source.tar.gz'


def regular_source(base, name):
    candidate = base / name
    # Do not follow symlinks, including parent directory symlinks.
    for parent in (candidate, *candidate.parents):
        if parent == base:
            break
        if parent.is_symlink():
            raise ValueError('Source symlinks require explicit review')
    candidate.resolve().relative_to(base.resolve())
    if not candidate.is_file():
        raise ValueError('Missing tracked source file: ' + name)
    return candidate


def source_paths(base, overlay):
    tracked = subprocess.check_output(['git', '-C', str(base), 'ls-files', '-z']).decode('utf-8').split('\0')
    names = {name for name in tracked if name and safe_name(name)}
    for file in overlay.rglob('*'):
        if file.is_symlink():
            raise ValueError('Overlay symlinks require explicit review')
        if file.is_file():
            name = file.relative_to(overlay).as_posix()
            if safe_name(name):
                names.add(name)
    return sorted(names)


def export(base, overlay, output):
    base = Path(base).resolve()
    overlay = Path(overlay).resolve()
    output = Path(output)
    names = source_paths(base, overlay)
    if not names:
        raise ValueError('No source files found')
    revision = subprocess.check_output(['git', '-C', str(base), 'rev-parse', 'HEAD']).decode().strip()
    # Validate and read before replacing any previous public archive.
    files = [(name, regular_source(base, name)) for name in names]
    temporary = output.with_name(output.name + '.new')
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(temporary, 'w:gz', format=tarfile.PAX_FORMAT) as archive:
            for name, path in files:
                payload = path.read_bytes()
                info = tarfile.TarInfo('homeio/' + name)
                info.size = len(payload)
                info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                info.mtime = 0
                archive.addfile(info, io.BytesIO(payload))
            recipe = ('Homeio corresponding source\n\n'
                      'Upstream baseline commit: ' + revision + '\n'
                      'This archive contains the patched source actually installed, including build scripts.\n'
                      'Use Node 22.23.4 and npm ci, then npm run build. The build script invokes\n'
                      'next build --webpack and the server TypeScript build. Runtime deployment\n'
                      'also requires a fresh private environment and PostgreSQL; neither accounts\n'
                      'nor runtime databases belong in this archive. No build is needed to read source.\n'
                      'Phone setup and integration source: https://github.com/Xcat2008/redmi-note12proplus-nas\n'
                      'Retain the included upstream and per-file licences.\n').encode()
            info = tarfile.TarInfo('BUILD-SOURCE.md')
            info.size = len(recipe)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(recipe))
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('homeio_source', type=Path)
    parser.add_argument('project_overlay', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print('Corresponding source files:', export(args.homeio_source, args.project_overlay, args.output))


if __name__ == '__main__':
    main()
