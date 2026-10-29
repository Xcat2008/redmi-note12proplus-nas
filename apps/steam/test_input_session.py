"""Host input sockets must survive display namespace entry and privilege drop."""
import importlib.machinery,importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch,MagicMock

loader=importlib.machinery.SourceFileLoader('steam_input_session',str(Path(__file__).with_name('enter-session')))
spec=importlib.util.spec_from_loader(loader.name,loader)
module=importlib.util.module_from_spec(spec);loader.exec_module(module)

class SessionTests(unittest.TestCase):
 def test_descriptor_pool_is_inherited(self):
  with patch.object(module.socket,'socket') as constructor:
   monitors=module.host_monitors(2)
   self.assertEqual(len(monitors),2)
   for monitor in monitors:monitor.set_inheritable.assert_called_with(True)
 def test_partial_socket_failure_closes_previous_descriptors(self):
  first=MagicMock()
  with patch.object(module.socket,'socket',side_effect=[first,OSError('unavailable')]):
   with self.assertRaises(OSError):module.host_monitors(2)
  first.close.assert_called_once()
 def test_preload_is_applied_after_privilege_drop(self):
  args=module.session_arguments('/var/lib/docker/resolv.conf',42,[3,4])
  script=args[4]
  self.assertIn('runuser -u nas -- env',script)
  self.assertIn('"LD_PRELOAD=$3"',script)
  self.assertEqual(args[-1],'3,4')
  self.assertNotIn('export LD_PRELOAD',script)
 def test_invalid_namespace_or_descriptor_is_rejected(self):
  for pid,fds in [('bad',[3]),(0,[3]),(42,[]),(42,[0]),(42,['3'])]:
   with self.assertRaises(ValueError):module.session_arguments('/resolver',pid,fds)
 def test_shell_metacharacters_are_arguments(self):
  resolver='/resolver/with spaces;literal'
  args=module.session_arguments(resolver,42,[3])
  self.assertIn(resolver,args)
  self.assertNotIn(resolver,args[4])

if __name__=='__main__':unittest.main()
