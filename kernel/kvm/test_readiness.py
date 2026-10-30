import errno,importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('readiness',Path(__file__).with_name('check_readiness.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ReadinessTests(unittest.TestCase):
 def test_exact_kernel_and_real_api_required(self):
  self.assertTrue(m.classify('aarch64','4.19.191-g914ba8403bb3-dirty',12)['ready'])
  self.assertFalse(m.classify('aarch64','4.19.191-g914ba8403bb3-dirty',11)['ready'])
  self.assertFalse(m.classify('x86_64','4.19.191-g914ba8403bb3-dirty',12)['ready'])
 def test_permission_failure_not_misreported_as_missing_el2(self):
  for error in [errno.EACCES,errno.EPERM]:
   self.assertEqual(m.classify('aarch64','4.19.191-g914ba8403bb3',None,error)['stage'],'permissions-required')
 def test_missing_device_does_not_claim_definite_el1(self):
  self.assertEqual(m.classify('aarch64','4.19.191-g914ba8403bb3',None,errno.ENOENT)['stage'],'platform-or-kernel-not-ready')
 def test_diagnostic_opens_device_read_only_and_never_starts_vm(self):
  import fcntl
  with patch.object(m.platform,'machine',return_value='aarch64'),patch.object(m.platform,'release',return_value='4.19.191-g914ba8403bb3'),patch.object(m.os,'open',return_value=42) as opened,patch.object(m.os,'close') as closed,patch.object(fcntl,'ioctl',return_value=12) as ioctl:
   result=m.inspect_kvm()
   self.assertEqual(opened.call_args.args[1],m.os.O_RDONLY|m.os.O_CLOEXEC)
   ioctl.assert_called_once_with(42,0xae00,0);closed.assert_called_once_with(42)
   self.assertTrue(result['ready']);self.assertFalse(result['guestStarted']);self.assertFalse(result['bootMetadataWritten'])

if __name__=='__main__':unittest.main()
