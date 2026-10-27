# Bluetooth controllers

Open **Settings → Bluetooth** in the Homeio web desktop. These controls operate the phone's Bluetooth radio, so its screen can remain off.

1. Turn Bluetooth on.
2. Put the controller in pairing mode.
3. Choose **Search for controllers**. The search stops automatically after 45 seconds.
4. Select the controller and choose **Pair controller**. A successful bond is saved by BlueZ; **Connect**, **Disconnect** and **Forget** are available afterward.

For a Bluetooth-capable Xbox controller, hold its pairing button until the light flashes quickly. For DualShock 4, hold Share + PS; for DualSense, hold Create + PS until the light flashes. Older Xbox controllers without Bluetooth need a different connection method.

The panel supports controllers that pair without typing a PIN. It does not provide a general keyboard/PIN-entry wizard. A controller already connected to another console or computer may need to be disconnected there before it can pair with the NAS.

**TV streaming is a different connection path:** pair the controller with the TV or Android box running Moonlight. Moonlight sends its input to Sunshine. Pair directly with the NAS when the controller is within Bluetooth range of the phone and that is the desired input path.

## Validation boundary

The radio's registration, power and discovery were exercised on the project phone. Browser checks verified authenticated access, rejection of unauthenticated/cross-origin requests, power switching, discovery across section changes, explicit stop and the automatic 45-second stop. Automated service tests cover the pairing-agent restrictions, time limits and device lifecycle. A Bluetooth Xbox controller was subsequently paired on the project device and its menu/in-game input was confirmed after profile fixes. PlayStation controllers and every controller/firmware combination are not certified by that result. The latest source/runtime integration status is recorded in [performance notes](PERFORMANCE.md).

BlueZ keeps bonds on the running NAS. Personal pairing keys, device lists, game libraries, playlists and save files are not included in the project source or clean image. Published captures must not show personal game libraries or their titles.

References: [BlueZ device API](https://github.com/bluez/bluez/blob/master/doc/org.bluez.Device.rst), [BlueZ pairing agent API](https://github.com/bluez/bluez/blob/master/doc/org.bluez.AgentManager.rst), [Sony controller pairing](https://www.playstation.com/en-ca/support/hardware/accessories/).
