<div align="center">

# 🩷 Stalker · Centinela del Tiempo 🩷

*Un programita que te vigila y, cuando llevas demasiado rato de ocio,*
*te suelta un error de Windows falso para que cierres la pestañita.* 🌸

![Python](https://img.shields.io/badge/Python-3.14-ff69b4?style=flat-square&logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-only-ffb6d9?style=flat-square&logo=windows&logoColor=white)
![Hecho con](https://img.shields.io/badge/hecho%20con-mango%20loco%20🥭-ff69b4?style=flat-square)
![Aprendiendo](https://img.shields.io/badge/aprendiendo-sola%20y%20a%20mi%20manera-ffb6d9?style=flat-square)

</div>

---

## 🌸 ¿Qué hace?

Corre en segundo plano y mira qué ventana tienes delante:

- Si llevas un rato de ocio → te **susurra** algo bajito por la esquina.
- Si sigues ahí → te salta una **ventana con cara de error de Windows** (la X roja y todo) que te cuestiona.
- Y si le contestas por el teclado, te responde con bordería 💅
- De madrugada cambia el chip y te manda a dormir.

> Lo de posponer "10 minutos" existe… pero es mentira. Si le das, te contesta **"ja ja, sí, claro."** y vuelve a salir a los 5 segundos. No hay escapatoria. 🩷

---

## 🩷 Cómo se usa

```powershell
pip install pywin32 psutil
python centineladeltiempo.py
```

Para que arranque sola cada vez que enciendes el PC, hay un acceso directo con `pythonw` en la carpeta de Inicio (sin ventana negra).

---

## 🌸 Para trastear

Dentro del archivo, arriba del todo, puedes cambiar:

- **`UMBRAL_SUSURRO`** y **`UMBRAL_DIALOGO`** → cada cuánto te avisa.
- **`OCIO_TITULOS`** / **`PRODUCTIVO_TITULOS`** → qué cuenta como ocio y qué no.
- **`SUSURROS`**, **`PREGUNTAS`**, **`REPLICAS`** → los mensajes, con tu propia voz.

---

 - Ahora funciona como app de bandeja, con pausar/salir/ver-tiempo, y registra el ocio diario en CSV. 

<div align="center">

*Hecho con mango loco, claudio y cautela.* 🥭🩷

</div>