# SPDX-License-Identifier: AGPL-3.0-only
import importlib.util
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('source_export', Path(__file__).with_name('export-corresponding-source.py'))
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class SourceExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.base = root / 'homeio'
        self.overlay = root / 'overlay'
        self.output = root / 'source.tar.gz'
        self.base.mkdir()
        self.overlay.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.base)], check=True)
        for name, value in [('source.ts', 'original source'), ('.env', 'private-password'), ('package.json', '{}')]:
            (self.base / name).write_text(value)
        subprocess.run(['git', '-C', str(self.base), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.base), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'], check=True)

    def test_modified_source_overlay_and_no_runtime_secrets(self):
        (self.base / 'source.ts').write_text('modified installed source')
        (self.overlay / 'extra.ts').write_text('overlay marker')
        (self.base / 'extra.ts').write_text('installed overlay source')
        (self.base / 'runtime.sqlite').write_text('private database')
        exporter.export(self.base, self.overlay, self.output)
        with tarfile.open(self.output) as archive:
            self.assertEqual(set(archive.getnames()), {'homeio/source.ts', 'homeio/package.json', 'homeio/extra.ts', 'BUILD-SOURCE.md'})
            self.assertEqual(archive.extractfile('homeio/source.ts').read(), b'modified installed source')
            self.assertEqual(archive.extractfile('homeio/extra.ts').read(), b'installed overlay source')
            self.assertNotIn(str(self.base).encode(), archive.extractfile('BUILD-SOURCE.md').read())

    def test_tracked_symlink_cannot_export_secret(self):
        (self.base / 'source.ts').unlink()
        (self.base / 'source.ts').symlink_to(self.base / '.env')
        with self.assertRaises(ValueError):
            exporter.export(self.base, self.overlay, self.output)
        self.assertFalse(self.output.exists())

    def test_missing_overlay_stops_before_replacing_previous_archive(self):
        self.output.write_bytes(b'previous source')
        (self.overlay / 'missing.ts').write_text('not installed')
        with self.assertRaises(ValueError):
            exporter.export(self.base, self.overlay, self.output)
        self.assertEqual(self.output.read_bytes(), b'previous source')

    def test_path_and_secret_filters(self):
        for name in ('../secret', '/etc/shadow'):
            with self.assertRaises(ValueError):
                exporter.safe_name(name)
        for name in ('.env.production', '.git/config', 'config/key.pem', 'public/homeio-corresponding-source.tar.gz'):
            self.assertFalse(exporter.safe_name(name))


if __name__ == '__main__':
    unittest.main()
