# Titlovi Bez Reklama

Mali Tkinter alat za automatsko čišćenje `.srt` titlova od reklama, potpisa prevoditelja i promotivnog teksta.

## Pokretanje

Linux/macOS:

```sh
./pokreni_titlovi_bez_reklama.sh
```

Windows:

```bat
pokreni_titlovi_bez_reklama.bat
```

Direktno s Pythonom:

```sh
python3 titlovi_bez_reklama.py
```

## Izrada paketa

Linux build:

```sh
python3 scripts/build_release.py
```

Skripta izrađuje artefakte u `release/`:

- Linux `.tar.gz`
- Linux `.deb`
- Linux AppImage, ako je dostupan `appimagetool`

Windows `.exe` se gradi na Windowsu:

```bat
build_windows_exe.bat
```

## Napomena

Prije masovne obrade testiraj program na kopiji nekoliko titlova. Ključne riječi su namjerno precizne kako se ne bi uklanjali normalni dijelovi dijaloga.
