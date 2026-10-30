import importlib.util,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('cpu_online',Path(__file__).with_name('nas-cpu-online.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class CpuAvailabilityTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  for name,field in [('thermal_limit','PPM thermal activate'),('dlpt_limit','PPM DLPT activate')]:
   p=self.root/'proc/ppm/policy'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(field+' = 0\n')
  for cpu in (6,7):
   p=self.root/f'sys/devices/system/cpu/cpu{cpu}/online';p.parent.mkdir(parents=True);p.write_text('0\n')
 def run_profile(self,profile='balanced',kernel='4.19.191-g914ba8403bb3-dirty'):
  return module.restore(self.root,kernel,profile)
 def test_balanced_restores_only_big_cpu_availability(self):
  self.assertEqual(self.run_profile()['activated'],[6,7]);self.assertEqual(self.run_profile()['activated'],[])
 def test_thermal_limit_remains_authoritative(self):
  p=self.root/'proc/ppm/policy/thermal_limit';p.write_text('PPM thermal activate = 1\n')
  self.assertEqual(self.run_profile()['activated'],[]);self.assertEqual(p.read_text(),'PPM thermal activate = 1\n')
 def test_battery_power_limit_remains_authoritative(self):
  (self.root/'proc/ppm/policy/dlpt_limit').write_text('PPM DLPT activate = 1\n')
  self.assertEqual(self.run_profile()['activated'],[])
 def test_power_saver_unknown_kernel_or_missing_safety_state_is_not_overridden(self):
  self.assertEqual(self.run_profile('power-saver')['activated'],[])
  self.assertEqual(self.run_profile(kernel='unknown')['activated'],[])
  (self.root/'proc/ppm/policy/thermal_limit').unlink();self.assertEqual(self.run_profile()['activated'],[])

if __name__=='__main__':unittest.main()
