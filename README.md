# Zoom Update Notifier for Ubuntu

This repo contains some small utilities to notify about new Zoom versions. It assumes

- Zoom is installed manually via the `.deb` file available from the [official Download page](https://zoom.us/download).
- Python 3 is available
- `apt`, `curl` and `notify-send` are available

It checks at most once per day if the version returned by the [REST API](https://zoom.us/rest/download?os=linux) matches
the one of the package, and sends a notification when this is not the case.

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
