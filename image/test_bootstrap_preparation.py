from pathlib import Path
import tempfile,unittest
from prepare_bootstrap import prepare


class BootstrapPreparation(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)/'root';repo=Path(temp.name)/'repo'
        for name,text in {'etc/debian_version':'13.7','etc/hosts':'127.0.0.1 localhost\n','etc/systemd/system/lxc@android.service':'[Service]\nExecStartPre=/usr/bin/lxc-start -d -n android\n','usr/bin/curl':'curl','usr/sbin/resize2fs':'resize'}.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        p=repo/'kernel/kvm/select_matching_modules.py';p.parent.mkdir(parents=True);p.write_text('# selector\n')
        return root,repo

    def test_missing_early_boot_tool_stops_before_service_changes(self):
        root,repo=self.fixture();(root/'usr/bin/curl').unlink()
        with self.assertRaisesRegex(ValueError,'Preinstall'):prepare(root,repo)
        self.assertFalse((root/'etc/systemd/system/lxc@android.service.d').exists())

    def test_personalized_system_is_rejected(self):
        root,repo=self.fixture();p=root/'var/lib/redmi-nas/personalized';p.parent.mkdir(parents=True);p.touch()
        with self.assertRaisesRegex(ValueError,'personalized'):prepare(root,repo)

    def test_clean_template_selects_modules_before_container_start(self):
        root,repo=self.fixture();result=prepare(root,repo)
        lines=(root/'etc/systemd/system/lxc@android.service.d/kvm-module-selection.conf').read_text().splitlines()
        commands=[line for line in lines if line.startswith('ExecStartPre=')]
        self.assertEqual(commands[0],'ExecStartPre=')
        self.assertIn('select-matching-modules.py',commands[1])
        self.assertEqual(commands[2],'ExecStartPre=/usr/bin/lxc-start -d -n android')
        self.assertTrue(result['bootstrapDependenciesPresent'])


if __name__=='__main__':unittest.main()
