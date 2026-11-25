MoonSusX v0.0.1 - Minecraft Java
Version 0.0.1
============================
Hecho para axel / elplayergod

QUE ES
------
Un launcher con 2 botones, en este orden:
  1. INSTALAR MINECRAFT
  2. EJECUTAR (solo sale cuando la version ya esta instalada)

COMO USARLO EN WINDOWS
-----------------------
1. Descomprime MoonSusX.zip en una carpeta.
2. Doble clic a MoonSusX.bat (necesitas Python 3.10+ en Windows)
3. Escoge la version, por defecto 26.3.
4. Pulsa INSTALAR MINECRAFT

   NO te manda a ninguna pagina ni abre el Launcher.
   MoonSusX se conecta solo a los servidores oficiales de Mojang,
   los mismos que usa el Launcher oficial:
     piston-meta.mojang.com
     piston-data.mojang.com
     libraries.minecraft.net
   Y descarga gratis, en tu PC:
     - <version>.json y <version>.jar
     - librerias para Windows + natives
     - assets (texturas, sonidos, etc., unos 487 MB en la 26.3)
     - configuracion de logs
     - Java, si no tienes uno (se descarga dentro de la app)
   Todo queda en %APPDATA%\.minecraft, como lo deja el Launcher oficial.
   Veras la barra de progreso mientras descarga. No cierres la ventana.

   Para que todo funcione necesitas tener Minecraft / el Launcher
   oficial instalado en tu PC, pero MoonSusX no te abre su ventana:
   descarga el solo.

5. Cuando termina, te aparece el boton EJECUTAR.
6. Pulsa EJECUTAR
   - MoonSusX CREA un .bat para esa version: minecraft-<version>.bat
     Lo genera leyendo el <version>.json oficial
     (mainClass, assetIndex, librerias, natives de Windows),
     con las mismas lineas que tu .bat original:
       @echo off
       javaw.exe del runtime oficial / Java descargado
       -Xms2G -Xmx4G, -XX:+UseZGC, etc.
       --username elplayergod
       --version <version>
       --gameDir %APPDATA%\.minecraft
       --assetsDir %APPDATA%\.minecraft\assets
       --assetIndex <el de esa version>
       --uuid db8a8821c02ee7b99473b310d1ef3def
       --accessToken null
       --clientId MzY1NjI1MGMtNjhhMi00Mjg0LWFlZjctYzk0NTExZDFhMDgy
       --xuid 2535451888961759
       --versionType release
       --width 1024 --height 768
   - Luego ejecuta ese .bat y te manda a jugar.
   - El .bat queda guardado en la carpeta, lo puedes abrir y ver.

PARA HACER UN .EXE (opcional)
-----------------------------
  pip install pyinstaller
  pyinstaller --onefile --windowed --name MoonSusX main.py
Copia minecraft.bat junto al .exe.
