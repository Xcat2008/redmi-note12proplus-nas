import hashlib,importlib.util,io,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('download',Path(__file__).resolve().parents[1]/'download.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

class DownloadTests(unittest.TestCase):
 def test_verified_existing_part_is_reused_without_network(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'part001';p.write_bytes(b'correct')
   item={'name':p.name,'bytes':7,'sha256':hashlib.sha256(b'correct').hexdigest()}
   with patch.object(d.urllib.request,'urlopen',side_effect=AssertionError('network not expected')):
    self.assertEqual(d.fetch_part(item,Path(tmp),'https://unused.invalid',lambda _:None),p)
 def test_existing_wrong_file_is_preserved(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'part001';p.write_bytes(b'keep this')
   with self.assertRaises(ValueError):d.fetch_part({'name':p.name,'bytes':1,'sha256':'0'*64},Path(tmp),'https://unused.invalid',lambda _:None)
   self.assertEqual(p.read_bytes(),b'keep this')
 def test_oversized_response_never_promoted(self):
  class Response(io.BytesIO):status=200;headers={}
  with tempfile.TemporaryDirectory() as tmp,patch.object(d.urllib.request,'urlopen',return_value=Response(b'oversized')):
   with self.assertRaises(ValueError):d.fetch_part({'name':'part001','bytes':1,'sha256':'0'*64},Path(tmp),'https://unused.invalid',lambda _:None)
   self.assertFalse((Path(tmp)/'part001').exists())
 def test_archive_escape_rejected(self):
  for name in ['../escape','/absolute','Redmi-NAS/../../escape','other/file','Redmi-NAS/C:/escape','Redmi-NAS/..\\escape']:
   with self.subTest(name=name),tempfile.TemporaryDirectory() as tmp:
    archive=Path(tmp)/'archive.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr(name,b'bad')
    with self.assertRaises(ValueError):d.extract_checked(archive,Path(tmp),'Redmi-NAS')
 def test_correct_archive_extracts(self):
  with tempfile.TemporaryDirectory() as tmp:
   archive=Path(tmp)/'archive.zip'
   with zipfile.ZipFile(archive,'w') as z:z.writestr('Redmi-NAS/README.txt',b'fixture')
   d.extract_checked(archive,Path(tmp),'Redmi-NAS')
   self.assertEqual((Path(tmp)/'Redmi-NAS/README.txt').read_bytes(),b'fixture')
 def test_complete_download_checks_then_launches_only_verified_assistant(self):
  class Response(io.BytesIO):status=200;headers={}
  memory=io.BytesIO()
  with zipfile.ZipFile(memory,'w') as z:z.writestr('Redmi-NAS/RedmiNAS-Setup.exe',b'neutral-test-fixture')
  raw=memory.getvalue();h=hashlib.sha256(raw).hexdigest()
  data={'repository':'Xcat2008/redmi-note12proplus-nas','tag':'v0.2.0-rc3','folder':'Redmi-NAS','parts':[{'name':'fixture.zip.part001','bytes':len(raw),'sha256':h}],'archive':{'name':'fixture.zip','bytes':len(raw),'sha256':h},'unpackedBytes':20,'setupSha256':hashlib.sha256(b'neutral-test-fixture').hexdigest()}
  with tempfile.TemporaryDirectory() as tmp,patch.object(d.urllib.request,'urlopen',return_value=Response(raw)),patch.object(d.subprocess,'Popen') as launch:
   d.install_download(data,Path(tmp),lambda _:None)
   self.assertEqual((Path(tmp)/'Redmi-NAS/RedmiNAS-Setup.exe').read_bytes(),b'neutral-test-fixture')
   self.assertEqual(launch.call_count,1)
   self.assertFalse(list(Path(tmp).glob('.redmi-nas-extract-*')))
 def test_checksum_failure_never_launches_or_creates_installation(self):
  class Response(io.BytesIO):status=200;headers={}
  data={'repository':'Xcat2008/redmi-note12proplus-nas','tag':'v0.2.0-rc3','folder':'Redmi-NAS','parts':[{'name':'fixture.zip.part001','bytes':3,'sha256':'0'*64}],'archive':{'name':'fixture.zip','bytes':3,'sha256':'0'*64},'unpackedBytes':20,'setupSha256':'0'*64}
  with tempfile.TemporaryDirectory() as tmp,patch.object(d.urllib.request,'urlopen',return_value=Response(b'bad')),patch.object(d.subprocess,'Popen') as launch:
   with self.assertRaises(ValueError):d.install_download(data,Path(tmp),lambda _:None)
   launch.assert_not_called();self.assertFalse((Path(tmp)/'Redmi-NAS').exists())

if __name__=='__main__':unittest.main()
