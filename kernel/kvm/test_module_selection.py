import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from select_matching_modules import select


class FreshModuleSelection(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        bundle=root/'usr/local/lib/redmi-nas/kvm-kernel';(bundle/'modules').mkdir(parents=True)
        entries=[]
        for name,target in [('radio.ko','/usr/lib/droid-vendor-overlay/lib/modules/radio.ko'),('binfmt_misc.ko','/usr/local/lib/redmi-nas/steam/binfmt_misc.ko')]:
            data=('matching-'+name).encode();(bundle/'modules'/name).write_bytes(data)
            entries.append({'module':name,'target':target,'sha256':hashlib.sha256(data).hexdigest()})
        target=root/entries[0]['target'].lstrip('/');target.parent.mkdir(parents=True);target.write_bytes(b'baseline')
        (bundle/'manifest.json').write_text(json.dumps({'kernelRelease':'tested-kernel','vendorBindings':entries}))
        return root,entries

    def test_fresh_phone_without_steam_or_lxc_aliases_can_prepare_android(self):
        root,entries=self.fixture();mount=Mock(side_effect=shutil.copyfile)
        result=select(root,'tested-kernel',mount)
        self.assertEqual(mount.call_count,1)
        self.assertIn(entries[1]['target'].lstrip('/'),result['deferredTargets'])
        self.assertEqual(result['selection'],'kvm-version-matched-modules')

    def test_mismatched_source_does_not_bind_anything(self):
        root,_=self.fixture();(root/'usr/local/lib/redmi-nas/kvm-kernel/modules/radio.ko').write_bytes(b'corrupt')
        mount=Mock()
        with self.assertRaisesRegex(ValueError,'mismatched'):select(root,'tested-kernel',mount)
        mount.assert_not_called()

    def test_baseline_kernel_preserves_originals(self):
        root,_=self.fixture();mount=Mock();result=select(root,'baseline-kernel',mount)
        mount.assert_not_called();self.assertEqual(result['selection'],'original-module-files-retained')


if __name__=='__main__':unittest.main()
