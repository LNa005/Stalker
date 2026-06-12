# -*- coding: utf-8 -*-
"""
Centinela del Tiempo
--------------------
Vigila en segundo plano qué ventana tienes activa. Si acumulas demasiado
tiempo de ocio, te susurra primero y, si insistes, te cuestiona con un
diálogo con pinta de error de Windows. De madrugada te invita a descansar.

Requisitos:  pip install pywin32 psutil
Ejecutar:    python centineladeltiempo.py
En silencio: pythonw centineladeltiempo.py   (sin consola)
"""

import time
import random
from datetime import datetime, time as dtime

import psutil
import win32gui
import win32process
import win32api
import winsound
import tkinter as tk

# ============================================================
#  CONFIGURACIÓN  ·  edita esto a tu gusto
# ============================================================

INTERVALO = 5            # segundos entre comprobaciones
UMBRAL_SUSURRO = 5 * 60      # ocio neto antes del primer aviso suave   (normal: 25*60)
UMBRAL_DIALOGO = 10 * 60     # ocio neto antes de que te cuestione       (normal: 50*60)
AFK_LIMITE = 3 * 60      # sin teclado/ratón este tiempo = estás ausente

# El tiempo productivo descuenta ocio a este ritmo (2 = lo resta el doble de rápido)
DESCUENTO_PRODUCTIVO = 2

# Ventana nocturna: dentro de este horario te invita a dormir aunque no sea ocio
NOCHE_INICIO = dtime(23, 30)
NOCHE_FIN = dtime(5, 0)
NOCHE_REPETIR = 45 * 60   # cada cuánto puede volver a insistir de noche

# --- Clasificación (todo en minúsculas) ---
# Por título de ventana: ideal para el navegador (YouTube vs StackOverflow)
OCIO_TITULOS = [
    "youtube", "netflix", "twitch", "tiktok", "instagram", "reddit",
    "9gag", "disney", "prime video", "hbo", "max", "twitter", "x.com",
    "facebook", "pinterest", "9animes", "crunchyroll",
]
PRODUCTIVO_TITULOS = [
    "visual studio code", "stack overflow", "stackoverflow", "github",
    "gitlab", "documentation", "docs", "localhost", "mdn", "vite",
    "phaser", "python", "java", "moodle",
]

# Por proceso (nombre del .exe)
OCIO_PROCESOS = {
    "vlc.exe",
    # añade tus juegos aquí, ej: "factorio.exe", "stardew valley.exe"
}
PRODUCTIVO_PROCESOS = {
    "code.exe", "windowsterminal.exe", "powershell.exe", "pwsh.exe",
    "cmd.exe", "python.exe", "pythonw.exe", "pycharm64.exe", "idea64.exe",
    "mysqlworkbench.exe", "laragon.exe",
}

# ============================================================
#  MENSAJES  ·  el tono cuestionador, edítalos con tu voz
# ============================================================

SUSURROS = [
    "Llevas un rato aquí. ¿Sigue mereciendo la pena?",
    "Una pausa consciente: ¿esto te acerca a donde quieres estar?",
    "El tiempo no avisa cuando se va. Yo sí.",
    "¿Estás eligiendo este rato, o solo dejándote llevar por él?",
    "Recuerda por qué empezaste el día. ¿Vas hacia allí?",
]

PREGUNTAS = [
    ("Un momento",
     "Llevas casi una hora seguida de ocio.\n\n"
     "¿Es esto lo que tu yo de mañana habría elegido por ti?"),
    ("Una pregunta honesta",
     "Si dentro de un año recordaras esta tarde,\n"
     "¿te alegrarías de cómo la pasaste?"),
    ("Solo por curiosidad",
     "¿Qué estabas a punto de hacer antes de abrir esto?\n\n"
     "Quizá todavía te está esperando."),
    ("Tu tiempo",
     "El descanso es valioso. La distracción disfrazada de descanso, no.\n\n"
     "¿Cuál de los dos es este?"),
]

NOCTURNOS = [
    ("Es tarde",
     "Pasa de las 23:30.\n\n"
     "Descansar también es una forma de respeto hacia ti misma.\n"
     "¿Lo dejamos por hoy?"),
    ("La noche",
     "Mañana hay otra Ele esperando, y dependerá de cómo duermas hoy.\n\n"
     "¿Le regalas un buen descanso?"),
    ("Hora de parar",
     "Lo que hagas ahora cansada, lo harás mejor mañana despierta.\n\n"
     "Ve a dormir."),
]

# Respuestas bordes cuando le contestas por teclado (edítalas a tu gusto)
REPLICAS = [
    "Déjate de rollos.",
    "Así no vas a ser nadie en la vida.",
    "No me cuentes batallas.",
    "Eso se lo cuentas a otra.",
    "Ya, claro. Y yo me lo creo.",
    "Lo mismo dijiste hace una hora.",
    "Menos hablar y más cerrar pestañas.",
    "excusas.exe ha dejado de funcionar.",
    "Error 403: tu excusa no tiene permisos.",
]

# ============================================================
#  DETECCIÓN
# ============================================================

def ventana_activa():
    """Devuelve (proceso_en_minusculas, titulo_en_minusculas)."""
    hwnd = win32gui.GetForegroundWindow()
    titulo = win32gui.GetWindowText(hwnd) or ""
    proceso = ""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proceso = psutil.Process(pid).name()
    except Exception:
        pass
    return proceso.lower(), titulo.lower()


def clasificar(proceso, titulo):
    if any(t in titulo for t in OCIO_TITULOS):
        return "ocio"
    if proceso in OCIO_PROCESOS:
        return "ocio"
    if any(t in titulo for t in PRODUCTIVO_TITULOS):
        return "productivo"
    if proceso in PRODUCTIVO_PROCESOS:
        return "productivo"
    return "neutral"


def segundos_ausente():
    """Tiempo sin actividad de teclado/ratón."""
    ultimo = win32api.GetLastInputInfo()
    return (win32api.GetTickCount() - ultimo) / 1000.0


def es_de_noche():
    ahora = datetime.now().time()
    if NOCHE_INICIO <= NOCHE_FIN:
        return NOCHE_INICIO <= ahora <= NOCHE_FIN
    # cruza medianoche
    return ahora >= NOCHE_INICIO or ahora <= NOCHE_FIN


# ============================================================
#  INTERFAZ  ·  susurro discreto y diálogo con cara de error
# ============================================================

PALETA = {
    "fondo": "#1a1625",
    "borde": "#3d3456",
    "texto": "#e8e3f0",
    "tenue": "#9a8fb5",
    "acento": "#c9a8ff",
}


def susurro(mensaje):
    """Ventanita discreta abajo a la derecha que se desvanece sola."""
    win = tk.Tk()
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.attributes("-alpha", 0.0)
    win.configure(bg=PALETA["borde"])

    ancho, alto = 340, 90
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    win.geometry(f"{ancho}x{alto}+{sw - ancho - 24}+{sh - alto - 64}")

    marco = tk.Frame(win, bg=PALETA["fondo"])
    marco.pack(fill="both", expand=True, padx=1, pady=1)
    tk.Label(
        marco, text=mensaje, bg=PALETA["fondo"], fg=PALETA["texto"],
        font=("Segoe UI", 10), wraplength=ancho - 36, justify="left",
    ).pack(fill="both", expand=True, padx=18, pady=14)

    # Aparece, espera y se desvanece
    def fade(valor, paso):
        valor += paso
        if 0.0 <= valor <= 0.95:
            win.attributes("-alpha", valor)
            win.after(20, lambda: fade(valor, paso))
        elif valor > 0.95:
            win.after(7000, lambda: fade(0.95, -0.05))
        else:
            win.destroy()

    win.after(0, lambda: fade(0.0, 0.05))
    win.mainloop()


def dialogo(titulo, mensaje, botones):
    """Diálogo con pinta de error de Windows. Puedes replicarle por teclado.
    Devuelve la etiqueta del botón pulsado."""
    eleccion = {"valor": botones[-1]}

    # Paleta retro de Windows
    PLATA = "#c0c0c0"
    AZUL = "#000080"
    SOMBRA = "#808080"

    win = tk.Tk()
    win.overrideredirect(True)          # quitamos la barra nativa
    win.attributes("-topmost", True)
    win.configure(bg=SOMBRA)

    ancho, alto = 440, 250
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"{ancho}x{alto}+{(sw - ancho)//2}+{(sh - alto)//2}")

    # Borde 3D exterior
    cuerpo = tk.Frame(win, bg=PLATA, bd=2, relief="raised")
    cuerpo.pack(fill="both", expand=True, padx=1, pady=1)

    # ---- Barra de título azul, con la X ----
    barra = tk.Frame(cuerpo, bg=AZUL, height=24)
    barra.pack(fill="x", padx=2, pady=2)
    barra.pack_propagate(False)
    tk.Label(barra, text=titulo, bg=AZUL, fg="white",
             font=("Tahoma", 8, "bold")).pack(side="left", padx=6)

    def cerrar(etiqueta=botones[-1]):
        eleccion["valor"] = etiqueta
        win.destroy()

    btn_x = tk.Button(barra, text="✕", command=cerrar, bg=PLATA, fg="black",
                      font=("Tahoma", 8, "bold"), bd=2, relief="raised",
                      width=2, activebackground=PLATA)
    btn_x.pack(side="right", padx=3, pady=2)

    # Arrastrar la ventana desde la barra
    def _ini(e): win._x, win._y = e.x, e.y
    def _mov(e): win.geometry(f"+{win.winfo_x()+e.x-win._x}+{win.winfo_y()+e.y-win._y}")
    barra.bind("<Button-1>", _ini); barra.bind("<B1-Motion>", _mov)

    # ---- Zona de contenido: icono X roja + mensaje ----
    contenido = tk.Frame(cuerpo, bg=PLATA)
    contenido.pack(fill="both", expand=True, padx=16, pady=(14, 6))

    icono = tk.Canvas(contenido, width=34, height=34, bg=PLATA,
                      highlightthickness=0)
    icono.create_oval(2, 2, 32, 32, fill="#d40000", outline="#9b0000")
    icono.create_line(11, 11, 23, 23, fill="white", width=3)
    icono.create_line(23, 11, 11, 23, fill="white", width=3)
    icono.pack(side="left", anchor="n", padx=(2, 14))

    lbl_msg = tk.Label(contenido, text=mensaje, bg=PLATA, fg="black",
                       font=("Tahoma", 9), justify="left",
                       wraplength=ancho - 110)
    lbl_msg.pack(side="left", anchor="n", fill="x", expand=True)

    # ---- Campo de réplica ----
    fila_input = tk.Frame(cuerpo, bg=PLATA)
    fila_input.pack(fill="x", padx=18, pady=(0, 8))
    tk.Label(fila_input, text="Tu réplica:", bg=PLATA, fg="black",
             font=("Tahoma", 8)).pack(side="left")
    entrada = tk.Entry(fila_input, font=("Tahoma", 9), bg="white",
                       relief="sunken", bd=2)
    entrada.pack(side="left", fill="x", expand=True, padx=(6, 0))

    def replicar(_=None):
        if entrada.get().strip():
            winsound.MessageBeep(0x00000010)  # MB_ICONHAND (sonido de error)
            lbl_msg.config(text=random.choice(REPLICAS))
            entrada.delete(0, "end")

    entrada.bind("<Return>", replicar)

    # ---- Botones de acción ----
    barra_btn = tk.Frame(cuerpo, bg=PLATA)
    barra_btn.pack(side="bottom", fill="x", padx=12, pady=(4, 12))

    def boton(parent, texto, cmd):
        return tk.Button(parent, text=texto, command=cmd, bg=PLATA, fg="black",
                         font=("Tahoma", 8), bd=2, relief="raised",
                         padx=10, pady=2, activebackground=PLATA, cursor="hand2")

    boton(barra_btn, "Responder", replicar).pack(side="left")
    for etiqueta in botones:
        boton(barra_btn, etiqueta,
              lambda e=etiqueta: cerrar(e)).pack(side="right", padx=(6, 0))

    winsound.MessageBeep(0x00000010)  # pita como un error nada más salir
    entrada.focus_force()
    win.mainloop()
    return eleccion["valor"]


# ============================================================
#  BUCLE PRINCIPAL
# ============================================================

def main():
    ocio = 0.0              # segundos de ocio neto acumulados
    aviso_susurro = False   # ya susurré en este tramo
    ultimo_nocturno = 0.0
    burla_pendiente = False        # pediste "10 min más" -> ventana de burla
    burla_noche_pendiente = False  # pediste "Un poco más" de noche -> burla

    print("Centinela del Tiempo en marcha. Ctrl+C para parar.")

    while True:
        ahora = time.time()

        # --- Aviso nocturno (independiente del ocio) ---
        if es_de_noche() and ahora - ultimo_nocturno > NOCHE_REPETIR:
            if burla_noche_pendiente:
                # No te dejo posponer de verdad
                r = dialogo("Permiso denegado", "nop, ningún poco más.",
                            ["Tienes razón, a dormir", "Un poco más"])
                if r == "Tienes razón, a dormir":
                    ocio = 0
                    burla_noche_pendiente = False
                    ultimo_nocturno = time.time()
                # si insiste en "Un poco más", la burla sigue cada vuelta
            else:
                titulo, msg = random.choice(NOCTURNOS)
                r = dialogo(titulo, msg,
                            ["Tienes razón, a dormir", "Un poco más"])
                if r == "Un poco más":
                    burla_noche_pendiente = True
                else:
                    ocio = 0
                    ultimo_nocturno = time.time()
            time.sleep(INTERVALO)
            continue

        # --- Estado actual ---
        if segundos_ausente() >= AFK_LIMITE:
            estado = "ausente"
            vt = "—"
        else:
            proceso, titulo = ventana_activa()
            estado = clasificar(proceso, titulo)
            vt = titulo[:45]

        # Seguimiento por consola (déjalo mientras pruebas)
        print(f"[ocio={int(ocio)}s] estado={estado} | {vt}")

        # --- Contador de ocio neto ---
        if estado == "ocio":
            ocio += INTERVALO
        elif estado == "productivo":
            ocio = max(0, ocio - INTERVALO * DESCUENTO_PRODUCTIVO)
            aviso_susurro = False  # si vuelves al lío, reseteo el aviso suave
        # "neutral" y "ausente" no tocan el contador

        # --- Avisos por ocio ---
        if burla_pendiente:
            # No te dejo posponer de verdad: te lo recuerdo cada 5 s
            r = dialogo("Permiso denegado", "ja ja, sí, claro.",
                        ["Tienes razón, lo dejo", "10 min más"])
            if r == "Tienes razón, lo dejo":
                ocio = 0
                aviso_susurro = False
                burla_pendiente = False
            # si vuelve a pulsar "10 min más", burla_pendiente sigue True
        elif ocio >= UMBRAL_DIALOGO:
            titulo, msg = random.choice(PREGUNTAS)
            r = dialogo(titulo, msg,
                        ["Tienes razón, lo dejo", "10 min más"])
            if r == "10 min más":
                burla_pendiente = True
            else:
                ocio = 0
                aviso_susurro = False
        elif ocio >= UMBRAL_SUSURRO and not aviso_susurro:
            susurro(random.choice(SUSURROS))
            aviso_susurro = True

        time.sleep(INTERVALO)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCentinela retirado. Cuida tu tiempo.")