#!/usr/bin/env python
"""Check for zoom update and send a notification when it needs to be updated."""

from __future__ import annotations

import abc
import argparse
import dataclasses
import json
import pathlib
import re
import subprocess
import tempfile
import time
from collections.abc import Collection, Mapping
from typing import TypedDict


class PackageMetadata(TypedDict):
    version: str
    url: str


class Package(abc.ABC):
    name: str

    @abc.abstractmethod
    def get_latest_version(self) -> PackageMetadata:
        """Get the latest version."""
        raise NotImplementedError

    def get_installed_version(self) -> str:
        """Get the installed version (default: via `apt show`)."""
        re_version = re.compile(r"Version: ([\d.-]+)$", flags=re.MULTILINE)
        p = subprocess.run(["apt", "show", self.name], capture_output=True)
        p.check_returncode()
        stdout = p.stdout.decode(encoding="utf8")
        if m := re_version.search(stdout):
            return m.group(1).split("-")[0]
        else:
            print(f"Could not parse installed version from:\n{stdout}")
            exit(-1)


@dataclasses.dataclass
class Zoom(Package):
    name: str = "zoom"

    def get_latest_version(self) -> PackageMetadata:
        """Get the latest version of Zoom (via unofficial REST API.)"""
        with tempfile.NamedTemporaryFile() as temporary_file:
            subprocess.run(
                [
                    "curl",
                    "https://zoom.us/rest/download?os=linux",
                    "-s",
                    "-o",
                    temporary_file.name,
                ],
                check=True,
            )
            data = json.loads(pathlib.Path(temporary_file.name).read_text())
        version = data["result"]["downloadVO"]["zoom"]["version"]
        url = f"https://zoom.us/client/{version}/zoom_amd64.deb"
        return PackageMetadata(version=version, url=url)


@dataclasses.dataclass
class Glab(Package):
    name: str = "glab"

    def get_latest_version(self) -> PackageMetadata:
        """Get the latest version of glab (via GitLab Releases API.)"""
        with tempfile.NamedTemporaryFile() as temporary_file:
            subprocess.run(
                [
                    "curl",
                    "https://gitlab.com/api/v4/projects/gitlab-org%2Fcli/releases/permalink/latest",
                    "-s",
                    "-L",
                    "-o",
                    temporary_file.name,
                ],
                check=True,
            )
            data = json.loads(pathlib.Path(temporary_file.name).read_text())
        version = data["tag_name"].lstrip("v")
        asset_name = f"glab_{version}_linux_amd64.deb"
        link = next(
            link for link in data["assets"]["links"] if link["name"] == asset_name
        )
        url = link.get("direct_asset_url", link["url"])
        return PackageMetadata(version=version, url=url)


@dataclasses.dataclass
class Pi(Package):
    name: str = "pi"

    def get_latest_version(self) -> PackageMetadata:
        """Get the latest version of pi (via GitHub Releases API.)"""
        with tempfile.NamedTemporaryFile() as temporary_file:
            subprocess.run(
                [
                    "curl",
                    "https://api.github.com/repos/earendil-works/pi/releases/latest",
                    "-s",
                    "-L",
                    "-o",
                    temporary_file.name,
                ],
                check=True,
            )
            data = json.loads(pathlib.Path(temporary_file.name).read_text())
        version = data["tag_name"].lstrip("v")
        asset_name = "pi-linux-x64.tar.gz"
        asset = next(
            asset for asset in data["assets"] if asset["name"] == asset_name
        )
        url = asset["browser_download_url"]
        return PackageMetadata(version=version, url=url)

    def get_installed_version(self) -> str:
        """Get the installed version of pi (via `pi --version`)."""
        re_version = re.compile(r"(\d+\.\d+\.\d+)")
        p = subprocess.run(["pi", "--version"], capture_output=True)
        p.check_returncode()
        stdout = p.stdout.decode(encoding="utf8")
        if m := re_version.search(stdout):
            return m.group(1)
        else:
            print(f"Could not parse installed version from:\n{stdout}")
            exit(-1)


@dataclasses.dataclass
class Codex(Package):
    name: str = "codex"

    def get_latest_version(self) -> PackageMetadata:
        """Get the latest version of Codex (via GitHub Releases API)."""
        with tempfile.NamedTemporaryFile() as temporary_file:
            subprocess.run(
                [
                    "curl",
                    "https://api.github.com/repos/openai/codex/releases/latest",
                    "-s",
                    "-L",
                    "-o",
                    temporary_file.name,
                ],
                check=True,
            )
            data = json.loads(pathlib.Path(temporary_file.name).read_text())
        return PackageMetadata(
            version=data["name"].lstrip("v"),
            url="https://chatgpt.com/codex/install.sh",
        )

    def get_installed_version(self) -> str:
        """Get the installed version of Codex (via `codex --version`)."""
        re_version = re.compile(r"codex-cli (\d+\.\d+\.\d+)")
        p = subprocess.run(["codex", "--version"], capture_output=True)
        p.check_returncode()
        stdout = p.stdout.decode(encoding="utf8")
        if m := re_version.search(stdout):
            return m.group(1)
        else:
            print(f"Could not parse installed version from:\n{stdout}")
            exit(-1)


@dataclasses.dataclass
class Manager:
    packages: Package | Collection[Package]
    download: bool = True
    notification: bool = True
    verbose: bool = True
    timeout: float | int = 24 * 60 * 60
    cache_root: pathlib.Path = pathlib.Path.home().joinpath(
        ".cache", "simple_package_manager"
    )
    download_root: pathlib.Path = pathlib.Path(tempfile.gettempdir(), "updates")
    _packages: Mapping[str, Package] = dataclasses.field(init=False, repr=False)

    def __post_init__(self):
        packages = self.packages
        if isinstance(packages, Package):
            packages = [packages]
        _packages = {}
        for package in packages:
            _packages[package.name] = package
        self._packages = _packages

    def get_installed_version(self, name: str) -> str:
        """Get the installed version."""
        return self._packages[name].get_installed_version()

    def get_latest_version(self, name: str, force: bool = False) -> PackageMetadata:
        """Get the latest version."""
        cache_path = self.cache_root.joinpath(name).with_suffix(".json")
        if (
            force
            or not cache_path.is_file()
            or time.time() - cache_path.stat().st_mtime > self.timeout
        ):
            self.cache_root.mkdir(parents=True, exist_ok=True)
            cache_path.unlink(missing_ok=True)
            data = self._packages[name].get_latest_version()
            with cache_path.open(mode="w") as f:
                json.dump(data, f, indent=2, sort_keys=True)
        with cache_path.open() as f:
            data = json.load(f)
        return data

    def _check(self, name: str, force: bool) -> None:
        version_installed = self.get_installed_version(name)
        if self.verbose:
            print(f"# Package: {name!r}")
            print("Installed:", version_installed)
        meta = self.get_latest_version(name=name, force=force)
        version_latest = meta["version"]
        if self.verbose:
            print("Latest:   ", version_latest)
        if version_installed == version_latest:
            if self.verbose:
                print(f"{name!r} is up-to-date")
            if not self.notification:
                return
            subprocess.run(
                [
                    "notify-send",
                    "-u",
                    "low",
                    f"{name} is up-to-date ({version_installed})",
                ]
            )
        else:
            if self.verbose:
                print("Zoom needs an update")
            if not self.notification:
                exit(-1)
            else:
                url = meta["url"]
                if self.download_root:
                    suffix = "".join(pathlib.PurePosixPath(url).suffixes)
                    output_path = pathlib.Path(self.download_root).joinpath(
                        f"{name}_{version_latest}{suffix}"
                    )
                    output_path.parent.mkdir(exist_ok=True, parents=True)
                    subprocess.run(["wget", "-O", str(output_path), url], check=True)
                    message = (
                        f"'{name} update available ({version_installed} -> {version_latest})'",
                        output_path,
                    )
                else:
                    message = (
                        f"'{name} update available ({version_installed} -> {version_latest})'",
                        url,
                    )
                subprocess.run(["notify-send", "-u", "critical", *message])

    def check(self, force: bool = False):
        for name in self._packages:
            self._check(name=name, force=force)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--no-message", action="store_true")
    parser.add_argument("--direct-link", action="store_true")
    parser.add_argument(
        "--cache-root",
        type=pathlib.Path,
        default=pathlib.Path("~", ".cache", "simple_package_manager").expanduser(),
    )
    parser.add_argument("--timeout", type=float, default=24 * 60 * 60)
    parser.add_argument("--download-root", type=str, default=tempfile.gettempdir())
    args = parser.parse_args()
    cache_root = pathlib.Path(args.cache_root)
    manager = Manager(
        packages=[Zoom(), Glab(), Pi(), Codex()],
        cache_root=cache_root,
        timeout=args.timeout,
    )
    manager.check(force=args.force)


if __name__ == "__main__":
    main()
