from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import messagebox


MESSAGES = {
    "en": {
        "checking": "Checking for updates...",
        "busy_title": "Update",
        "busy": "The update check is already running.",
        "failed_title": "Update check failed",
        "failed": "I could not check for a new version. Check the internet connection and try again.",
        "current_title": "Up to date",
        "current": "You are using the latest version ({current}).",
        "available_title": "Update available",
        "available": "A new version is available.\n\nCurrent version: {current}\nNew version: {latest}\n\nDownload and install it now?",
        "no_asset_title": "Update",
        "no_asset": "No matching installer was found for this system. Open the download page?",
        "downloading": "Downloading update...",
        "installing": "Installing update...",
        "restart_title": "Update",
        "restart": "The update was downloaded. The application will close and restart.",
        "manual_title": "Update downloaded",
        "manual": "The update was downloaded here:\n{path}\n\nOpen it manually to finish the update.",
        "install_started": "The installer was started. Complete it and start the application again.",
    },
    "hr": {
        "checking": "Provjeravam update...",
        "busy_title": "Update",
        "busy": "Provjera updatea je vec pokrenuta.",
        "failed_title": "Provjera nije uspjela",
        "failed": "Nisam uspio provjeriti novu verziju. Provjerite internet vezu i pokusajte ponovno.",
        "current_title": "Program je azuran",
        "current": "Koristite najnoviju verziju programa ({current}).",
        "available_title": "Dostupna je nova verzija",
        "available": "Dostupna je nova verzija.\n\nTrenutna verzija: {current}\nNova verzija: {latest}\n\nZelite li je sada preuzeti i instalirati?",
        "no_asset_title": "Update",
        "no_asset": "Nisam nasao odgovarajuci installer za ovaj sustav. Otvoriti stranicu za preuzimanje?",
        "downloading": "Preuzimam update...",
        "installing": "Instaliram update...",
        "restart_title": "Update",
        "restart": "Update je preuzet. Aplikacija ce se zatvoriti i ponovno pokrenuti.",
        "manual_title": "Update preuzet",
        "manual": "Update je preuzet ovdje:\n{path}\n\nOtvorite ga rucno za dovrsetak updatea.",
        "install_started": "Installer je pokrenut. Dovrsite instalaciju i ponovno pokrenite aplikaciju.",
    },
}


class SelfUpdater:
    def __init__(
        self,
        root,
        app_name: str,
        app_version: str,
        repo: str,
        *,
        binary_names: list[str] | tuple[str, ...],
        linux_command: str | None = None,
        status_callback=None,
        button_getter=None,
        language_getter=None,
    ) -> None:
        self.root = root
        self.app_name = app_name
        self.app_version = app_version
        self.repo = repo
        self.binary_names = tuple(binary_names)
        self.linux_command = linux_command
        self.status_callback = status_callback
        self.button_getter = button_getter
        self.language_getter = language_getter
        self.running = False

    def check(self, *, show_current: bool = True, show_errors: bool = True) -> None:
        if self.running:
            messagebox.showinfo(self._msg("busy_title"), self._msg("busy"))
            return
        self.running = True
        self._set_button_enabled(False)
        self._set_status(self._msg("checking"))
        threading.Thread(target=self._check_worker, args=(show_current, show_errors), daemon=True).start()

    def _check_worker(self, show_current: bool, show_errors: bool) -> None:
        release = None
        error = None
        try:
            release = self._fetch_latest_release()
        except (OSError, TimeoutError, urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
            error = exc
        self._after(lambda: self._handle_release_result(release, error, show_current, show_errors))

    def _fetch_latest_release(self) -> dict:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repo}/releases/latest",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"{self.app_name}/{self.app_version}",
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get("draft") or data.get("prerelease"):
            return {}
        return {
            "tag": str(data.get("tag_name", "")).strip(),
            "url": data.get("html_url") or f"https://github.com/{self.repo}/releases/latest",
            "assets": data.get("assets") or [],
        }

    def _handle_release_result(self, release: dict | None, error: Exception | None, show_current: bool, show_errors: bool) -> None:
        self.running = False
        self._set_button_enabled(True)
        if error is not None or not release or not release.get("tag"):
            self._set_status(self._msg("failed"))
            if show_errors:
                messagebox.showwarning(self._msg("failed_title"), self._msg("failed"))
            return

        latest = str(release["tag"])
        if not self.is_newer_version(latest, self.app_version):
            self._set_status(self._msg("current").format(current=self.app_version))
            if show_current:
                messagebox.showinfo(self._msg("current_title"), self._msg("current").format(current=self.app_version))
            return

        asset = self._select_asset(release.get("assets") or [])
        if asset is None:
            if messagebox.askyesno(self._msg("no_asset_title"), self._msg("no_asset")):
                webbrowser.open(str(release.get("url") or f"https://github.com/{self.repo}/releases/latest"), new=2)
            return

        if messagebox.askyesno(
            self._msg("available_title"),
            self._msg("available").format(current=self.app_version, latest=latest),
        ):
            self._download_and_install(asset)

    def _download_and_install(self, asset: dict) -> None:
        self.running = True
        self._set_button_enabled(False)
        self._set_status(self._msg("downloading"))
        threading.Thread(target=self._download_worker, args=(asset,), daemon=True).start()

    def _download_worker(self, asset: dict) -> None:
        path = None
        error = None
        try:
            path = self._download_asset(asset)
        except (OSError, TimeoutError, urllib.error.URLError, ValueError) as exc:
            error = exc
        self._after(lambda: self._handle_download_result(path, error))

    def _download_asset(self, asset: dict) -> Path:
        url = asset.get("browser_download_url")
        name = asset.get("name") or f"{self.app_name}-update"
        if not url:
            raise ValueError("release asset has no download URL")
        safe_name = re.sub(r"[^A-Za-z0-9._+-]+", "-", str(name)).strip("-") or "update"
        target_dir = Path(tempfile.gettempdir()) / f"{self._slug()}-updates"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / safe_name
        request = urllib.request.Request(str(url), headers={"User-Agent": f"{self.app_name}/{self.app_version}"})
        with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        return target

    def _handle_download_result(self, path: Path | None, error: Exception | None) -> None:
        self.running = False
        self._set_button_enabled(True)
        if error is not None or path is None:
            messagebox.showwarning(self._msg("failed_title"), self._msg("failed"))
            return
        self._set_status(self._msg("installing"))
        try:
            action = self._install(path)
        except Exception as exc:  # noqa: BLE001 - GUI must show a friendly fallback.
            messagebox.showwarning(self._msg("manual_title"), self._msg("manual").format(path=path))
            self._set_status(str(exc))
            return
        if action == "restart":
            messagebox.showinfo(self._msg("restart_title"), self._msg("restart"))
            self._shutdown_app()
        elif action == "started":
            messagebox.showinfo(self._msg("restart_title"), self._msg("install_started"))
            self._shutdown_app()
        else:
            messagebox.showinfo(self._msg("manual_title"), self._msg("manual").format(path=path))

    def _install(self, path: Path) -> str:
        suffix = path.name.lower()
        if sys.platform.startswith("win") and suffix.endswith(".exe"):
            return self._install_windows_exe(path)
        if sys.platform.startswith("linux"):
            if suffix.endswith(".appimage"):
                return self._install_linux_appimage(path)
            if suffix.endswith(".tar.gz"):
                return self._install_linux_tar(path)
            if suffix.endswith(".deb"):
                return self._install_linux_deb(path)
        self._open_file(path)
        return "manual"

    def _install_windows_exe(self, path: Path) -> str:
        current = self._current_executable()
        if current is None:
            subprocess.Popen([str(path)], close_fds=True)
            return "started"
        script = path.with_suffix(".bat")
        script.write_text(
            "\n".join(
                [
                    "@echo off",
                    f":wait",
                    f'tasklist /FI "PID eq {os.getpid()}" | find "{os.getpid()}" >nul',
                    "if not errorlevel 1 (timeout /T 1 /NOBREAK >nul & goto wait)",
                    f'copy /Y "{path}" "{current}" >nul',
                    f'start "" "{current}"',
                    f'del "{path}"',
                    'del "%~f0"',
                ]
            ),
            encoding="utf-8",
        )
        subprocess.Popen(["cmd", "/c", str(script)], close_fds=True)
        return "restart"

    def _install_linux_appimage(self, path: Path) -> str:
        os.chmod(path, os.stat(path).st_mode | 0o755)
        current = self._current_appimage_or_executable()
        if current is None:
            subprocess.Popen([str(path)], close_fds=True)
            return "started"
        self._write_linux_replace_script(path, current, restart=[str(current)])
        return "restart"

    def _install_linux_tar(self, path: Path) -> str:
        current = self._current_executable()
        if current is None:
            self._open_file(path)
            return "manual"
        extracted_binary = self._extract_tar_binary(path)
        self._write_linux_replace_script(extracted_binary, current, restart=[str(current)])
        return "restart"

    def _install_linux_deb(self, path: Path) -> str:
        command = self.linux_command or (self.binary_names[-1] if self.binary_names else "")
        script = path.with_suffix(".install.sh")
        installer = f"apt install -y {shlex.quote(str(path))}"
        if os.geteuid() != 0:
            pkexec = shutil.which("pkexec")
            if pkexec:
                installer = f"{shlex.quote(pkexec)} apt install -y {shlex.quote(str(path))}"
            else:
                self._open_file(path)
                return "manual"
        restart_line = f"nohup {shlex.quote(command)} >/dev/null 2>&1 &" if command else ""
        script.write_text(
            "\n".join(
                [
                    "#!/bin/sh",
                    f"while kill -0 {os.getpid()} 2>/dev/null; do sleep 1; done",
                    installer,
                    restart_line,
                    f"rm -f {shlex.quote(str(path))}",
                    f"rm -f {shlex.quote(str(script))}",
                ]
            ),
            encoding="utf-8",
        )
        os.chmod(script, 0o755)
        subprocess.Popen(["/bin/sh", str(script)], close_fds=True)
        return "started"

    def _write_linux_replace_script(self, source: Path, target: Path, *, restart: list[str]) -> None:
        script = source.with_suffix(source.suffix + ".install.sh")
        restart_command = " ".join(shlex.quote(part) for part in restart)
        script.write_text(
            "\n".join(
                [
                    "#!/bin/sh",
                    f"while kill -0 {os.getpid()} 2>/dev/null; do sleep 1; done",
                    f"cp {shlex.quote(str(source))} {shlex.quote(str(target))}",
                    f"chmod +x {shlex.quote(str(target))}",
                    f"nohup {restart_command} >/dev/null 2>&1 &",
                    f"rm -f {shlex.quote(str(source))}",
                    f"rm -f {shlex.quote(str(script))}",
                ]
            ),
            encoding="utf-8",
        )
        os.chmod(script, 0o755)
        subprocess.Popen(["/bin/sh", str(script)], close_fds=True)

    def _extract_tar_binary(self, path: Path) -> Path:
        extract_dir = path.with_suffix("").with_suffix("")
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True)
        base = extract_dir.resolve()
        with tarfile.open(path, "r:gz") as archive:
            for member in archive.getmembers():
                target = (extract_dir / member.name).resolve()
                if not target.is_relative_to(base):
                    raise ValueError("unsafe tar member")
                archive.extract(member, extract_dir)
        for name in self.binary_names:
            for candidate in extract_dir.rglob(name):
                if candidate.is_file():
                    os.chmod(candidate, os.stat(candidate).st_mode | 0o755)
                    return candidate
        for candidate in extract_dir.rglob("*"):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate
        raise FileNotFoundError("updated binary was not found in archive")

    def _select_asset(self, assets: list[dict]) -> dict | None:
        names = [(asset, str(asset.get("name") or "").lower()) for asset in assets]
        if sys.platform.startswith("win"):
            return self._first(names, [".exe"], ["windows", "win"]) or self._first(names, [".exe"], [])
        if sys.platform.startswith("linux"):
            if os.environ.get("APPIMAGE"):
                return self._first(names, [".appimage"], []) or self._first(names, [".tar.gz"], []) or self._first(names, [".deb"], [])
            current = self._current_executable()
            if current and str(current).startswith("/usr/"):
                return self._first(names, [".deb"], []) or self._first(names, [".appimage"], []) or self._first(names, [".tar.gz"], [])
            return self._first(names, [".tar.gz"], []) or self._first(names, [".appimage"], []) or self._first(names, [".deb"], [])
        return None

    def _first(self, names: list[tuple[dict, str]], endings: list[str], preferred_words: list[str]) -> dict | None:
        matches = [(asset, name) for asset, name in names if any(name.endswith(ending) for ending in endings)]
        for word in preferred_words:
            for asset, name in matches:
                if word in name:
                    return asset
        return matches[0][0] if matches else None

    def _current_executable(self) -> Path | None:
        if getattr(sys, "frozen", False):
            return Path(sys.executable)
        return None

    def _current_appimage_or_executable(self) -> Path | None:
        appimage = os.environ.get("APPIMAGE")
        if appimage:
            return Path(appimage)
        return self._current_executable()

    def _open_file(self, path: Path) -> None:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)], close_fds=True)
        else:
            subprocess.Popen(["xdg-open", str(path)], close_fds=True)

    def _shutdown_app(self) -> None:
        try:
            self.root.after(300, self.root.destroy)
        except Exception:
            os._exit(0)

    def _set_button_enabled(self, enabled: bool) -> None:
        if self.button_getter is None:
            return
        try:
            button = self.button_getter()
            if button is not None:
                state = "normal" if enabled else "disabled"
                try:
                    button.configure(state=state)
                except Exception:
                    button.config(state=state)
        except Exception:
            pass

    def _set_status(self, message: str) -> None:
        if self.status_callback is None:
            return
        try:
            self.status_callback(message)
        except Exception:
            pass

    def _after(self, callback) -> None:
        try:
            self.root.after(0, callback)
        except Exception:
            pass

    def _language(self) -> str:
        if self.language_getter is None:
            return "hr"
        try:
            language = str(self.language_getter()).lower()
        except Exception:
            return "hr"
        return "hr" if language.startswith("hr") or "hrvat" in language else "en"

    def _msg(self, key: str) -> str:
        return MESSAGES.get(self._language(), MESSAGES["en"]).get(key, MESSAGES["en"][key])

    def _slug(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.app_name.lower()).strip("-") or "app"

    @staticmethod
    def version_tuple(value: str) -> tuple[int, int, int]:
        parts = [int(part) for part in re.findall(r"\d+", str(value).lstrip("v"))[:3]]
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts)

    @classmethod
    def is_newer_version(cls, latest: str, current: str) -> bool:
        return cls.version_tuple(latest) > cls.version_tuple(current)
