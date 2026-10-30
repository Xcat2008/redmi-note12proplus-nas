# SPDX-License-Identifier: AGPL-3.0-only
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('proxmox_control',Path(__file__).resolve().parents[1]/'control.py')
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)


class SetupBoundary(unittest.TestCase):
    def test_password_constraints(self):
        for value in ['1234567','password\n',None,'x'*129]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):control.validate_password(value)

    @unittest.skipUnless(os.geteuid()==0,'runtime paths require root ownership')
    def test_missing_kvm_never_queues_setup_or_stores_password(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime=Path(folder)/'run'
            with patch.object(control,'RUNTIME',runtime),patch.object(control,'status',return_value={'configured':False,'busy':False,'ready':False,'errors':['KVM unavailable']}),patch.object(control.subprocess,'run') as run:
                with self.assertRaisesRegex(ValueError,'KVM unavailable'):control.queue_setup('private-test-pass')
                run.assert_not_called();self.assertFalse(list(runtime.glob('secret-*')))

    @unittest.skipUnless(os.geteuid()==0,'runtime paths require root ownership')
    def test_existing_account_is_not_reconfigured(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(control,'RUNTIME',Path(folder)/'run'),patch.object(control,'status',return_value={'configured':True}),patch.object(control.subprocess,'run') as run:
                with self.assertRaisesRegex(ValueError,'preserved'):control.queue_setup('private-test-pass')
                run.assert_not_called()

    @unittest.skipUnless(os.geteuid()==0,'runtime paths require root ownership')
    def test_password_uses_private_stdin_file_and_is_removed_by_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime=Path(folder)/'run';password='private-test-pass';seen=[]
            def fake_run(args,**kwargs):
                self.assertNotIn(password,' '.join(args))
                secret=Path(args[-1]);self.assertEqual(secret.read_text(),password)
                self.assertEqual(secret.stat().st_mode&0o777,0o600);seen.append(secret)
                return subprocess.CompletedProcess(args,0)
            current={'configured':False,'busy':False,'ready':True,'errors':[]}
            with patch.object(control,'RUNTIME',runtime),patch.object(control,'status',return_value=current),patch.object(control.subprocess,'run',side_effect=fake_run):control.queue_setup(password)
            received=[]
            with patch.object(control,'RUNTIME',runtime),patch.object(control.runpy,'run_path',return_value={'enable':received.append}):control.worker(str(seen[0]))
            self.assertEqual(received,[password]);self.assertFalse(seen[0].exists())
            self.assertNotIn(password,(runtime/'job.json').read_text())
            self.assertEqual(json.loads((runtime/'job.json').read_text())['state'],'succeeded')


if __name__=='__main__':unittest.main()
