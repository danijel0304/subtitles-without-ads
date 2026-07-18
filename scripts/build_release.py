#!/usr/bin/env python3
from __future__ import annotations

import io
import os
import re
import shutil
import stat
import subprocess
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "Subtitles Without Ads"
APP_SLUG = "subtitles-without-ads"
PYINSTALLER_BINARY = ROOT / "dist" / APP_NAME
RELEASE_DIR = ROOT / "release"
BUILD_DIR = ROOT / "build" / "release"
APPDIR = BUILD_DIR / f"{APP_SLUG}.AppDir"


def run(command: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, env=env, check=True)


def read_version() -> str:
    source = (ROOT / "subtitles_without_ads.py").read_text(encoding="utf-8")
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", source)
    if not match:
        raise RuntimeError("APP_VERSION was not found in subtitles_without_ads.py")
    return match.group(1)


def clean() -> None:
    RELEASE_DIR.mkdir(exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    for path in RELEASE_DIR.iterdir():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    if APPDIR.exists():
        shutil.rmtree(APPDIR)


def build_pyinstaller() -> None:
    run(["pyinstaller", "--clean", "--noconfirm", "subtitles_without_ads.spec"])
    if not PYINSTALLER_BINARY.exists():
        raise RuntimeError(f"PyInstaller did not create {PYINSTALLER_BINARY}")


def make_linux_tar(version: str) -> Path:
    package_dir = BUILD_DIR / f"{APP_SLUG}-{version}-linux-x86_64"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True)
    shutil.copy2(PYINSTALLER_BINARY, package_dir / APP_SLUG)
    os.chmod(package_dir / APP_SLUG, 0o755)
    shutil.copy2(ROOT / "DESCRIPTION_AND_INSTRUCTIONS.txt", package_dir / "DESCRIPTION_AND_INSTRUCTIONS.txt")
    shutil.copy2(ROOT / "README.md", package_dir / "README.md")

    run_script = package_dir / "run.sh"
    run_script.write_text(
        '#!/usr/bin/env sh\nDIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec "$DIR/subtitles-without-ads" "$@"\n',
        encoding="utf-8",
    )
    os.chmod(run_script, 0o755)

    output = RELEASE_DIR / f"{APP_SLUG}-{version}-linux-x86_64.tar.gz"
    with tarfile.open(output, "w:gz") as archive:
        archive.add(package_dir, arcname=package_dir.name)
    return output


def tar_bytes(files: dict[str, tuple[bytes, int]], xz: bool = True) -> bytes:
    buffer = io.BytesIO()
    mode = "w:xz" if xz else "w:gz"
    with tarfile.open(fileobj=buffer, mode=mode) as archive:
        for name, (content, file_mode) in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            info.mode = file_mode
            info.uid = 0
            info.gid = 0
            info.uname = "root"
            info.gname = "root"
            archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def make_deb(version: str) -> Path:
    package = f"{APP_SLUG}_{version}_amd64"
    deb_work = BUILD_DIR / package
    if deb_work.exists():
        shutil.rmtree(deb_work)
    deb_work.mkdir(parents=True)

    desktop = (ROOT / "packaging" / f"{APP_SLUG}.desktop").read_bytes()
    icon = (ROOT / "packaging" / f"{APP_SLUG}.svg").read_bytes()
    binary = PYINSTALLER_BINARY.read_bytes()
    readme = (ROOT / "DESCRIPTION_AND_INSTRUCTIONS.txt").read_bytes()
    wrapper = f'#!/usr/bin/env sh\nexec "/opt/{APP_SLUG}/{APP_NAME}" "$@"\n'.encode("utf-8")
    copyright_text = (
        "Subtitles Without Ads\n"
        "Author: Danijel\n"
        "License: Free for personal use. See application notes for details.\n"
    ).encode("utf-8")

    control = (
        f"Package: {APP_SLUG}\n"
        f"Version: {version}\n"
        "Section: utils\n"
        "Priority: optional\n"
        "Architecture: amd64\n"
        "Maintainer: Danijel <danijel0304@users.noreply.github.com>\n"
        "Depends: libc6\n"
        "Description: Clean SRT subtitles from ads and promotional text\n"
        " Subtitles Without Ads is a small GUI tool for cleaning subtitle files.\n"
    ).encode("utf-8")

    control_tar = tar_bytes({"./control": (control, 0o644)})
    data_tar = tar_bytes(
        {
            f"./opt/{APP_SLUG}/{APP_NAME}": (binary, 0o755),
            f"./opt/{APP_SLUG}/DESCRIPTION_AND_INSTRUCTIONS.txt": (readme, 0o644),
            f"./usr/bin/{APP_SLUG}": (wrapper, 0o755),
            f"./usr/share/applications/{APP_SLUG}.desktop": (desktop, 0o644),
            f"./usr/share/icons/hicolor/scalable/apps/{APP_SLUG}.svg": (icon, 0o644),
            f"./usr/share/doc/{APP_SLUG}/copyright": (copyright_text, 0o644),
        }
    )

    debian_binary = deb_work / "debian-binary"
    control_path = deb_work / "control.tar.xz"
    data_path = deb_work / "data.tar.xz"
    debian_binary.write_text("2.0\n", encoding="ascii")
    control_path.write_bytes(control_tar)
    data_path.write_bytes(data_tar)

    output = RELEASE_DIR / f"{package}.deb"
    run(["ar", "rcs", str(output), "debian-binary", "control.tar.xz", "data.tar.xz"], cwd=deb_work)
    return output


def make_appdir() -> None:
    if APPDIR.exists():
        shutil.rmtree(APPDIR)
    (APPDIR / "usr" / "bin").mkdir(parents=True)
    (APPDIR / "usr" / "share" / "applications").mkdir(parents=True)
    (APPDIR / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps").mkdir(parents=True)

    shutil.copy2(PYINSTALLER_BINARY, APPDIR / "usr" / "bin" / APP_SLUG)
    os.chmod(APPDIR / "usr" / "bin" / APP_SLUG, 0o755)

    app_run = APPDIR / "AppRun"
    app_run.write_text(
        '#!/usr/bin/env sh\nHERE=$(dirname "$(readlink -f "$0")")\nexec "$HERE/usr/bin/subtitles-without-ads" "$@"\n',
        encoding="utf-8",
    )
    os.chmod(app_run, 0o755)

    desktop_src = ROOT / "packaging" / f"{APP_SLUG}.desktop"
    icon_src = ROOT / "packaging" / f"{APP_SLUG}.svg"
    shutil.copy2(desktop_src, APPDIR / f"{APP_SLUG}.desktop")
    shutil.copy2(desktop_src, APPDIR / "usr" / "share" / "applications" / f"{APP_SLUG}.desktop")
    shutil.copy2(icon_src, APPDIR / f"{APP_SLUG}.svg")
    shutil.copy2(icon_src, APPDIR / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps" / f"{APP_SLUG}.svg")


def find_appimagetool() -> Path | None:
    env_tool = os.environ.get("APPIMAGETOOL")
    candidates = []
    if env_tool:
        candidates.append(Path(env_tool))
    which_tool = shutil.which("appimagetool")
    if which_tool:
        candidates.append(Path(which_tool))
    candidates.append(ROOT / "tools" / "appimagetool-x86_64.AppImage")

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def make_appimage(version: str) -> Path | None:
    make_appdir()
    tool = find_appimagetool()
    if tool is None:
        print("AppImage skipped: appimagetool was not found.")
        return None

    output = RELEASE_DIR / f"{APP_SLUG}-{version}-x86_64.AppImage"
    env = os.environ.copy()
    env["ARCH"] = "x86_64"
    env["APPIMAGE_EXTRACT_AND_RUN"] = "1"
    run([str(tool), str(APPDIR), str(output)], env=env)
    os.chmod(output, os.stat(output).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return output


def validate() -> None:
    run(["python3", "-B", "-c", "import py_compile; py_compile.compile('subtitles_without_ads.py', cfile='/tmp/subtitles_without_ads.pyc', doraise=True)"])
    if shutil.which("desktop-file-validate"):
        run(["desktop-file-validate", str(ROOT / "packaging" / f"{APP_SLUG}.desktop")])


def main() -> None:
    version = read_version()
    clean()
    validate()
    build_pyinstaller()

    artifacts = [
        make_linux_tar(version),
        make_deb(version),
    ]
    appimage = make_appimage(version)
    if appimage:
        artifacts.append(appimage)

    print("\nArtifacts:")
    for artifact in artifacts:
        print(f"- {artifact.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
