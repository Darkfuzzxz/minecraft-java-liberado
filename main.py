#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
MoonSusX v3.1 - Launcher para Minecraft Java
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
APP_NAME = "MoonSusX"
VERSION = "0.0.1"
UUID = "db8a8821c02ee7b99473b310d1ef3def"
CLIENT_ID = "MzY1NjI1MGMtNjhhMi00Mjg0LWFlZjctYzk0NTExZDFhMDgy"
XUID = "2535451888961759"
MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_BAT = BASE_DIR / "minecraft.bat"

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
    return mc_dir() / "bin" / f"{version}-natives"

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

def find_javaw():
    # 1. Java descargado por MoonSusX
    local = BASE_DIR / "java-runtime" / "bin" / "javaw.exe"
    if local.is_file():
        return str(local)
    # 2. Runtime oficial del Launcher, como en tu .bat original
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Packages" / "Microsoft.4297127D64EC6_8wekyb3d8bbwe" / "LocalCache" / "Local" / "runtime"
    try:
        for runtime in sorted(base.glob("java-runtime-*"), reverse=True):
            for javaw in runtime.rglob("bin/javaw.exe"):
                return str(javaw)
    except Exception:
        pass
    try:
        for javaw in sorted((mc_dir() / "runtime").rglob("bin/javaw.exe"), reverse=True):
            return str(javaw)
    except Exception:
        pass
    return "javaw.exe"

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
    """Si no hay Java, lo descarga dentro de la app (Temurin JRE, sin abrir paginas)."""
    if find_javaw() != "javaw.exe":
        return
    log(f"Descargando Java {major} para poder jugar...")
    dest = BASE_DIR / "java-runtime.zip"
    url = f"https://api.adoptium.net/v3/binary/latest/{major}/ga/windows/x64/jre/hotspot/normal/eclipse"
    try:
        download(url, dest)
        target = BASE_DIR / "java-runtime"
        if target.exists():
            shutil.rmtree(target)
        with zipfile.ZipFile(dest) as z:
            z.extractall(BASE_DIR / "_java_tmp")
        # Temurin viene en una carpeta jdk-<version>-jre
        inner = next((BASE_DIR / "_java_tmp").iterdir())
        shutil.move(str(inner), str(target))
        shutil.rmtree(BASE_DIR / "_java_tmp", ignore_errors=True)
        dest.unlink(missing_ok=True)
        log("Java descargado.")
    except Exception as e:
        log(f"No pude descargar Java automaticamente: {e}. Instala Java 21+ y vuelve a intentar.")

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

    # Java
    major = int(data.get("javaVersion", {}).get("majorVersion", 21))
    ensure_java(major, log)
    progress(1.0)
    log(f"Minecraft {version} instalado.")

def build_bat(version: str) -> Path:
    data = {}
    if version_json(version).is_file():
        try:
            data = json.loads(version_json(version).read_text(encoding="utf-8"))
        except Exception:
            data = {}
    main_class = data.get("mainClass", "net.minecraft.client.main.Main")
    asset_index = str(data.get("assetIndex", {}).get("id", "34"))
    ndir = f"%APPDATA%\\.minecraft\\bin\\{version}-natives"

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
        out = BASE_DIR / f"minecraft-{version}.bat"
        out.write_text(txt, encoding="utf-8")
        return out
    else:
        raise FileNotFoundError(f"No encontre {version_json(version)} ni la plantilla minecraft.bat")

    javaw = find_javaw()
    if "AppData\\Local\\" in javaw:
        javaw_bat = javaw.replace(os.environ.get("LOCALAPPDATA", ""), "%LOCALAPPDATA%")
    else:
        javaw_bat = javaw

    # --- ARREGLO ERROR DE JAVA VIRTUAL MACHINE ---
    # Tu .bat original usa flags que solo entiende Java 24/25:
    #   -XX:+UseCompactObjectHeaders, --enable-native-access, -XX:+UseZGC
    # Si MoonSusX agarra un Java viejo (17, 21...), Java se cierra con
    # "Could not create the Java Virtual Machine" / "Unrecognized VM option".
    # Por eso ahora detectamos la version de Java y quitamos esos flags
    # si ese Java no los entiende. La 26.3 necesita Java 25, asi que si
    # no tienes Java 25, el instalador descarga uno dentro de la app.
    jmajor = java_major(javaw)
    # Si no pudimos detectar la version, asumimos Java nuevo (25) como antes
    if jmajor == 0:
        jmajor = 25
    jvm_extra = ""
    if jmajor >= 24:
        jvm_extra = "--enable-native-access=ALL-UNNAMED --add-exports java.base/jdk.internal.misc=ALL-UNNAMED -XX:+UseCompactObjectHeaders -XX:+AlwaysPreTouch -XX:+UseStringDeduplication -XX:+UseZGC"
    elif jmajor >= 21:
        jvm_extra = "--enable-native-access=ALL-UNNAMED --add-exports java.base/jdk.internal.misc=ALL-UNNAMED -XX:+UseG1GC"
    else:
        jvm_extra = "-XX:+UseG1GC"

    log_cfg = mc_dir() / "assets" / "log_configs" / "client-1.21.2.xml"
    log_arg = " -Dlog4j.configurationFile=%APPDATA%\\.minecraft\\assets\\log_configs\\client-1.21.2.xml" if log_cfg.is_file() else ""

    game_args = (
        f"{main_class} "
        f"--username {USERNAME} "
        f"--version {version} "
        "--gameDir %APPDATA%\\.minecraft "
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
        "-Xms2G -Xmx4G "
        f"{log_arg} "
        f"{game_args}",
        "if errorlevel 1 (",
        "  echo.",
        "  echo ERROR AL INICIAR JAVA - copia el mensaje de arriba y pasamelo",
        "  pause",
        ")",
    ]
    out = BASE_DIR / f"minecraft-{version}.bat"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (BASE_DIR / "minecraft.bat").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Bat SEGURO, por si el normal sigue fallando: sin flags raros, 2 GB
    safe_lines = [
        "@echo off",
        "REM Bat seguro de MoonSusX - sin flags de Java 24/25, solo 2 GB de RAM",
        f"{javaw_bat} -Xms1G -Xmx2G "
        f"-Djava.library.path={ndir} "
        f"-cp {classpath} "
        f"{game_args}",
        "if errorlevel 1 (",
        "  echo.",
        "  echo ERROR AL INICIAR JAVA - copia el mensaje de arriba y pasamelo",
        "  pause",
        ")",
    ]
    safe_out = BASE_DIR / f"minecraft-{version}-seguro.bat"
    safe_out.write_text("\n".join(safe_lines) + "\n", encoding="utf-8")
    return out


class MoonSusX(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  -  Minecraft Launcher")
        self.geometry("540x540")
        self.resizable(False, False)
        self.configure(bg="#0b0e1a")
        self._queue = queue.Queue()
        self._installing = False

        tk.Label(self, text="🌙  MoonSusX", font=("Segoe UI", 28, "bold"),
                 bg="#0b0e1a", fg="#f5f5f5").pack(pady=(20, 2))
        tk.Label(self, text=f"Minecraft Java  •  Jugador: {USERNAME}",
                 font=("Segoe UI", 10), bg="#0b0e1a", fg="#9aa3c7").pack(pady=(0, 14))

        tk.Label(self, text="1. Escoge la version:", font=("Segoe UI", 11, "bold"),
                 bg="#0b0e1a", fg="#f5f5f5").pack()
        versions = list(dict.fromkeys(KNOWN_VERSIONS + installed_versions()))
        self.version_var = tk.StringVar(value="26.3")
        combo = ttk.Combobox(self, textvariable=self.version_var, values=versions,
                             font=("Segoe UI", 12), width=18)
        combo.pack(pady=6)
        combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_status())
        combo.bind("<FocusOut>", lambda e: self.refresh_status())

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

        tk.Label(self, text="Instalar descarga la version de Mojang, sin abrir paginas.\nEjecutar crea el .bat para esa version y te manda a jugar.",
                 font=("Segoe UI", 9), bg="#0b0e1a", fg="#6b7280",
                 justify="center").pack(pady=12)

        self.refresh_status()
        self.after(100, self._drain_queue)

    def _drain_queue(self):
        try:
            while True:
                kind, value = self._queue.get_nowait()
                if kind == "log":
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
            self.status_var.set(f"✅ Minecraft {v} ya esta instalado\nYa puedes pulsar EJECUTAR")
            self.btn_play.pack(fill="x", padx=40, pady=8)
        else:
            self.status_var.set(f"⚠️ Minecraft {v} todavia no esta instalado\nPulsa INSTALAR MINECRAFT, se descarga solo")
            self.btn_play.pack_forget()

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
            bat = build_bat(v)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"No pude crear el .bat para {v}:\n{e}")
            return
        try:
            subprocess.Popen(
                ["cmd", "/c", str(bat)],
                cwd=str(BASE_DIR),
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
            )
            self.status_var.set(f"🎮 Ejecutando Minecraft {v}...\nBat creado: {bat.name}")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"No pude ejecutar el .bat:\n{e}\n\nEl .bat ya quedo creado en:\n{bat}")

if __name__ == "__main__":
    app = MoonSusX()
    app.mainloop()
