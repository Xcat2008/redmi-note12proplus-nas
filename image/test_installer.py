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


class ReleaseBoundary(unittest.TestCase):
    def test_binary_review_required_even_after_physical_install(self):
        with self.assertRaisesRegex(ValueError,'redistribution'):
            installer.require_release({'physical_install_test_passed':True,'binary_redistribution_audit_passed':False})

    def test_both_release_checks_pass(self):
        installer.require_release({'physical_install_test_passed':True,'binary_redistribution_audit_passed':True})

    def test_bad_personal_fields_do_not_generate_key(self):
        with patch.object(installer.subprocess,'run') as run:
            for args in [('12\nroot:bad','',''),('1234','Home\nOther','example-password'),('1234','Home','short')]:
                with self.subTest(args=args),self.assertRaises(ValueError):installer.make_setup_fields(*args)
            run.assert_not_called()


class BootMetadataBoundary(unittest.TestCase):
    def test_expected_product_matches_the_verified_recovery_path(self):
        properties={'product':'rubypro','current-slot':'a','unlocked':'yes','partition-size:boot_a':'8000000','partition-size:userdata':hex(242019696640),'partition-size:vbmeta_a':'800000'}
        with patch.object(installer.subprocess,'run',return_value=type('Result',(),{'stdout':'test-serial fastboot\n'})()),patch.object(installer,'getvar',side_effect=lambda exe,serial,name:properties[name]):
            self.assertEqual(installer.device_preflight('fastboot',{'userdata_partition_bytes':242019696640,'requires_linux_vbmeta':False}),'test-serial')
            properties['product']='ruby'
            with self.assertRaisesRegex(ValueError,'rubypro'):installer.device_preflight('fastboot',{})

    def test_retired_empty_vbmeta_candidate_rejected_before_device_access(self):
        with patch.object(installer.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'failed physical boot'):
                installer.device_preflight('fastboot',{'requires_linux_vbmeta':True})
            run.assert_not_called()

    def test_retired_metadata_profile_cannot_erase_userdata(self):
        with patch.object(installer,'command') as command:
            with self.assertRaisesRegex(ValueError,'factory AVB'):installer.flash_images('fastboot','test',Path('/test'),{'requires_linux_vbmeta':True})
            command.assert_not_called()

    def test_corrected_flash_preserves_factory_metadata(self):
        with patch.object(installer,'command') as command:
            installer.flash_images('fastboot','test',Path('/test'),{'requires_linux_vbmeta':False})
            self.assertEqual(command.call_count,2)
            operations=[call.args[2:] for call in command.call_args_list]
            self.assertEqual(operations,[('-S','128M','flash','userdata',str(Path('/test/userdata.img'))),('flash','boot_a',str(Path('/test/boot.img')))])


if __name__=='__main__':unittest.main()
