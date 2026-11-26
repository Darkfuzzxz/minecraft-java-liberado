#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
MoonSusX v3.7 - Launcher para Minecraft Java
Hecho para axel / elplayergod

Flujo:
  1. Escoges una version.
  2. Boton 1: INSTALAR MINECRAFT
     NO te manda a ninguna pagina ni abre el Launcher.
     MoonSusX se conecta directo a los servidores oficiales
     de Mojang, los mismos que usa el Launcher oficial:
       piston-meta.mojang.com  (lista de versiones y .json)
       piston-data.mojang.com  (cliente, librerias, assets)
       libraries.minecraft.net (librerias)
     Y descarga, en tu PC, gratis:
       - <version>.json y <version>.jar
       - librerias para Windows + natives
       - assets (texturas, sonidos, etc.)
       - configuracion de logs
       - Java runtime, si no tienes uno (Temurin, dentro de la app)
     Todo queda en %APPDATA%\.minecraft, como lo deja el Launcher oficial.
     Para que todo funcione necesitas tener el Launcher oficial
     instalado / tu cuenta de Minecraft, pero MoonSusX no te
     abre su ventana ni te manda a su pagina: descarga el solo.

  3. Cuando la version ya esta instalada, aparece el boton 2: EJECUTAR
     Crea un .bat para esa version, parecido al .bat que me pasaste:
       @echo off, javaw.exe, -Xms2G -Xmx4G,
       --username elplayergod, --version <version>,
       --uuid ..., --accessToken null, --clientId ..., --xuid ...,
       --versionType release, --width 1024 --height 768
     Lo genera leyendo el <version>.json oficial.
     Y luego lo ejecuta, para mandarte a jugar.
     El .bat queda como minecraft-<version>.bat en esta carpeta.

Requisitos en Windows: Python 3.10+, internet.
"""
import hashlib
import re
import json
import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
import urllib.request
import zipfile
from tkinter import messagebox, ttk
from pathlib import Path

USERNAME = "elplayergod"
USERNAME_FILE = Path(__file__).resolve().parent / "username.txt"

def get_username() -> str:
    """Nombre del jugador, que se puede cambiar en el launcher.
    Se guarda en username.txt, para que no se pierda al actualizar.
    Si el archivo no existe o esta vacio, es elplayergod."""
    try:
        if USERNAME_FILE.is_file():
            name = USERNAME_FILE.read_text(encoding="utf-8").strip()
            if name:
                return name
    except Exception:
        pass
    return USERNAME

def save_username(name: str) -> str:
    """Guarda el nombre, limpiandolo. Minecraft solo acepta
    letras, numeros y guion bajo, de 3 a 16 caracteres."""
    name = (name or "").strip()
    if not name:
        name = USERNAME
    # Quita espacios y caracteres raros, deja solo lo valido
    name = re.sub(r"[^A-Za-z0-9_]", "", name)[:16]
    if len(name) < 3:
        name = USERNAME
    try:
        USERNAME_FILE.write_text(name, encoding="utf-8")
    except Exception:
        pass
    return name
APP_NAME = "MoonSusX"
VERSION = "0.0.8"
UUID = "db8a8821c02ee7b99473b310d1ef3def"
CLIENT_ID = "MzY1NjI1MGMtNjhhMi00Mjg0LWFlZjctYzk0NTExZDFhMDgy"
XUID = "2535451888961759"
MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_BAT = BASE_DIR / "minecraft.bat"
MANIFEST_CACHE = BASE_DIR / "version_manifest.json"

# Respaldo por si no hay internet al abrir: las de antes.
KNOWN_VERSIONS = [
    "26.3", "1.21.11", "1.21.8", "1.21.5", "1.21.1",
    "1.20.1", "1.19.4", "1.18.2", "1.16.5", "1.12.2",
]

def mc_dir() -> Path:
    return Path(os.environ.get("APPDATA", "")) / ".minecraft"

def versions_dir() -> Path:
    return mc_dir() / "versions"

def version_json(version: str) -> Path:
    return versions_dir() / version / f"{version}.json"

def version_jar(version: str) -> Path:
    return versions_dir() / version / f"{version}.jar"

def natives_dir(version: str) -> Path:
    # Natives ahora van dentro de la carpeta de esa version, no en
    # %APPDATA%\.minecraft\bin, para que cada Minecraft tenga lo suyo.
    return version_folder(version) / "natives"

def version_folder(version: str) -> Path:
    r"""Carpeta organizada de cada Minecraft, dentro de MoonSusX:
    MoonSusX/Minecrafts/<version>/
      minecraft-<version>.bat       <- ejecutable
      minecraft-<version>-seguro.bat
      juego/                        <- gameDir: options, saves, screenshots
      natives/                      <- DLLs nativas de esa version
    Lo compartido (librerias, assets, .jar, .json) sigue en
    %APPDATA%\.minecraft, como lo deja Mojang, porque muchas versiones
    comparten las mismas librerias y no tiene sentido duplicar 500 MB
    de assets por version."""
    return BASE_DIR / "Minecrafts" / version

def game_folder(version: str) -> Path:
    return version_folder(version) / "juego"

def is_installed(version: str) -> bool:
    return version_jar(version).is_file() and version_json(version).is_file()

def installed_versions():
    out = []
    try:
        for d in sorted(versions_dir().iterdir()):
            if d.is_dir() and (d / f"{d.name}.json").is_file():
                out.append(d.name)
    except Exception:
        pass
    return out

def fetch_all_versions():
    """Todas las versiones de Mojang, no solo unas pocas.

    Lee https://piston-meta.mojang.com/mc/game/version_manifest_v2.json
    (la lista oficial que usa el Launcher). En este momento son 926:
    103 release, 762 snapshot, 26 old_beta y 35 old_alpha.
    Guarda una copia en version_manifest.json, y si no hay internet
    usa esa copia, y si tampoco hay copia, usa KNOWN_VERSIONS.
    Devuelve una lista de dicts {id, type} en orden de Mojang
    (de la mas nueva a la mas vieja).
    """
    try:
        req = urllib.request.Request(MANIFEST_URL, headers={"User-Agent": "MoonSusX/3.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            manifest = json.loads(r.read().decode("utf-8"))
        MANIFEST_CACHE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest.get("versions", [])
    except Exception:
        pass
    try:
        if MANIFEST_CACHE.is_file():
            manifest = json.loads(MANIFEST_CACHE.read_text(encoding="utf-8"))
            return manifest.get("versions", [])
    except Exception:
        pass
    return [{"id": v, "type": "release"} for v in KNOWN_VERSIONS]

def filter_versions(all_versions, kind):
    """Filtra la lista completa segun el tipo elegido en la ventana."""
    if kind == "Instaladas":
        inst = set(installed_versions())
        return [v["id"] for v in all_versions if v["id"] in inst] or installed_versions()
    if kind == "Todas":
        return [v["id"] for v in all_versions]
    type_map = {
        "Release": "release",
        "Snapshot": "snapshot",
        "Beta antigua": "old_beta",
        "Alpha antigua": "old_alpha",
    }
    wanted = type_map.get(kind, "release")
    return [v["id"] for v in all_versions if v.get("type") == wanted]

def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def download(url: str, dest: Path, expected_sha1=None, expected_size=None):
    """Descarga un archivo, saltandolo si ya esta completo."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        if expected_size and dest.stat().st_size != expected_size:
            pass
        elif expected_sha1:
            try:
                if sha1_of(dest) == expected_sha1:
                    return False
            except Exception:
                pass
        else:
            return False
    req = urllib.request.Request(url, headers={"User-Agent": "MoonSusX/3.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f, length=1024 * 64)
    return True

def library_allowed(lib: dict) -> bool:
    rules = lib.get("rules")
    if not rules:
        return True
    allowed = False
    for rule in rules:
        action = rule.get("action") == "allow"
        os_rule = rule.get("os", {})
        name = os_rule.get("name")
        if name and name != "windows":
            if action:
                return False
            continue
        allowed = action
    return allowed

def _javaw_candidates():
    """Todos los javaw.exe que puede haber en el PC, en orden de preferencia."""
    out = []
    # 1. Java descargado por MoonSusX, por version (java-runtime-8, -21, -25...)
    try:
        for d in sorted(BASE_DIR.glob("java-runtime-*")):
            p = d / "bin" / "javaw.exe"
            if p.is_file():
                out.append(str(p))
    except Exception:
        pass
    local = BASE_DIR / "java-runtime" / "bin" / "javaw.exe"
    if local.is_file():
        out.append(str(local))
    # 2. Runtime oficial del Launcher
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Packages" / "Microsoft.4297127D64EC6_8wekyb3d8bbwe" / "LocalCache" / "Local" / "runtime"
    try:
        for runtime in sorted(base.glob("java-runtime-*"), reverse=True):
            for javaw in runtime.rglob("bin/javaw.exe"):
                out.append(str(javaw))
    except Exception:
        pass
    try:
        for javaw in sorted((mc_dir() / "runtime").rglob("bin/javaw.exe"), reverse=True):
            out.append(str(javaw))
    except Exception:
        pass
    w = shutil.which("javaw")
    if w:
        out.append(w)
    return list(dict.fromkeys(out))

def find_javaw():
    cands = _javaw_candidates()
    return cands[0] if cands else "javaw.exe"

def find_javaw_for(major: int):
    """Busca un Java con esa version mayor exacta (8 para la 1.0, 21/25 para las nuevas).
    Las versiones viejas como la 1.0 usan LWJGL 2.9.0 y LaunchWrapper,
    y NO arrancan con Java 17/21/25. Si no hay uno exacto, devuelve el primero."""
    for cand in _javaw_candidates():
        if java_major(cand) == major:
            return cand
    return find_javaw()

def java_major(javaw: str) -> int:
    """Detecta la version de Java, para no usar flags que ese Java no entiende."""
    try:
        out = subprocess.run([javaw, "-version"], capture_output=True, text=True, timeout=10)
        txt = (out.stderr or "") + (out.stdout or "")
        m = re.search(r'version "([0-9]+)', txt)
        if m:
            return int(m.group(1))
        m = re.search(r'([0-9]+)\.[0-9]+\.[0-9]+', txt)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return 0

def ensure_java(major: int, log):
    """Descarga Java <major> dentro de la app si no hay uno de esa version.
    Antes solo descargaba si no habia NINGUN Java, y por eso la 1.0
    (que necesita Java 8) se quedaba con el Java 21/25 del Launcher
    y daba 'ERROR AL INICIAR JAVA'. Ahora se descarga por version,
    en java-runtime-<major>, sin borrar los otros."""
    if find_javaw_for(major) and java_major(find_javaw_for(major)) == major:
        return
    log(f"Descargando Java {major} para poder jugar...")
    dest = BASE_DIR / f"java-runtime-{major}.zip"
    url = f"https://api.adoptium.net/v3/binary/latest/{major}/ga/windows/x64/jre/hotspot/normal/eclipse"
    try:
        download(url, dest)
        target = BASE_DIR / f"java-runtime-{major}"
        if target.exists():
            shutil.rmtree(target)
        with zipfile.ZipFile(dest) as z:
            z.extractall(BASE_DIR / "_java_tmp")
        inner = next((BASE_DIR / "_java_tmp").iterdir())
        shutil.move(str(inner), str(target))
        shutil.rmtree(BASE_DIR / "_java_tmp", ignore_errors=True)
        dest.unlink(missing_ok=True)
        log(f"Java {major} descargado.")
    except Exception as e:
        # Java 16 ya no esta en Adoptium como "latest" en algunos casos;
        # la 1.17 pide 16, pero corre bien con 17, asi que prueba con 17.
        if major == 16:
            log("Java 16 no se pudo descargar, probando con Java 17...")
            try:
                ensure_java(17, log)
                return
            except Exception:
                pass
        log(f"No pude descargar Java {major} automaticamente: {e}. Instala Java {major} y vuelve a intentar.")

def install_version(version: str, log, progress):
    """Descarga la version completa de los servidores oficiales de Mojang."""
    log(f"Buscando Minecraft {version} en Mojang...")
    with urllib.request.urlopen(urllib.request.Request(MANIFEST_URL, headers={"User-Agent": "MoonSusX/3.0"}), timeout=30) as r:
        manifest = json.loads(r.read().decode("utf-8"))
    entry = next((v for v in manifest["versions"] if v["id"] == version), None)
    if not entry:
        raise ValueError(f"La version {version} no existe en Mojang. Revisa el nombre.")

    vdir = versions_dir() / version
    vdir.mkdir(parents=True, exist_ok=True)
    # Carpeta organizada de esta version, con su juego dentro
    version_folder(version).mkdir(parents=True, exist_ok=True)
    game_folder(version).mkdir(parents=True, exist_ok=True)
    log("Descargando datos de la version...")
    download(entry["url"], version_json(version), entry.get("sha1"), entry.get("size"))
    data = json.loads(version_json(version).read_text(encoding="utf-8"))

    # Cliente .jar
    client = data["downloads"]["client"]
    log("Descargando el juego (cliente)...")
    download(client["url"], version_jar(version), client.get("sha1"), client.get("size"))
    progress(0.15)

    # Librerias + natives
    libs = [l for l in data.get("libraries", []) if library_allowed(l)]
    log(f"Descargando {len(libs)} librerias...")
    natives = natives_dir(version)
    natives.mkdir(parents=True, exist_ok=True)
    for i, lib in enumerate(libs):
        dl = lib.get("downloads", {})
        art = dl.get("artifact")
        if art and art.get("url"):
            dest = mc_dir() / "libraries" / art["path"].replace("/", "\\")
            download(art["url"], dest, art.get("sha1"), art.get("size"))
        for key in ("natives-windows", "natives-windows-x86", "natives-windows-arm64"):
            nat = dl.get("classifiers", {}).get(key)
            if nat and nat.get("url"):
                tmp = BASE_DIR / "_native_tmp.jar"
                download(nat["url"], tmp, nat.get("sha1"), nat.get("size"))
                try:
                    with zipfile.ZipFile(tmp) as z:
                        for name in z.namelist():
                            if name.startswith("META-INF/"):
                                continue
                            z.extract(name, natives)
                except Exception:
                    pass
                tmp.unlink(missing_ok=True)
        if i % 10 == 0:
            progress(0.15 + 0.35 * (i + 1) / max(1, len(libs)))

    # Log config
    logging_cfg = data.get("logging", {}).get("client", {}).get("file")
    if logging_cfg:
        dest = mc_dir() / "assets" / "log_configs" / logging_cfg["id"]
        download(logging_cfg["url"], dest, logging_cfg.get("sha1"), logging_cfg.get("size"))

    # Assets
    ai = data.get("assetIndex", {})
    if ai.get("url"):
        log("Descargando lista de assets...")
        ai_path = mc_dir() / "assets" / "indexes" / f"{ai['id']}.json"
        download(ai["url"], ai_path, ai.get("sha1"), ai.get("size"))
        assets = json.loads(ai_path.read_text(encoding="utf-8"))
        objects = assets.get("objects", {})
        total = len(objects)
        log(f"Descargando {total} assets (esto puede tardar)...")
        for i, (name, info) in enumerate(objects.items()):
            h = info["hash"]
            dest = mc_dir() / "assets" / "objects" / h[:2] / h
            if not dest.is_file() or dest.stat().st_size != info["size"]:
                url = f"https://resources.download.minecraft.net/{h[:2]}/{h}"
                try:
                    download(url, dest, h, info["size"])
                except Exception:
                    pass
            if i % 50 == 0:
                progress(0.5 + 0.45 * (i + 1) / max(1, total))
        if ai.get("id") in ("legacy", "pre-1.6"):
            log("Copiando sonidos viejos a donde el juego los busca...")
            copy_old_sounds(version, log)

    # Java
    major = infer_required_java(data, version)
    ensure_java(major, log)
    progress(1.0)
    log(f"Minecraft {version} instalado.")

def _arg_rules_allowed(rules):
    """Reglas de Mojang para arguments.game/jvm, en Windows x64.
    features: no es demo, si tiene resolucion personalizada (1024x768),
    no es quick play. os: windows, arch x86/x64."""
    if not rules:
        return True
    allowed = False
    for rule in rules:
        action = rule.get("action") == "allow"
        os_rule = rule.get("os", {})
        if os_rule:
            name = os_rule.get("name")
            if name and name != "windows":
                if action:
                    return False
                continue
            arch = os_rule.get("arch")
            if arch and arch not in ("x86", "x64", "amd64"):
                if action:
                    return False
                continue
        feats = rule.get("features", {})
        if feats:
            # Solo has_custom_resolution es true para nosotros
            for k, v in feats.items():
                want = (k == "has_custom_resolution")
                if bool(v) != want:
                    if action:
                        return False
                    continue
        allowed = action
    return allowed

def _substitute(text, subs):
    for k, v in subs.items():
        text = text.replace(k, v)
    return text

def resolve_argument_list(arg_list, subs):
    """Resuelve una lista arguments.game/jvm de Mojang a texto plano,
    respetando sus reglas. Es lo que hace que la 1.13-1.17 NO reciba
    --clientId/--xuid (que solo existen desde la 1.19) y que la 26.3
    si los reciba, sin tener que adivinar por version."""
    out = []
    for item in arg_list or []:
        if isinstance(item, str):
            out.append(_substitute(item, subs))
        elif isinstance(item, dict):
            if _arg_rules_allowed(item.get("rules")):
                val = item.get("value")
                if isinstance(val, str):
                    out.append(_substitute(val, subs))
                elif isinstance(val, list):
                    out.extend(_substitute(x, subs) for x in val)
    return out

def infer_required_java(data, version):
    """Java que pide cada version. Si el .json lo dice, ese.
    Si no lo dice (1.6.4 y anteriores), es Java 8: son de antes de
    que Mojang pusiera javaVersion en el .json, y con Java 16+ no arrancan."""
    jv = data.get("javaVersion") or {}
    if jv.get("majorVersion"):
        return int(jv["majorVersion"])
    return 8

def is_pre_1_6(version: str) -> bool:
    """Versiones viejas (alpha, beta, 1.0-1.5.2) que no entienden lang:en_us."""
    v = version.strip().lower()
    if v.startswith(("a", "b")):
        return True
    m = re.match(r"1\.(\d+)", v)
    return bool(m and int(m.group(1)) < 6)

def copy_old_sounds(version: str, log=None):
    """Copia los sonidos de las versiones viejas a donde el juego los busca.

    Por que no habia sonido en la 1.0/1.1/1.5.2 aunque ya servian:
    esas versiones NO usan assets/objects como las nuevas, ni solo
    assets/virtual/legacy como la 1.6.4. Su SoundManager busca los
    sonidos en <gameDir>/resources/<ruta>, por ejemplo
    juego/resources/sound3/dig/stone1.ogg, juego/resources/newsound/...,
    juego/resources/music/calm1.ogg.
    El indice pre-1.6 trae esas rutas (sound3, newsound, sound, music,
    newmusic, streaming), y los archivos estan descargados en
    assets/objects/<hash>, pero nadie los copiaba a resources/.
    Por eso el juego arrancaba mudo, sin error: simplemente no
    encontraba ningun sonido.
    La 1.6.4 (indice legacy) si usa assets/virtual/legacy/sounds/...,
    asi que a esa se le copia ahi. A las pre-1.6 se les copia a los
    TRES sitios, para que suene seguro: juego/resources/, assets/
    y assets/virtual/legacy/.
    Devuelve (copiados, faltantes). No descarga nada, solo copia lo
    que ya esta en objects; si faltan muchos, hay que reinstalar.
    """
    copied = 0
    missing = 0
    try:
        data = json.loads(version_json(version).read_text(encoding="utf-8"))
    except Exception:
        return (0, 0)
    ai = data.get("assetIndex", {})
    ai_id = ai.get("id", "")
    if ai_id not in ("pre-1.6", "legacy"):
        return (0, 0)
    ai_path = mc_dir() / "assets" / "indexes" / f"{ai_id}.json"
    if not ai_path.is_file():
        return (0, 0)
    try:
        assets = json.loads(ai_path.read_text(encoding="utf-8"))
    except Exception:
        return (0, 0)
    objects = assets.get("objects", {})
    for name, info in objects.items():
        h = info["hash"]
        src = mc_dir() / "assets" / "objects" / h[:2] / h
        if not src.is_file():
            missing += 1
            continue
        dests = []
        if ai_id == "pre-1.6":
            dests = [
                game_folder(version) / "resources",
                mc_dir() / "assets",
                mc_dir() / "assets" / "virtual" / "legacy",
            ]
        else:  # legacy, 1.6.4
            dests = [mc_dir() / "assets" / "virtual" / "legacy"]
        for base in dests:
            try:
                dest = base.joinpath(*name.split("/"))
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.is_file() or dest.stat().st_size != info["size"]:
                    shutil.copyfile(src, dest)
                    copied += 1
            except Exception:
                pass
    if log:
        log(f"Sonidos copiados: {copied}, faltantes: {missing}")
    return (copied, missing)

def fix_options_lang(version: str):
    """Arregla options.txt para versiones viejas.

    Causa del crash de la 1.1 (y 1.0, 1.5.2...):
    las versiones nuevas (26.3, etc.) escriben en options.txt
    lang:en_us  (todo en minusculas), pero las viejas buscan el
    archivo lang/en_US.lang (con US en mayusculas), no lo encuentran,
    getResourceAsStream devuelve null y new InputStreamReader(null)
    tira NullPointerException en Reader.java:78, justo en la pantalla
    de carga, en abn.a / StringTranslate. No es Java, ni la grafica,
    ni falta de RAM: es solo esa linea. La solucion es lang:en_US.
    """
    if not is_pre_1_6(version):
        return
    # Ahora cada version tiene su propio options.txt en su carpeta
    # juego/, asi que ya no se contamina con el de la 26.3, pero se
    # arregla tambien el viejo de .minecraft por si acaso.
    for opts in (game_folder(version) / "options.txt", mc_dir() / "options.txt"):
        try:
            if not opts.is_file():
                continue
            txt = opts.read_text(encoding="utf-8", errors="ignore")
            fixed = re.sub(r"lang:([a-z]{2})_([a-z]{2})",
                           lambda m: f"lang:{m.group(1)}_{m.group(2).upper()}", txt)
            if fixed != txt:
                opts.write_text(fixed, encoding="utf-8")
        except Exception:
            pass

def build_bat(version: str) -> Path:
    data = {}
    if version_json(version).is_file():
        try:
            data = json.loads(version_json(version).read_text(encoding="utf-8"))
        except Exception:
            data = {}
    main_class = data.get("mainClass", "net.minecraft.client.main.Main")
    asset_index = str(data.get("assetIndex", {}).get("id", "34"))
    # %~dp0 es la carpeta del .bat, o sea Minecrafts/<version>/, asi el
    # .bat funciona aunque muevas toda la carpeta MoonSusX a otro lado.
    # gameDir = Minecrafts/<version>/juego, natives = Minecrafts/<version>/natives
    ndir = "%~dp0natives"
    gdir = "%~dp0juego"

    cp_parts = []
    for lib in data.get("libraries", []):
        if not library_allowed(lib):
            continue
        dl = lib.get("downloads", {})
        art = dl.get("artifact")
        if art and art.get("path"):
            cp_parts.append(f"%APPDATA%\\.minecraft\\libraries\\{art['path'].replace('/', chr(92))}")
        for key in ("natives-windows", "natives-windows-x86", "natives-windows-arm64"):
            nat = dl.get("classifiers", {}).get(key)
            if nat and nat.get("path"):
                cp_parts.append(f"%APPDATA%\\.minecraft\\libraries\\{nat['path'].replace('/', chr(92))}")

    if cp_parts:
        cp_parts.append(f"%APPDATA%\\.minecraft\\versions\\{version}\\{version}.jar")
        classpath = ";".join(cp_parts)
    elif TEMPLATE_BAT.is_file():
        txt = TEMPLATE_BAT.read_text(encoding="utf-8", errors="ignore")
        txt = txt.replace("26.3", version)
        # Si el Java es viejo, quita los flags de Java 24/25 que dan el error de JVM
        _jm = java_major(find_javaw())
        if 0 < _jm < 24:
            for _bad in ("-XX:+UseCompactObjectHeaders ", "--enable-native-access=ALL-UNNAMED ",
                         "--add-exports java.base/jdk.internal.misc=ALL-UNNAMED ",
                         "-XX:+UseZGC ", "-XX:+AlwaysPreTouch ", "-XX:+UseStringDeduplication "):
                txt = txt.replace(_bad, "")
            txt = txt.replace("-Xmx4G", "-Xmx2G")
        txt = txt.rstrip() + "\nif errorlevel 1 (\n  echo.\n  echo ERROR AL INICIAR JAVA - copia el mensaje de arriba y pasamelo\n  pause\n)\n"
        out = version_folder(version) / f"minecraft-{version}.bat"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(txt, encoding="utf-8")
        return out
    else:
        raise FileNotFoundError(f"No encontre {version_json(version)} ni la plantilla minecraft.bat")

    # Java que pide ESA version, no el primero que haya.
    # La 1.0 pide Java 8 (jre-legacy), la 1.16.5/1.12.2 tambien,
    # la 1.21 pide 21, la 26.3 pide 25. Si usas Java 25 con la 1.0,
    # LWJGL 2.9.0 no arranca y sale el error de JVM.
    required_major = infer_required_java(data, version)
    javaw = find_javaw_for(required_major)
    if "AppData\\Local\\" in javaw:
        javaw_bat = javaw.replace(os.environ.get("LOCALAPPDATA", ""), "%LOCALAPPDATA%")
    else:
        javaw_bat = javaw

    jmajor = java_major(javaw)
    if jmajor == 0:
        jmajor = required_major
    jvm_extra = ""
    if jmajor >= 24:
        jvm_extra = "--enable-native-access=ALL-UNNAMED --add-exports java.base/jdk.internal.misc=ALL-UNNAMED -XX:+UseCompactObjectHeaders -XX:+AlwaysPreTouch -XX:+UseStringDeduplication -XX:+UseZGC"
    elif jmajor >= 21:
        jvm_extra = "--enable-native-access=ALL-UNNAMED --add-exports java.base/jdk.internal.misc=ALL-UNNAMED -XX:+UseG1GC"
    elif jmajor >= 17:
        jvm_extra = "-XX:+UseG1GC --add-opens java.base/java.lang=ALL-UNNAMED"
    elif jmajor >= 9:
        jvm_extra = "-XX:+UseG1GC"
    else:
        # Java 8: sin flags modernos, solo CMS como hacia el Launcher viejo
        jvm_extra = "-XX:+UseConcMarkSweepGC -XX:+CMSIncrementalMode"

    # RAM segun la edad: las viejas no necesitan 4 GB, con 1 GB van sobradas
    ram = "-Xms2G -Xmx4G" if required_major >= 17 else "-Xms512M -Xmx1G"
    safe_ram = "-Xms1G -Xmx2G" if required_major >= 17 else "-Xms512M -Xmx1G"

    log_cfg = mc_dir() / "assets" / "log_configs" / "client-1.21.2.xml"
    log_arg = " -Dlog4j.configurationFile=%APPDATA%\\.minecraft\\assets\\log_configs\\client-1.21.2.xml" if log_cfg.is_file() and required_major >= 17 else ""

    # Argumentos del juego: las viejas NO usan --username/--uuid/--accessToken.
    # La 1.0 usa minecraftArguments del .json:
    #   ${auth_player_name} ${auth_session} --gameDir ... --assetsDir ...
    # y su mainClass es LaunchWrapper, que necesita --tweakClass VanillaTweaker.
    # Si le pasas los argumentos modernos, LaunchWrapper falla y sale el error.
    subs = {
        "${auth_player_name}": get_username(),
        "${auth_session}": "null",
        "${game_directory}": gdir,
        "${game_assets}": "%APPDATA%\\.minecraft\\assets",
        "${assets_root}": "%APPDATA%\\.minecraft\\assets",
        "${assets_index_name}": asset_index,
        "${version_name}": version,
        "${auth_uuid}": UUID,
        "${auth_access_token}": "null",
        "${clientid}": CLIENT_ID,
        "${auth_xuid}": XUID,
        "${user_type}": "mojang",
        "${version_type}": str(data.get("type", "release")),
        "${user_properties}": "{}",
        "${resolution_width}": "1024",
        "${resolution_height}": "768",
        "${natives_directory}": ndir,
        "${launcher_name}": "minecraft-launcher",
        "${launcher_version}": "3.42.5",
        "${classpath}": classpath,
        "${library_directory}": "%APPDATA%\\.minecraft\\libraries",
    }
    if data.get("minecraftArguments"):
        tpl = _substitute(data["minecraftArguments"], subs)
        tweak = ""
        if main_class == "net.minecraft.launchwrapper.Launch":
            tweak = "--tweakClass net.minecraft.launchwrapper.VanillaTweaker "
        game_args = f"{main_class} {tweak}{tpl}"
    elif data.get("arguments", {}).get("game"):
        # 1.13 en adelante: usa la lista arguments.game de Mojang tal cual.
        # Asi la 1.13-1.17 no recibe --clientId/--xuid (no existen ahi)
        # y la 1.19+/26.3 si los recibe, sin adivinar por version.
        resolved = resolve_argument_list(data["arguments"]["game"], subs)
        game_args = f"{main_class} " + " ".join(resolved)
    else:
        game_args = (
            f"{main_class} "
            f"--username {get_username()} "
            f"--version {version} "
            f"--gameDir {gdir} "
            "--assetsDir %APPDATA%\\.minecraft\\assets "
            f"--assetIndex {asset_index} "
            f"--uuid {UUID} "
            "--accessToken null "
            f"--clientId {CLIENT_ID} "
            f"--xuid {XUID} "
            "--versionType release "
            "--width 1024 --height 768"
        )
    lines = [
        "@echo off",
    ]
    if is_pre_1_6(version):
        # Arreglo lang:en_us -> lang:en_US en options.txt, tambien si
        # se ejecuta el .bat a mano sin pasar por MoonSusX. Si no se hace,
        # la 1.1/1.0/1.5.2 crashea en la pantalla de carga con
        # NullPointerException en InputStreamReader (Reader.java:78).
        lines.append("REM Arreglo idioma para versiones viejas: lang:en_us -> lang:en_US")
        lines.append("powershell -NoProfile -Command \"$p='%~dp0juego\\options.txt'; if (Test-Path $p) { $t = Get-Content $p -Raw; $t = [regex]::Replace($t, 'lang:([a-z]+)_([a-z]+)', { param($m) 'lang:' + $m.Groups[1].Value + '_' + $m.Groups[2].Value.ToUpper() }); Set-Content $p $t -NoNewline }\"")
    lines += [
        f"{javaw_bat} "
        "-XX:HeapDumpPath=MojangTricksIntelDriversForPerformance_javaw.exe_minecraft.exe.heapdump "
        "-Xss1M -XX:StackShadowPages=32 "
        f"{jvm_extra} "
        f"-Djava.library.path={ndir} "
        f"-Djna.tmpdir={ndir} "
        f"-Dorg.lwjgl.system.SharedLibraryExtractPath={ndir} "
        f"-Dio.netty.native.workdir={ndir} "
        "-Dminecraft.launcher.brand=minecraft-launcher "
        "-Dminecraft.launcher.version=3.42.5 "
        f"-cp {classpath} "
        f"{ram} "
        f"{log_arg} "
        f"{game_args}",
        "if errorlevel 1 (",
        "  echo.",
        "  echo ERROR AL INICIAR JAVA - copia el mensaje de arriba y pasamelo",
        "  pause",
        ")",
    ]
    # El .bat ya no se tira en la raiz de MoonSusX, va en su carpeta:
    # Minecrafts/<version>/minecraft-<version>.bat
    vfolder = version_folder(version)
    vfolder.mkdir(parents=True, exist_ok=True)
    game_folder(version).mkdir(parents=True, exist_ok=True)
    out = vfolder / f"minecraft-{version}.bat"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Bat SEGURO, por si el normal sigue fallando: sin flags raros, 2 GB
    safe_lines = [
        "@echo off",
        "REM Bat seguro de MoonSusX - sin flags de Java 24/25, solo 2 GB de RAM",
        f"{javaw_bat} {safe_ram} "
        f"-Djava.library.path={ndir} "
        f"-cp {classpath} "
        f"{game_args}",
        "if errorlevel 1 (",
        "  echo.",
        "  echo ERROR AL INICIAR JAVA - copia el mensaje de arriba y pasamelo",
        "  pause",
        ")",
    ]
    safe_out = vfolder / f"minecraft-{version}-seguro.bat"
    safe_out.write_text("\n".join(safe_lines) + "\n", encoding="utf-8")
    return out


class MoonSusX(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  -  Minecraft Launcher")
        self.geometry("540x740")
        self.resizable(False, False)
        self.configure(bg="#0b0e1a")
        self._queue = queue.Queue()
        self._installing = False

        tk.Label(self, text="🌙  MoonSusX", font=("Segoe UI", 28, "bold"),
                 bg="#0b0e1a", fg="#f5f5f5").pack(pady=(20, 2))
        self.player_label = tk.Label(self, text=f"Minecraft Java  •  Jugador: {get_username()}",
                 font=("Segoe UI", 10), bg="#0b0e1a", fg="#9aa3c7")
        self.player_label.pack(pady=(0, 14))

        tk.Label(self, text="1. Escoge la version:", font=("Segoe UI", 11, "bold"),
                 bg="#0b0e1a", fg="#f5f5f5").pack()
        # Todas las versiones de Mojang, con filtro por tipo.
        # Al abrir, se cargan las 10 de respaldo y en segundo plano
        # se descarga la lista completa (926 en este momento) y se
        # actualiza el desplegable solo, sin bloquear la ventana.
        self.all_versions = [{"id": v, "type": "release"} for v in KNOWN_VERSIONS]
        # Si ya hay una lista completa guardada (version_manifest.json,
        # que viene incluida en el zip), usala desde el primer segundo,
        # no solo las 10 de respaldo, para que TODAS las versiones
        # esten en el desplegable al abrir, sin esperar a internet.
        try:
            if MANIFEST_CACHE.is_file():
                _cached = json.loads(MANIFEST_CACHE.read_text(encoding="utf-8"))
                if _cached.get("versions"):
                    self.all_versions = _cached["versions"]
        except Exception:
            pass
        self.filter_var = tk.StringVar(value="Todas")
        filter_combo = ttk.Combobox(self, textvariable=self.filter_var,
                                    values=["Release", "Todas", "Snapshot", "Beta antigua", "Alpha antigua", "Instaladas"],
                                    font=("Segoe UI", 10), width=16, state="readonly")
        filter_combo.pack(pady=(2, 2))
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())
        self.count_var = tk.StringVar(value="Cargando todas las versiones...")
        tk.Label(self, textvariable=self.count_var, font=("Segoe UI", 9),
                 bg="#0b0e1a", fg="#9aa3c7").pack()
        # Al abrir ya estan TODAS en el desplegable, no solo las 10
        versions = [v["id"] for v in self.all_versions]
        for v in installed_versions():
            if v not in versions:
                versions.append(v)
        self.version_var = tk.StringVar(value="26.3")
        self.combo = ttk.Combobox(self, textvariable=self.version_var, values=versions,
                             font=("Segoe UI", 12), width=18)
        self.combo.pack(pady=6)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_status())
        self.combo.bind("<FocusOut>", lambda e: self.refresh_status())

        tk.Label(self, text="2. Tu nombre en el juego:", font=("Segoe UI", 11, "bold"),
                 bg="#0b0e1a", fg="#f5f5f5").pack(pady=(6, 0))
        name_frame = tk.Frame(self, bg="#0b0e1a")
        name_frame.pack(pady=6)
        self.username_var = tk.StringVar(value=get_username())
        name_entry = tk.Entry(name_frame, textvariable=self.username_var,
                              font=("Segoe UI", 12), width=18, justify="center")
        name_entry.pack(side="left", padx=(0, 8))
        name_entry.bind("<Return>", lambda e: self.change_name())
        name_entry.bind("<FocusOut>", lambda e: self.change_name())
        tk.Button(name_frame, text="Guardar nombre", font=("Segoe UI", 10, "bold"),
                  bg="#30363d", fg="white", activebackground="#484f58", relief="flat",
                  padx=10, pady=6, cursor="hand2", command=self.change_name).pack(side="left")
        self.name_status_var = tk.StringVar(value="Solo letras, numeros y _, de 3 a 16 caracteres.")
        tk.Label(self, textvariable=self.name_status_var, font=("Segoe UI", 9),
                 bg="#0b0e1a", fg="#9aa3c7").pack()

        self.status_var = tk.StringVar()
        tk.Label(self, textvariable=self.status_var, font=("Segoe UI", 11, "bold"),
                 bg="#0b0e1a", fg="#7ee787", wraplength=480, justify="center").pack(pady=6)

        self.progress = ttk.Progressbar(self, orient="horizontal", length=440, mode="determinate")
        self.progress.pack(pady=4)

        self.btn_install = tk.Button(self, text="⬇  INSTALAR MINECRAFT",
                                     font=("Segoe UI", 13, "bold"), bg="#1f6feb", fg="white",
                                     activebackground="#388bfd", relief="flat", padx=20, pady=14,
                                     cursor="hand2", command=self.install)
        self.btn_install.pack(fill="x", padx=40, pady=(12, 8))

        self.btn_play = tk.Button(self, text="▶  EJECUTAR",
                                  font=("Segoe UI", 15, "bold"), bg="#238636", fg="white",
                                  activebackground="#2ea043", relief="flat", padx=20, pady=16,
                                  cursor="hand2", command=self.play)

        self.btn_folder = tk.Button(self, text="📁  ABRIR CARPETA DE ESTA VERSION",
                                  font=("Segoe UI", 11, "bold"), bg="#30363d", fg="white",
                                  activebackground="#484f58", relief="flat", padx=20, pady=10,
                                  cursor="hand2", command=self.open_folder)

        self.btn_sound = tk.Button(self, text="🔊  REPARAR SONIDO DE ESTA VERSION",
                                  font=("Segoe UI", 11, "bold"), bg="#30363d", fg="white",
                                  activebackground="#484f58", relief="flat", padx=20, pady=10,
                                  cursor="hand2", command=self.repair_sound)

        tk.Label(self, text="Instalar descarga la version de Mojang, sin abrir paginas.\nEjecutar crea el .bat para esa version y te manda a jugar.\nCada version queda en su carpeta: Minecrafts/<version>/ con su .bat,\nsu carpeta juego/ (saves, options) y sus natives.",
                 font=("Segoe UI", 9), bg="#0b0e1a", fg="#6b7280",
                 justify="center").pack(pady=12)

        self.apply_filter()
        self.refresh_status()
        self.after(100, self._drain_queue)
        threading.Thread(target=self._load_versions_bg, daemon=True).start()

    def _load_versions_bg(self):
        self.all_versions = fetch_all_versions()
        self._queue.put(("versions", len(self.all_versions)))

    def apply_filter(self):
        kind = self.filter_var.get()
        current = self.version_var.get().strip()
        values = filter_versions(self.all_versions, kind)
        # Las instaladas siempre tienen que aparecer, aunque el filtro no las traiga
        for v in installed_versions():
            if v not in values:
                values.append(v)
        self.combo["values"] = values
        n = len(self.all_versions)
        counts = {}
        for v in self.all_versions:
            counts[v.get("type", "?")] = counts.get(v.get("type", "?"), 0) + 1
        self.count_var.set(
            f"{n} versiones en total: {counts.get('release', 0)} release, "
            f"{counts.get('snapshot', 0)} snapshot, {counts.get('old_beta', 0)} beta, "
            f"{counts.get('old_alpha', 0)} alpha  •  Mostrando: {len(values)} ({kind})"
        )
        if current not in values:
            self.version_var.set(values[0] if values else current)
        self.refresh_status()

    def _drain_queue(self):
        try:
            while True:
                kind, value = self._queue.get_nowait()
                if kind == "versions":
                    self.apply_filter()
                elif kind == "log":
                    self.status_var.set(value)
                elif kind == "progress":
                    self.progress["value"] = value * 100
                elif kind == "done":
                    self._installing = False
                    self.btn_install.config(state="normal")
                    self.progress["value"] = 100
                    self.refresh_status()
                    if value:
                        messagebox.showinfo(APP_NAME, value)
                elif kind == "error":
                    self._installing = False
                    self.btn_install.config(state="normal")
                    messagebox.showerror(APP_NAME, value)
                    self.refresh_status()
        except queue.Empty:
            pass
        self.after(100, self._drain_queue)

    def selected_version(self) -> str:
        return self.version_var.get().strip()

    def refresh_status(self):
        if self._installing:
            return
        v = self.selected_version()
        if not v:
            self.status_var.set("Escoge una version arriba.")
            self.btn_play.pack_forget()
            return
        if is_installed(v):
            self.status_var.set(f"✅ Minecraft {v} ya esta instalado\nYa puedes pulsar EJECUTAR\nCarpeta: Minecrafts/{v}/")
            self.btn_play.pack(fill="x", padx=40, pady=8)
            self.btn_folder.pack(fill="x", padx=40, pady=(0, 8))
            self.btn_sound.pack(fill="x", padx=40, pady=(0, 8))
        else:
            self.status_var.set(f"⚠️ Minecraft {v} todavia no esta instalado\nPulsa INSTALAR MINECRAFT, se descarga solo")
            self.btn_play.pack_forget()
            self.btn_folder.pack_forget()
            self.btn_sound.pack_forget()

    def change_name(self):
        name = save_username(self.username_var.get())
        self.username_var.set(name)
        self.player_label.config(text=f"Minecraft Java  •  Jugador: {name}")
        self.name_status_var.set(f"Nombre guardado: {name}. Ya se usara en el proximo EJECUTAR.")
        self.refresh_status()

    def repair_sound(self):
        v = self.selected_version()
        if not is_installed(v):
            messagebox.showwarning(APP_NAME, f"Minecraft {v} todavia no esta instalado.")
            return
        copied, missing = copy_old_sounds(v)
        if copied == 0 and missing == 0:
            messagebox.showinfo(APP_NAME, f"Minecraft {v} no es version vieja, su sonido ya va por assets/objects.\nSi no se oye, revisa el volumen en Opciones > Musica y sonidos.")
        elif missing > 50:
            messagebox.showwarning(APP_NAME, f"Copie {copied} sonidos, pero faltan {missing} archivos en assets/objects.\nVuelve a pulsar INSTALAR para que se descarguen, y luego REPARAR SONIDO otra vez.")
        else:
            messagebox.showinfo(APP_NAME, f"Sonido reparado para Minecraft {v}.\nCopie {copied} archivos a juego/resources/ y a assets/virtual/legacy/.\nFaltantes: {missing}. Ya deberia sonar.")
        self.refresh_status()

    def open_folder(self):
        v = self.selected_version()
        folder = version_folder(v)
        folder.mkdir(parents=True, exist_ok=True)
        game_folder(v).mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(str(folder))
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as e:
            messagebox.showinfo(APP_NAME, f"La carpeta es:\n{folder}\n\n{e}")

    def install(self):
        v = self.selected_version()
        if not v:
            messagebox.showwarning(APP_NAME, "Escoge una version primero.")
            return
        if is_installed(v):
            self.refresh_status()
            return
        if self._installing:
            return
        self._installing = True
        self.btn_install.config(state="disabled")
        self.btn_play.pack_forget()
        self.progress["value"] = 0

        def log(msg):
            self._queue.put(("log", msg))
        def prog(f):
            self._queue.put(("progress", f))
        def worker():
            try:
                install_version(v, log, prog)
                self._queue.put(("done", f"Minecraft {v} instalado.\nYa te salio el boton EJECUTAR."))
            except Exception as e:
                self._queue.put(("error", f"No pude instalar Minecraft {v}:\n{e}\n\nRevisa tu internet y vuelve a intentar."))
        threading.Thread(target=worker, daemon=True).start()

    def play(self):
        v = self.selected_version()
        if not is_installed(v):
            messagebox.showwarning(APP_NAME, f"Minecraft {v} todavia no esta instalado.\nPulsa INSTALAR primero.")
            self.refresh_status()
            return
        try:
            # Antes de lanzar: si es version vieja, arregla lang:en_us -> en_US
            # en options.txt, si no crashea en la pantalla de carga.
            fix_options_lang(v)
            # Y copia los sonidos a juego/resources/ si es pre-1.6,
            # para que no arranque mudo aunque ya estuviera instalada.
            copy_old_sounds(v)
            bat = build_bat(v)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"No pude crear el .bat para {v}:\n{e}")
            return
        try:
            subprocess.Popen(
                ["cmd", "/c", str(bat)],
                cwd=str(bat.parent),
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
            )
            self.status_var.set(f"🎮 Ejecutando Minecraft {v}...\nCarpeta: Minecrafts/{v}/  •  Bat: {bat.name}")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"No pude ejecutar el .bat:\n{e}\n\nEl .bat ya quedo creado en:\n{bat}")

if __name__ == "__main__":
    app = MoonSusX()
    app.mainloop()
