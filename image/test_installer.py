# SPDX-License-Identifier: AGPL-3.0-only
import base64
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import installer
import personalize_usb


class ImageChecks(unittest.TestCase):
    def fixture(self,chunk,blocks=1):
        header=struct.pack('<IHHHHIIII',0xED26FF3A,1,0,28,12,4096,blocks,1,0)
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        path=Path(folder.name)/'tiny.img';path.write_bytes(header+chunk)
        return path

    def test_valid_sparse_hole(self):
        path=self.fixture(struct.pack('<HHII',0xCAC3,0,1,12))
        installer.validate_sparse(path,4096)

    def test_truncated_raw_chunk_is_rejected(self):
        path=self.fixture(struct.pack('<HHII',0xCAC1,0,1,4108)+b'short')
        with self.assertRaisesRegex(ValueError,'exceeds'):installer.validate_sparse(path,4096)

    def test_unknown_chunk_is_rejected(self):
        path=self.fixture(struct.pack('<HHII',0xAAAA,0,1,12))
        with self.assertRaisesRegex(ValueError,'chunk length'):installer.validate_sparse(path,4096)

    def test_capacity_mismatch_is_rejected(self):
        path=self.fixture(struct.pack('<HHII',0xCAC3,0,1,12))
        with self.assertRaisesRegex(ValueError,'capacity'):installer.validate_sparse(path,8192)

    def test_unvalidated_candidate_does_not_contact_phone(self):
        with patch.object(installer.sys,'argv',['installer','--install']),patch.object(installer,'inspect_package',return_value={'physical_install_test_passed':False}),patch.object(installer,'locate_fastboot') as locate:
            with self.assertRaisesRegex(ValueError,'not passed'):installer.main()
            locate.assert_not_called()

    def test_default_operation_only_checks_package(self):
        with patch.object(installer.sys,'argv',['installer']),patch.object(installer,'inspect_package',return_value={}) as inspect,patch.object(installer,'device_preflight') as device:
            installer.main();inspect.assert_called_once();device.assert_not_called()


class SetupFields(unittest.TestCase):
    def fields(self):
        kind=b'ssh-ed25519';raw=struct.pack('>I',len(kind))+kind+struct.pack('>I',32)+bytes(range(32))
        return {'pin':'123456','ssh_public_key':'ssh-ed25519 '+base64.b64encode(raw).decode()+' fresh-device'}

    def test_valid_setup_drops_key_comment(self):
        self.assertEqual(len(personalize_usb.validate(self.fields())['ssh_public_key'].split()),2)

    def test_bad_pin_rejected(self):
        fields=self.fields();fields['pin']='12\nroot:bad'
        with self.assertRaisesRegex(ValueError,'PIN'):personalize_usb.validate(fields)

    def test_authorized_keys_options_rejected(self):
        fields=self.fields();fields['ssh_public_key']='command="id" '+fields['ssh_public_key']
        with self.assertRaisesRegex(ValueError,'Ed25519'):personalize_usb.validate(fields)

    def test_malformed_public_key_rejected(self):
        fields=self.fields();fields['ssh_public_key']='ssh-ed25519 '+base64.b64encode(b'too short').decode()
        with self.assertRaisesRegex(ValueError,'Malformed'):personalize_usb.validate(fields)

    def test_wifi_control_characters_rejected(self):
        fields=self.fields();fields['wifi']={'ssid':'Home\nother','password':'example-password'}
        with self.assertRaisesRegex(ValueError,'SSID'):personalize_usb.validate(fields)


if __name__=='__main__':unittest.main()
