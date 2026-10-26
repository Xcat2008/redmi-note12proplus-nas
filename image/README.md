# Installer source

Read [image status](../docs/IMAGE-INSTALLER.md) before use. Normal installation is disabled for an unvalidated candidate. Running the client without arguments only checks the supplied package; it does not access a device.

```sh
python -m pip install -r image/requirements.txt
python image/installer.py --folder PATH_TO_EXTRACTED_PACKAGE
```

`personalize_usb.py` runs on the phone as a one-time first-boot service. It accepts a newly chosen PIN, a fresh public SSH key and optional Wi-Fi details over a physical USB serial connection. It is not a root shell or a network service.

Original integration code: José Miranda (Xcat2008). AGPL-3.0-only.
