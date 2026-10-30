from pathlib import Path
import importlib.util,tempfile,unittest
spec=importlib.util.spec_from_file_location('network_config',Path(__file__).resolve().parents[1]/'network-config.py')
network=importlib.util.module_from_spec(spec);spec.loader.exec_module(network)

class NetworkRegistration(unittest.TestCase):
    def fixture(self,text):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name)
        (root/'usr/bin').mkdir(parents=True);(root/'usr/bin/pvesh').touch()
        path=root/'etc/network/interfaces';path.parent.mkdir(parents=True);path.write_text(text)
        return root,path
    def test_only_pristine_firstboot_stub_is_replaced(self):
        root,path=self.fixture('# generated\nauto lo\niface lo inet loopback\niface eth0 inet manual\n')
        self.assertTrue(network.register(root)['changed']);self.assertEqual(path.read_text(),network.INTERFACES)
        self.assertFalse(network.register(root)['changed'])
    def test_user_network_and_pending_changes_are_not_overwritten(self):
        original='auto lo\niface lo inet loopback\nauto vmbr1\niface vmbr1 inet static\n    address 10.8.0.1/24\n'
        root,path=self.fixture(original);self.assertFalse(network.register(root)['changed']);self.assertEqual(path.read_text(),original)
    def test_nas_host_is_not_a_proxmox_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):network.register(Path(tmp))

if __name__=='__main__':unittest.main()
