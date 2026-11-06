# ARINC-429-completo

Aplicación web educativa en español, iniciada con Flask, SQLAlchemy y MySQL. La transmisión UART por puerto COM es una demostración informática, no una interfaz física ARINC 429 certificada.

## Estructura

- `app/`: fábrica Flask, configuración, modelos, rutas, codificación BNR y salidas serial/audio.
- `app/templates/` y `app/static/`: interfaz HTML, CSS y JavaScript.
- `sql/schema.sql`: tablas MySQL para instrumentos, envíos e historiales de salida.
- `tests/`: pruebas de rangos, codificación BNR, UART simulada y muestras de audio PCM.
- `run.py`: punto de entrada local.

## Ejecutar en PowerShell

Desde la carpeta del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
python run.py
```

Abrí `http://127.0.0.1:5000/`. Si PowerShell bloquea la activación del entorno virtual, ejecutá `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` en esa ventana y volvé a activar el entorno.

## MySQL

1. Ejecutá `sql/schema.sql` en MySQL Workbench o desde el cliente MySQL. El script crea la base `arinc429` y sus tablas.
2. Copiá `.env.example` como `.env` y completá `DATABASE_URL` con la URL de conexión de tu instalación MySQL. No agregues `.env` al repositorio ni compartas sus credenciales. La ruta de `.env` se resuelve desde el proyecto, no desde el directorio actual.
3. Detené cualquier servidor Flask que ya esté ejecutándose y volvé a iniciar `python run.py`: la configuración se lee al iniciar el proceso. Al arrancar, se informa el driver, host, puerto y nombre de base activos, nunca las credenciales. Las variables del proceso tienen precedencia sobre `.env`.

Sin `DATABASE_URL`, la app usa SQLite local para facilitar el primer arranque y lo indica en la consola. SQLite y MySQL son bases separadas: los registros históricos de `instance/arinc429.db` no se copian automáticamente a MySQL.

## Codificación inicial

`app/encoding.py` comprueba rangos y arma una palabra de demostración con campos Label (8 bits), SDI (2), Data BNR (19, complemento a dos), SSM (2) y paridad impar (1). El campo Data se calcula como `(valor - offset) / escala` y se acepta solo si el resultado es un entero exacto. La representación binaria/hexadecimal es la palabra de 32 bits. Antes de usarla con hardware real, hay que validar convenciones de Label, escala, SSM, orden de bits y requisitos de interfaz contra la documentación del equipo y la instalación objetivo.

## Envíos

En la sección **Envíos** se puede crear, consultar, editar y eliminar el historial. Cada valor debe estar dentro del rango inclusivo del instrumento, ser exactamente representable con su resolución BNR y caber en el campo firmado de 19 bits. Al editar, se vuelve a calcular y guardar la palabra completa. Las pruebas del módulo se ejecutan con `python -m pytest tests/test_envios.py`.

## Transmisión UART de demostración

Cada envío tiene un panel **Transmitir**. Consultar, crear o editar envíos no inicia ninguna transmisión; solo el botón envía una solicitud. El modo inicial es **Simulación**, que genera y registra los cuatro bytes sin abrir un puerto. En modo COM, la lista se obtiene automáticamente desde Windows con pyserial y el servidor vuelve a verificar que el puerto siga disponible.

La interfaz permite 9600, 19200 o 115200 baudios, y orden **big-endian** (byte más significativo primero) o **little-endian** (byte menos significativo primero). El enlace serial se configura como UART 8N1: 8 bits de datos, sin paridad UART y 1 bit de parada. Se transmiten exactamente los cuatro bytes de la palabra almacenada; el historial guarda fecha, instrumento, valor, puerto/modo, velocidad, orden, código, bytes y resultado.

Desde Windows Terminal, en la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest tests/test_serial_transmission.py tests/test_transmisiones.py -v
.\.venv\Scripts\python.exe run.py
```

Después abrí `http://127.0.0.1:5000/`, expandí **Transmitir** en un envío y dejá **Simulación** para probar sin hardware. Para una prueba UART, cambiá a **Puerto COM**, seleccioná el dispositivo detectado, elegí baudios y orden de bytes, y presioná **Transmitir**. Los intentos y los cuatro bytes aparecen en **Intentos de transmisión**. La tabla `transmisiones` se crea al ejecutar `sql/schema.sql`; en SQLite local se crea automáticamente.

No conectes el adaptador UART directamente a un instrumento aeronáutico real: UART no genera niveles, temporización ni señalización eléctrica ARINC 429, y este proyecto no es una interfaz certificada.

## Salida de audio de demostración

`app/audio_output.py` genera PCM `float32` para los 32 bits guardados: el 1 usa un pulso positivo y el 0 uno negativo, cada uno durante la mitad de su celda de bit; el resto vuelve a cero. La amplitud digital inicial es `0.020` y el máximo permitido es `0.050` sobre escala normalizada. Windows y el amplificador pueden cambiar el nivel analógico efectivo.

La aplicación detecta dispositivos de salida y usa una frecuencia de muestreo que el dispositivo acepta. La forma contiene 48 muestras por bit, por lo que su ritmo demostrativo es `frecuencia_de_muestreo / 48` (por ejemplo, 1000 bits/s a 48 kHz). No intenta reproducir ni afirmar fidelidad a las temporizaciones ARINC 429 de 12,5 o 100 kbit/s.

Desde Windows Terminal, instalá dependencias y corré las pruebas sin hardware:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest tests/test_audio_output.py tests/test_audio_routes.py -v
.\.venv\Scripts\python.exe run.py
```

En la interfaz, abrí **Vista previa y audio**, ajustá la amplitud si hace falta y presioná **Previsualizar forma de onda**. La vista previa nunca reproduce sonido. Para escucharla, seleccioná un dispositivo detectado, elegí **Reproducir por auriculares**, volvé a previsualizar si cambiaste amplitud o dispositivo y presioná **Transmitir por audio**. La modalidad inicial es simulación y los intentos se registran en `reproducciones_audio`; la tabla se crea al ejecutar `sql/schema.sql` en MySQL y automáticamente en SQLite local.

La salida de auriculares es únicamente una demostración de baja amplitud. No la conectes directa ni indirectamente a equipos aeronáuticos: no es una salida ARINC 429, no está certificada y no genera sus niveles eléctricos ni temporización.
