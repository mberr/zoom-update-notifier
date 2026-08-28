# Package Update Notifier for Ubuntu

This repo contains a small utility to notify about new versions of Zoom, GitLab CLI,
Pi, and Codex. It assumes

- Zoom is installed manually via the `.deb` file available from the [official Download page](https://zoom.us/download).
- Python 3 is available
- `apt`, `curl` and `notify-send` are available

Codex is checked through its GitHub releases. Its update notification points to the
[official standalone installer](https://chatgpt.com/codex/install.sh), which is also
the update method recommended by Codex itself.

It checks at most once per day whether each package's release API reports a newer
version than the one installed locally, and sends a notification when it does.

# Installation

- Move / Link `./bin/check_zoom_update.py` to somewhere which is in your `$PATH`, e.g.,
  ```shell
  ln -s ./check_zoom_update.py \
    $HOME/bin/check_zoom_update.py
  ```
  You may want to verify that the script is executable
  ```shell
  chmod u+x $HOME/bin/check_zoom_update.py
  ``` 
- (optional) let the script run on every login, by moving/linking
  the [desktop entry](https://wiki.archlinux.org/title/Desktop_entries):
  ```shell
  ln -s ./zoom_update_check.desktop \
    $HOME/.config/autostart/zoom_update_check.desktop
  ```
