"""
bandeja.py — Icono en la bandeja del sistema para el Centinela del Tiempo.

Menú de clic derecho:
    · Pausar / Reanudar   -> congela la vigilancia sin matar el proceso
    · Ver tiempo de hoy   -> notificación con el ocio acumulado del día
    · Salir               -> cierra la aplicación de verdad (adiós a 'Stop-Process')

Además guarda el ocio del día en disco (datos/ocio_hoy.json) para que el
contador sobreviva a reinicios, y cierra cada día en datos/registro.csv
(fecha,segundos_ocio) — listo para el futuro dashboard con pandas.

Requiere:  pip install pystray pillow
"""

import json
import os
import threading
import time
from datetime import date

import pystray
from PIL import Image, ImageDraw

# --- Rutas de datos (junto a este archivo / la raíz del proyecto) ---
CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos")
ARCHIVO_HOY = os.path.join(CARPETA, "ocio_hoy.json")
ARCHIVO_LOG = os.path.join(CARPETA, "registro.csv")
INTERVALO_GUARDADO = 15  # segundos mínimos entre escrituras a disco


class Estado:
    """Estado compartido entre el bucle de vigilancia y el icono de bandeja."""

    def __init__(self):
        self._pausa = threading.Event()        # set() = pausado
        self._lock = threading.Lock()
        self._dia = date.today()
        self._segundos = 0.0
        self._ultimo_guardado = 0.0
        os.makedirs(CARPETA, exist_ok=True)
        self._cargar()

    # ---------------------------- PAUSA ----------------------------
    @property
    def pausado(self):
        return self._pausa.is_set()

    def alternar_pausa(self):
        if self._pausa.is_set():
            self._pausa.clear()
        else:
            self._pausa.set()

    # ------------------------ OCIO DEL DÍA -------------------------
    def sumar_ocio(self, segundos):
        """Suma los segundos de ocio de este ciclo. Llámalo desde tu bucle."""
        with self._lock:
            self._rollover_si_cambia_dia()
            self._segundos += segundos
            ahora = time.time()
            if ahora - self._ultimo_guardado >= INTERVALO_GUARDADO:
                self._guardar_hoy()
                self._ultimo_guardado = ahora

    @property
    def segundos_hoy(self):
        with self._lock:
            self._rollover_si_cambia_dia()
            return self._segundos

    # ----------------------- PERSISTENCIA --------------------------
    def _cargar(self):
        try:
            with open(ARCHIVO_HOY, encoding="utf-8") as f:
                d = json.load(f)
        except (FileNotFoundError, ValueError, json.JSONDecodeError):
            return
        dia_guardado = d.get("dia")
        segundos = float(d.get("segundos", 0))
        if dia_guardado == date.today().isoformat():
            self._segundos = segundos          # retomamos el día en curso
        elif dia_guardado:                     # el día guardado ya pasó: lo cerramos
            try:
                self._anexar_log(date.fromisoformat(dia_guardado), segundos)
            except ValueError:
                pass

    def _guardar_hoy(self):
        tmp = ARCHIVO_HOY + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"dia": self._dia.isoformat(),
                       "segundos": round(self._segundos, 1)}, f)
        os.replace(tmp, ARCHIVO_HOY)           # escritura atómica

    def _rollover_si_cambia_dia(self):
        hoy = date.today()
        if hoy != self._dia:
            self._anexar_log(self._dia, self._segundos)   # cierra el día anterior
            self._dia = hoy
            self._segundos = 0.0
            self._guardar_hoy()

    def _anexar_log(self, dia, segundos):
        nuevo = not os.path.exists(ARCHIVO_LOG)
        with open(ARCHIVO_LOG, "a", encoding="utf-8", newline="") as f:
            if nuevo:
                f.write("fecha,segundos_ocio\n")
            f.write(f"{dia.isoformat()},{round(segundos, 1)}\n")

    def cerrar(self):
        """Vuelca a disco antes de salir."""
        with self._lock:
            self._guardar_hoy()


estado = Estado()


# ------------------------- ICONO Y MENÚ ----------------------------
def _crear_icono():
    """Dibuja un ojo sencillo (tema 'centinela', iris rosa) de 64x64."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 20, 60, 44), fill=(248, 248, 250, 255),
              outline=(45, 45, 55, 255), width=2)          # almendra
    d.ellipse((23, 21, 41, 43), fill=(230, 90, 160, 255))  # iris rosa
    d.ellipse((28, 27, 36, 37), fill=(25, 25, 30, 255))    # pupila
    d.ellipse((29, 28, 33, 32), fill=(255, 255, 255, 230)) # brillo
    return img


def _formato(segundos):
    segundos = int(segundos)
    h, resto = divmod(segundos, 3600)
    m, s = divmod(resto, 60)
    if h:
        return f"{h} h {m} min"
    if m:
        return f"{m} min {s} s"
    return f"{s} s"


def _construir_icono():
    def texto_pausa(item):
        return "Reanudar" if estado.pausado else "Pausar"

    def on_pausa(icon, item):
        estado.alternar_pausa()
        icon.update_menu()

    def on_tiempo(icon, item):
        icon.notify(f"Ocio de hoy: {_formato(estado.segundos_hoy)}",
                    "Centinela del Tiempo")

    def on_salir(icon, item):
        estado.cerrar()
        icon.stop()
        os._exit(0)   # garantiza el cierre aunque haya un diálogo abierto

    menu = pystray.Menu(
        pystray.MenuItem(texto_pausa, on_pausa),
        pystray.MenuItem("Ver tiempo de hoy", on_tiempo),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Salir", on_salir),
    )
    return pystray.Icon("centinela", _crear_icono(),
                        "Centinela del Tiempo", menu=menu)


def iniciar():
    """
    Muestra el icono en la bandeja en su propio hilo (no bloquea).
    Llámalo ANTES de tu 'while True' para que tu bucle y tus diálogos de
    tkinter sigan en el hilo principal.
    """
    icon = _construir_icono()
    icon.run_detached()
    return icon


# --------------------------- PRUEBA RÁPIDA --------------------------
if __name__ == "__main__":
    # Ejecuta:  python bandeja.py
    # Verás el icono en la bandeja; simula 1 s de ocio por segundo.
    def _fake():
        while True:
            if not estado.pausado:
                estado.sumar_ocio(1)
            time.sleep(1)

    threading.Thread(target=_fake, daemon=True).start()
    _construir_icono().run()   # bloqueante; usa "Salir" para terminar