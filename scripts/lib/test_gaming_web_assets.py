from pathlib import Path
import importlib.util,tempfile,unittest
spec=importlib.util.spec_from_file_location('gaming_web_assets',Path(__file__).with_name('gaming-web-assets.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
PUBLIC=Path(__file__).resolve().parents[2]/'homeio/new-files/public'

class BrowserAssets(unittest.TestCase):
    def fixture(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name)
        config=root/'etc/nginx/redmi-retroarch/homeio-locations.conf';config.parent.mkdir(parents=True)
        config.write_text('location = /retroarch-icon.svg { alias /owned/icon.svg; }\n')
        return root,config
    def test_installs_real_launcher_document_and_all_shortcut_routes(self):
        root,config=self.fixture();module.install(root,PUBLIC)
        self.assertIn('/gaming-launcher.js',(root/'usr/local/share/redmi-nas/gaming-launcher.html').read_text())
        self.assertIn('location = /sunshine/',config.read_text())
        first=config.read_bytes();module.install(root,PUBLIC);self.assertEqual(config.read_bytes(),first)
    def test_missing_html_cannot_silently_produce_a_broken_install(self):
        root,config=self.fixture();before=config.read_bytes()
        with self.assertRaises(FileNotFoundError):module.install(root,root/'absent-assets')
        self.assertEqual(config.read_bytes(),before)
    def test_unknown_existing_shortcut_route_is_preserved(self):
        root,config=self.fixture();config.write_text('location = /sunshine/ { return 302 /custom; }\n');before=config.read_bytes()
        with self.assertRaises(ValueError):module.install(root,PUBLIC)
        self.assertEqual(config.read_bytes(),before)

if __name__=='__main__':unittest.main()
