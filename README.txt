MoonSusX v0.0.8 - Minecraft Java
Version 0.0.8
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
   Ahora trae TODAS las versiones de Mojang, no solo 10:
   926 en total (103 release, 762 snapshot, 26 beta antigua,
   35 alpha antigua). Usa el filtro de arriba para cambiar
   entre Release / Todas / Snapshot / Beta / Alpha / Instaladas.
   La lista se descarga de piston-meta.mojang.com al abrir,
   y se guarda en version_manifest.json por si no hay internet.
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


V0.0.3 - ARREGLO VERSIONES VIEJAS (1.0, 1.12.2, 1.16.5...)
------------------------------------------------------------
La 1.0 pedia Java 8 y usaba LaunchWrapper, no los argumentos
modernos. Antes MoonSusX le pasaba Java 21/25 y --username/--uuid,
y por eso salia ERROR AL INICIAR JAVA. Ahora:
  - Busca el Java que pide CADA version (8 para la 1.0, 21/25 para las nuevas)
    y si no lo tienes lo descarga en java-runtime-<version>.
  - Para versiones con minecraftArguments en su .json, usa esos
    argumentos tal cual, con --tweakClass VanillaTweaker si hace falta.
  - Sin flags modernos en Java 8, y solo 512M/1G de RAM en viejas.
Si te vuelve a salir el error, copia el mensaje DE ARRIBA del todo,
no solo el de 'ERROR AL INICIAR JAVA', y pasamelo.


V0.0.4 - COMPATIBLE CON TODOS LOS MINECRAFT
------------------------------------------------
Ya no hay un .bat fijo para todas las versiones. Ahora MoonSusX
lee el .json de CADA version y arma el .bat como lo haria el
Launcher oficial:
  - Java que pide cada version: 8 para alpha/beta/1.0-1.16.5,
    16 para la 1.17 (con respaldo a 17 si no se descarga),
    17 para 1.18-1.20, 21 para 1.21, 25 para 26.x.
    Si no tienes ese Java, lo descarga en java-runtime-<version>.
  - Argumentos del juego: minecraftArguments para las viejas
    (LaunchWrapper + VanillaTweaker en 1.0/beta/alpha),
    arguments.game de Mojang para 1.13 en adelante, asi la
    1.13-1.17 no recibe --clientId/--xuid y la 1.19+ si.
  - Assets viejos: legacy/pre-1.6 se copian tambien a
    assets/virtual/legacy, si no, no hay sonidos ni texturas.
Probado generando el .bat de 15 versiones: a1.2.6, b1.8.1, 1.0,
1.6.4, 1.7.10, 1.8.9, 1.12.2, 1.13.2, 1.16.5, 1.17.1, 1.19.4,
1.20.1, 1.21.1, 26.3 y 26.4-pre-1, todas con su Java y sus
argumentos correctos.


V0.0.5 - ARREGLO CRASH 1.1 / 1.0 / 1.5.2 EN LA PANTALLA DE CARGA
--------------------------------------------------------------------
Las versiones nuevas escriben lang:en_us en options.txt, pero las
viejas buscan lang/en_US.lang y crashean con NullPointerException
en InputStreamReader (Reader.java:78). No es Java ni la grafica.
MoonSusX ahora, al ejecutar una version anterior a la 1.6, cambia
lang:en_us -> lang:en_US en options.txt, en Python y tambien en
el .bat con PowerShell, por si ejecutas el .bat a mano.
Si ya te crasheo, tambien lo puedes arreglar a mano: abre
%APPDATA%\.minecraft\options.txt y cambia lang:en_us por lang:en_US,
o borra options.txt y el juego lo crea de nuevo.


V0.0.6 - CARPETAS ORGANIZADAS POR MINECRAFT
----------------------------------------------
Ya no se tiran .bat sueltos en la raiz de MoonSusX. Ahora cada
version tiene su carpeta:
  MoonSusX/Minecrafts/<version>/
    minecraft-<version>.bat
    minecraft-<version>-seguro.bat
    juego/      <- options.txt, saves, screenshots de ESA version
    natives/    <- DLLs nativas de ESA version
Asi cada Minecraft tiene su options, sus mundos y su ejecutable,
y ya no se mezclan (eso tambien arregla el crash de idioma de la
1.1, porque la 1.1 ya no ve el options.txt de la 26.3).
Lo compartido sigue en %APPDATA%\.minecraft (librerias, assets,
.jar y .json), porque muchas versiones comparten lo mismo y no
tiene sentido duplicar 500 MB por version.
En la ventana hay un boton ABRIR CARPETA DE ESTA VERSION.
Los .bat viejos que quedaron en la raiz ya no se usan, los puedes
borrar.


V0.0.7 - SONIDO EN VERSIONES VIEJAS + CAMBIAR NOMBRE
---------------------------------------------------------
SONIDO: la 1.0/1.1/1.5.2 no usan assets/objects, buscan los
sonidos en juego/resources/ (sound3, newsound, music...).
MoonSusX ahora los copia ahi al instalar y tambien al ejecutar,
para que no arranque mudo aunque ya estuviera instalada.
Tambien hay un boton REPARAR SONIDO DE ESTA VERSION, que copia
los sonidos y te dice cuantos faltan. Si faltan muchos, vuelve a
pulsar INSTALAR para descargarlos.
La 1.6.4 sigue usando assets/virtual/legacy/sounds/...
NOMBRE: en la ventana, punto 2, escribe tu nombre y pulsa
Guardar nombre (o Enter). Solo letras, numeros y _, 3 a 16
caracteres. Se guarda en username.txt y se usa en el proximo
EJECUTAR, en todas las versiones. Por defecto elplayergod.


V0.0.8 - TODAS LAS VERSIONES DESDE QUE ABRES
--------------------------------------------------
Tienes razon, al abrir solo se veian las 10 de respaldo y el
filtro estaba en Release, asi que las snapshot, beta y alpha
no se veian hasta que cargaba internet.
Ahora: el filtro por defecto es Todas, y el zip ya trae la lista
completa guardada en version_manifest.json (926 versiones:
103 release, 762 snapshot, 26 beta antigua, 35 alpha antigua),
asi que al abrir ya estan TODAS en el desplegable, sin esperar.
Puedes escribir el nombre de la version en el desplegable o
usar el filtro: Release, Todas, Snapshot, Beta antigua,
Alpha antigua, Instaladas.
