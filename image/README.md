# Installer source

Read [image scope](../docs/IMAGE-INSTALLER.md) and the [Windows guide](../docs/INSTALL-WIZARD.pt-PT.md) before use. Running the CLI without arguments only checks the supplied package; it does not access a phone.

`download.py` retrieves fixed release parts from an embedded manifest, verifies SHA-256, joins and safely extracts the ZIP, then opens the assistant. The release provides its source and embedded manifest alongside the frozen Windows executable. It does not install drivers or change execution policies.

`wizard.py` verifies the package first, creates individual credentials, checks the device before writing and offers a USB-setup-only retry. Unvalidated boot/layout changes remain blocked. Experimental rc3 eligibility is narrowly tied to the physically tested rc2 boot/layout, live userspace checks and completed source/distribution inventory; the manifest does not claim a new physical rc3 reinstall.

```sh
python -m pip install -r image/requirements.txt
python image/installer.py --folder PATH_TO_EXTRACTED_PACKAGE
```

`personalize_usb.py` is a one-time physical USB first-boot service. It accepts a newly chosen PIN, fresh SSH public key and optional Wi-Fi details. It is not a root shell or network service. The first NAS setup downloads upstream programs, so this is not an entirely offline distribution.

Original integration code: José Miranda (Xcat2008). AGPL-3.0-only.
