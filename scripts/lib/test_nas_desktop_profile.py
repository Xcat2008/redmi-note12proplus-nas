# SPDX-License-Identifier: AGPL-3.0-only
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('desktop_profile', Path(__file__).with_name('nas-desktop-profile.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class DesktopProfileTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.home = root / 'home'
        self.home.mkdir()
        self.state = root / 'backup/state.json'

    def run_profile(self, **kwargs):
        return m.configure(self.home, os.getuid(), os.getgid(), self.state, **kwargs)

    def test_check_only_writes_nothing(self):
        self.run_profile()
        self.assertFalse((self.home / '.config').exists())
        self.assertFalse(self.state.exists())

    def test_apply_idempotent_and_restore_original_user_choice(self):
        folder = self.home / '.config/autostart'
        folder.mkdir(parents=True)
        original = b'[Desktop Entry]\nHidden=false\n'
        (folder / 'org.gnome.Software.desktop').write_bytes(original)
        self.assertTrue(self.run_profile(apply=True)['applied'])
        state = self.state.read_bytes()
        self.assertTrue(self.run_profile(apply=True)['alreadyConfigured'])
        self.assertEqual(state, self.state.read_bytes())
        self.run_profile(apply=True, restore=True)
        self.assertEqual((folder / 'org.gnome.Software.desktop').read_bytes(), original)
        self.assertFalse((self.home / '.config/gnome-initial-setup-done').exists())
        self.assertFalse(self.state.exists())

    def test_existing_finished_setup_marker_is_preserved(self):
        config = self.home / '.config'
        config.mkdir()
        marker = config / 'gnome-initial-setup-done'
        marker.write_bytes(b'existing-version\n')
        self.run_profile(apply=True)
        self.assertEqual(marker.read_bytes(), b'existing-version\n')

    def test_symlink_refused_before_writes(self):
        outside = self.home.parent / 'outside'
        outside.mkdir()
        (self.home / '.config').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_profile(apply=True)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse(self.state.exists())

    def test_changed_managed_file_is_never_overwritten_by_restore(self):
        self.run_profile(apply=True)
        marker = self.home / '.config/gnome-initial-setup-done'
        marker.write_bytes(b'new personal choice')
        with self.assertRaises(ValueError):
            self.run_profile(apply=True, restore=True)
        self.assertEqual(marker.read_bytes(), b'new personal choice')
        self.assertTrue(self.state.exists())


if __name__ == '__main__':
    unittest.main()
