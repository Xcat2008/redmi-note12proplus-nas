# Start here / Começar aqui

## What is automatic today?

| Stage | Current experience |
| --- | --- |
| Xiaomi account and bootloader unlock | Manual, with Xiaomi's official tools |
| Replace Android with the native Droidian port | Manual developer/porter procedure; no public flashable image yet |
| Install the NAS stack once native Droidian boots | `scripts/install-nas.sh`, an automated entry point with a read-only preflight mode |
| Create the Homeio administrator | First-run web page, your own credentials |
| Add applications | Homeio app store; app-specific hardware compatibility must still be checked |

**For a non-technical user starting from stock Android, this release is not yet a simple consumer installation.** The original working phone demonstrates feasibility; it does not remove the unfinished Linux image/installer work. Do not run the NAS installer on Android/Termux or a different Redmi.

## Already have this native Droidian port running?

Run these commands **on the phone's native Linux system**, through a local terminal or SSH:

```sh
git clone https://github.com/Xcat2008/redmi-note12proplus-nas.git
cd redmi-note12proplus-nas
sudo bash scripts/install-nas.sh --check YOUR_LINUX_USER
```

Review the check and source. On a fresh compatible system, start the NAS installation:

```sh
sudo bash scripts/install-nas.sh --install YOUR_LINUX_USER
```

Replace `YOUR_LINUX_USER` with the Phosh desktop user you created. It requires the documented kernel, prepared `/userdata` and `/DATA` layout, Debian 13 base, internet access and an active Phosh user session. It refuses an existing Homeio installation rather than overwriting accounts. It does not unlock, flash or format the phone.

The script installs prerequisites and the pinned Docker packages, applies the NAS display/power policy, builds pinned Homeio with both local patches, and enables its services. This new combined wrapper has preflight/syntax checks; a fresh end-to-end installation on a second phone is still pending. The original component steps and patched application builds were tested separately.

After completion, open `http://redmi-nas.local` from another computer on the same network. Create your Homeio account there. Read [validation](VALIDATION.md) before adding important data.

## Ainda estás no Android?

O comando acima **não instala Linux sobre Android**. Primeiro é necessário desbloquear pelo processo oficial Xiaomi e preparar o port Droidian descrito no [guia técnico](INSTALLATION.md). Essa parte ainda é para quem sabe trabalhar com boot images, Halium e recuperação de telemóveis.

O passo necessário para uma experiência simples é produzir uma imagem Linux limpa e reproduzível, sem dados do autor, e testá-la de raiz num segundo aparelho. Essa imagem ainda não está publicada. O repositório apresenta esta limitação de forma explícita.
