# Install, update or uninstall

[Overview](../README.md) · [Features](FEATURES.md) · [Controls](CONTROLS.md)

## Install

Requires **Windows / Steam build 25190541**. The installer checks the exact game file.

1. Back up your saves and `%LOCALAPPDATA%\TalesOfEternia-WatersEdition.ini`.
2. Close the game and [download the Easy-Install ZIP](https://github.com/Water130/tales-of-eternia-waters-edition/releases/tag/v0.14.30R).
3. Extract the whole ZIP. Keep **Install.cmd**, **Uninstall.cmd** and **Support** together.
4. Run **Install.cmd**, check the detected game folder, type **Y**, then press Enter.
5. Wait for **Installed and verified**, then launch through Steam.

Choose the **Easy-Install.zip** asset, not GitHub's **Source code** downloads.
No Python, mod loader or extra download is needed. Keep at least **5 GiB free**.

## Update or remove

- **Update:** uninstall the older release using its own **Uninstall.cmd**, then install the new one.
- **Remove:** close the game, run **Uninstall.cmd**, confirm the folder with **Y**.

The installer backs up the original DLL and French HP/TP font bundle beside
each patched file. Keep both backups for removal. Saves are not directly edited by the installer;
mod preferences are retained when uninstalling.

## If the installer cannot continue

| Message or situation | What to do |
| --- | --- |
| Game folder requested | In Steam, choose **Manage → Browse local files**, then paste that folder's path. |
| Game still running | Close Tales of Eternia completely and try again. |
| Unsupported or modified DLL | Restore the supported original game file. Do not force a patch onto another build or DLL mod. |
| Uninstall fails | Close the game and try [Steam's file verification](https://help.steampowered.com/en/faqs/view/0C48-FCBD-DA71-93EB). |

Verifying or reinstalling game files cannot recover damaged saves or lost progress.

## Settings and backups

Open **Mod settings** on the title screen. Options are saved automatically.
The INI file above also contains extra arte assignments and spell counters tied
to saves; back it up and copy it when moving PCs. Steam Cloud does not automatically include it.

**Support/Status.cmd** checks the installation.
**Support/Compatibility-Mode.cmd** restores the native spell queue while keeping other changes.
See [compatibility limits](FEATURES.md#compatibility-and-limits) and [use-at-your-own-risk terms](ABOUT.md).
