# Install, update or uninstall

[Overview](../README.md) · [Features](FEATURES.md) · [Controls](CONTROLS.md)

Requires **Windows / Steam build 25190541** and at least **5 GiB of free space**. Mods that change the same game files may conflict.

## Install

1. Back up your saves and `%LOCALAPPDATA%\TalesOfEternia-WatersEdition.ini`.
2. Close the game and [download the mod archive](https://github.com/Water130/tales-of-eternia-waters-edition/releases/latest). Choose the archive containing **Install.cmd**, rather than GitHub's source code downloads.
3. Extract the whole archive. Keep **Install.cmd**, **Uninstall.cmd** and **Support** together.
4. Run **Install.cmd**, check the game folder and confirm with **Y**.
5. Wait for **Installed and verified**, then launch through Steam.

If asked for the game folder, open Steam and select **Manage → Browse local files** for Tales of Eternia, then copy that folder's path.

## Update or remove

To **update**, uninstall the previous version using the uninstaller that came with it, then install the new one.

To **remove** the mod, close the game, run **Uninstall.cmd** and confirm the game folder. Keep the original-file backups created by the installer. Mod settings are retained after removal.

If the uninstaller cannot restore the files, use [Steam's file verification](https://help.steampowered.com/en/faqs/view/0C48-FCBD-DA71-93EB). This restores game files and may also replace changes made by other mods. It cannot recover damaged saves or lost progress.

## Settings and backups

Open **Mod settings** on the title screen. Choices are saved automatically.

The settings file listed above also stores extra arte assignments and progression data. Back it up alongside your saves and copy it when moving to another PC; Steam Cloud does not automatically include it.

## Troubleshooting

| Situation | What to do |
| --- | --- |
| Game still running | Close it completely before installing or removing the mod. |
| Unsupported or modified game files | Check the required game build and restore its original files before installing. |
| Check whether the mod is installed | Run **Support/Status.cmd**. |
| Problems with overlapping spells | Run **Support/Compatibility-Mode.cmd** to restore the original spell queue. |

See [About Water's Edition](ABOUT.md) for the project's limitations and sharing permissions.
