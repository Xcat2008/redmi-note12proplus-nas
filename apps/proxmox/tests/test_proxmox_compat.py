# SPDX-License-Identifier: AGPL-3.0-only
import importlib.util
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


firmware=module('pve_firmware',ROOT/'runtime/firmware_compat.py')
preflight=module('pve_preflight',ROOT/'preflight.py')


def fixture(offset=16,destination=64):
    data=bytearray(192)
    branch=0x54000000 | (((destination-(offset+16))//4)<<5)
    struct.pack_into('<5I',data,offset,0xd5384240,0x36180100,0xd5380720,0xf2780c1f,branch)
    struct.pack_into('<I',data,destination,0x17ffffbb)
    return bytes(data)


class FirmwareSafety(unittest.TestCase):
    def test_only_entry_instruction_changes(self):
        original=fixture();patched,receipt=firmware.patch_early_map(original)
        self.assertEqual(patched[:16],original[:16])
        self.assertEqual(patched[20:],original[20:])
        self.assertEqual(struct.unpack_from('<I',patched,16)[0],0x1400000c)
        self.assertEqual(receipt['destination'],64)

    def test_unknown_or_ambiguous_layout_rejected(self):
        for data in [bytes(192),fixture()+fixture(),fixture()[:64]]:
            with self.subTest(length=len(data)):
                with self.assertRaises(ValueError):firmware.patch_early_map(data)

    def test_unreviewed_vendor_build_rejected(self):
        with self.assertRaisesRegex(ValueError,'digest'):
            firmware.transform_vendor(fixture(),'4.19.191-test')

    def test_new_kernel_keeps_original_firmware(self):
        data=fixture();result,receipt=firmware.transform_vendor(data,'6.12.0')
        self.assertEqual(result,data);self.assertFalse(receipt['workaround_active'])


class ProfileBoundary(unittest.TestCase):
    def baseline(self):
        return ['aarch64','4.19.191-g914ba8403bb3-dirty','systemd-nspawn','13',[0xd05]*6+[0xd41]*2,12,'9.2.20']

    def test_existing_profile_accepted(self):
        self.assertEqual(preflight.inventory_errors(*self.baseline()),[])

    def test_host_wrong_kernel_or_missing_kvm_rejected(self):
        for index,value in [(0,'x86_64'),(1,'4.19.191-g914ba8403bb3'),(2,'none'),(3,'12'),(4,[0xd41]*8),(5,-1),(6,'99.0.0')]:
            args=self.baseline();args[index]=value
            with self.subTest(field=index):self.assertTrue(preflight.inventory_errors(*args))

    @unittest.skipUnless(platform.machine() in ('x86_64','AMD64'),'x86 refusal test')
    def test_apply_rejected_before_installing_on_host(self):
        result=subprocess.run(['bash',str(ROOT/'apply-existing.sh'),'--apply'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('"configuration_written": false',result.stdout)


@unittest.skipUnless(shutil.which('gcc') and platform.system()=='Linux','requires Linux compiler')
class LegacyCacheRegression(unittest.TestCase):
    def test_cross_cluster_restore_and_error_propagation(self):
        with tempfile.TemporaryDirectory() as folder:
            stage=Path(folder);backend=stage/'liblegacykvm.so';shim=stage/'libcompat.so';binary=stage/'test'
            for args in [
                ['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-o',str(backend),str(ROOT/'tests/legacy-kvm-backend.c')],
                ['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-pthread','-o',str(shim),str(ROOT/'runtime/redmi-kvm-cache-affinity.c'),'-ldl'],
                ['gcc','-Wall','-Wextra','-Werror','-o',str(binary),str(ROOT/'tests/cache-affinity-test.c'),'-L'+folder,'-llegacykvm','-Wl,-rpath,$ORIGIN'],
            ]:subprocess.run(args,capture_output=True,text=True,check=True)
            baseline=subprocess.run([str(binary),'baseline'],capture_output=True,text=True)
            self.assertEqual(baseline.returncode,0,baseline.stderr)
            self.assertIn('failure reproduced',baseline.stdout)
            result=subprocess.run([str(binary),'adapted'],env=dict(os.environ,LD_PRELOAD=str(shim)),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('affinity/errors preserved',result.stdout)


if __name__=='__main__':unittest.main()
