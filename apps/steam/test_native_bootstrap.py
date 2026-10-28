from pathlib import Path
import contextlib,hashlib,importlib.util,io,json,stat,struct,tempfile,unittest,zipfile
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('bootstrap',Path(__file__).with_name('bootstrap-native-steam.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class BootstrapTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.old=(module.BASE,module.CLIENT,module.PACKAGE_MANIFEST)
  module.BASE=self.root/'data';module.CLIENT=module.BASE/'native-arm64/home/.local/share/Steam';module.PACKAGE_MANIFEST=self.root/'packages.json'
 def tearDown(self):
  module.BASE,module.CLIENT,module.PACKAGE_MANIFEST=self.old;self.temp.cleanup()
 def archive(self,entries):
  target=self.root/'program.zip'
  with zipfile.ZipFile(target,'w') as archive:
   for name,data in entries.items():archive.writestr(name,data)
  return target
 def test_safe_program_archive(self):
  destination=self.root/'extract';destination.mkdir()
  archive=self.archive({'program.sh':b'#!/bin/sh\nexit 0\n'})
  module.extract(archive,destination)
  self.assertTrue((destination/'program.sh').stat().st_mode&stat.S_IXUSR)
 def test_parent_escape_rejected(self):
  destination=self.root/'extract';destination.mkdir()
  with self.assertRaises(RuntimeError):module.extract(self.archive({'../outside':b'bad'}),destination)
  self.assertFalse((self.root/'outside').exists())
 def test_link_escape_rejected(self):
  archive=self.root/'symlink.zip'
  with zipfile.ZipFile(archive,'w') as package:
   info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
   package.writestr(info,'../../outside')
  destination=self.root/'extract';destination.mkdir()
  with self.assertRaises(RuntimeError):module.extract(archive,destination)
 def program(self):
  header=b'\x7fELF'+b'\0'*14+struct.pack('<H',183)
  archive=self.archive({'steamrtarm64/steam':header,'steamrtarm64/steamwebhelper':header})
  data=archive.read_bytes();metadata=[{'file':'test.zip.validated','size':len(data),'sha256':hashlib.sha256(data).hexdigest()}]
  module.PACKAGE_MANIFEST.write_text(json.dumps(metadata));return data
 def test_fresh_setup_and_repeat_preserve_config(self):
  data=self.program()
  with patch.object(module.os,'geteuid',return_value=32011),patch.object(module.urllib.request,'urlopen',side_effect=lambda *a,**k:io.BytesIO(data)),contextlib.redirect_stdout(io.StringIO()):module.main()
  private=module.CLIENT/'config';private.mkdir();(private/'keep').write_bytes(b'user-state-fixture')
  with patch.object(module.os,'geteuid',return_value=32011),contextlib.redirect_stdout(io.StringIO()):module.main()
  self.assertEqual((private/'keep').read_bytes(),b'user-state-fixture')
  self.assertTrue((module.BASE/'native-arm64/home/.steam/root').is_symlink())
 def test_checksum_failure_does_not_install(self):
  self.program()
  with patch.object(module.os,'geteuid',return_value=32011),patch.object(module.urllib.request,'urlopen',side_effect=lambda *a,**k:io.BytesIO(b'invalid')):
   with self.assertRaises(RuntimeError):module.main()
  self.assertFalse(module.CLIENT.exists())
 def test_root_extraction_not_allowed(self):
  with patch.object(module.os,'geteuid',return_value=0):
   with self.assertRaises(RuntimeError):module.main()

if __name__=='__main__':unittest.main()
