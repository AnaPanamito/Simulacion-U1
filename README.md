# Simulación de puestos de atención en una biblioteca universitaria (M/M/c)

Proyecto de Simulación que analiza cuántos puestos de atención requiere una biblioteca universitaria. Se comparan las medidas teóricas del modelo **M/M/c** con una **simulación de eventos discretos en Python** para evaluar la utilización de los puestos, la longitud media de la cola y el tiempo medio de espera.

La simulación permite comparar distintas configuraciones y seleccionar la menor que cumpla los criterios del estudio. **Python genera los datos**; el reporte **HTML** y el modelo de **NetLogo 7** permiten visualizar los resultados. Las tasas utilizadas son supuestos académicos, no mediciones de una biblioteca real.

## Tecnologías

- **Python 3.10 o posterior:** modelo matemático y simulación de eventos discretos.
- **NumPy:** generación reproducible de tiempos de llegada y servicio.
- **SciPy:** cálculo de intervalos de confianza del 95 %.
- **SymPy:** comprobación simbólica de las fórmulas M/M/c.
- **Matplotlib:** generación de gráficas en formato PNG.
- **HTML, CSS y JavaScript:** panel interactivo generado por Python; no necesita servidor ni conexión a internet.
- **NetLogo Desktop 7 (2D):** visualización de los datos importados desde CSV.
- **unittest:** pruebas automáticas, incluido en la biblioteca estándar de Python.

No se necesita instalar **SimPy**, **pytest** ni Java para ejecutar el código Python. NetLogo Desktop es una aplicación independiente.

## Instalación y ejecución

Descarga o clona el repositorio y abre una terminal **en la carpeta que contiene `main.py`**. Se recomienda usar un entorno virtual para instalar las dependencias.

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Si Windows no reconoce `python`, puedes probar con `py` al crear el entorno. Si PowerShell impide activarlo, **no necesitas modificar la política de seguridad**: ejecuta directamente el intérprete del entorno:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### Linux y macOS (Terminal)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

En Linux puede ser necesario instalar previamente el paquete de soporte de entornos virtuales de Python (`venv`) desde el gestor de paquetes de tu distribución.

### Opciones de ejecución

Para abrir automáticamente el reporte HTML en el navegador:

```bash
python main.py --abrir-html
```

Para una prueba corta del funcionamiento (3 réplicas, 1000 minutos y 100 de calentamiento):

```bash
python main.py --rapido
```

**Importante:** el modo rápido solo sirve para demostrar que el sistema funciona. Para generar los resultados oficiales del informe debes volver a ejecutar `python main.py` sin `--rapido`.

Para consultar todos los parámetros disponibles:

```bash
python main.py --help
```

El programa **no muestra un menú interactivo**: toma los parámetros predeterminados o los que indiques en los argumentos, ejecuta los experimentos y presenta una tabla en la consola.

## Resultados

Al ejecutar `main.py`, el programa crea automáticamente las carpetas **`Resultados/`** y **`Resultados_Graficas/`**. Estas carpetas son salidas generadas y **no se suben al repositorio GitHub**.

Archivos principales de `Resultados/`:

- `dashboard.html`: resumen interactivo con tablas, gráficas y reproducción de los estados registrados.
- `tabla_III_teoria.csv`: métricas teóricas del modelo M/M/c.
- `tabla_IV_comparacion.csv`: valores teóricos y simulados, con intervalos de confianza.
- `tabla_V_decision.csv`: evaluación de los criterios de espera y utilización.
- `tabla_VI_sensibilidad.csv`: análisis teórico de diferentes tasas de llegada.
- `replicas_detalladas.csv`: resultados de cada réplica.
- `netlogo_escenarios.csv`: resumen que importa NetLogo.
- `netlogo_serie_c3.csv` a `netlogo_serie_c6.csv`: estados registrados de cola y puestos ocupados para cada escenario.
- `netlogo_eventos_c3.csv` a `netlogo_eventos_c6.csv`: registro de eventos individuales exportado por Python.
- `analisis_simbolico_sympy.txt`: verificación matemática con SymPy.
- `parametros_ejecucion.json`: parámetros utilizados en la última corrida.

Archivos de `Resultados_Graficas/`:

- `fig_espera_python.png`: comparación de tiempos medios de espera (`Wq`).
- `fig_cola_python.png`: comparación de longitudes medias de cola (`Lq`).
- `fig_utilizacion_python.png`: comparación de la utilización (`ρ`).

**Significado de las métricas:** `Wq` es el tiempo medio en cola; `Lq` es el número medio de usuarios esperando; `ρ = λ / (c × μ)` es la utilización de los puestos. Los resultados simulados pueden variar si se cambian las semillas o los parámetros.

### Pruebas

Desde la carpeta principal del proyecto, con el entorno activado:

```bash
python -m unittest discover -s tests -v
```

Las **16 pruebas** comprueban, entre otros aspectos, configuración (Builder), cálculos teóricos, distribuciones (Strategy), reproducibilidad, observadores, límite de saturación, exportación de CSV, SymPy y estructura XML del modelo NetLogo. La comprobación XML no sustituye probar la interfaz directamente en NetLogo Desktop.

### Visualización en NetLogo 7

Primero ejecuta `python main.py` para generar los CSV. Después:

1. Mantén `NetLogo/` y `Resultados/` dentro de la **misma carpeta principal del proyecto**.
2. Abre **NetLogo Desktop 7 (2D)** y selecciona `NetLogo/Biblioteca_MMc_NETLOGO7.nlogox`.
3. Pulsa **INICIAR**: el modelo busca automáticamente los CSV, sin pedirte que los selecciones.
4. Utiliza los botones **3 PUESTOS**, **4 PUESTOS**, **5 PUESTOS** o **6 PUESTOS** para comparar.
5. Pulsa **PASO** o **ANIMAR** para recorrer los registros; **REINICIAR** vuelve al inicio.
6. Si ejecutas Python nuevamente, pulsa **CARGAR DATOS** para actualizar los resultados.

NetLogo muestra **estados registrados** (personas en cola y puestos ocupados). No vuelve a generar llegadas aleatorias ni realiza una segunda simulación. Los CSV de eventos se guardan para posibles mejoras de animación individual.

## Estructura

El programa utiliza una **arquitectura por capas simplificada**: presentación, dominio, aplicación e infraestructura. Incluye cinco patrones de diseño: **Builder, Strategy, Factory, Observer y Facade**.

```text
Biblioteca_Universitaria/
├── main.py                         # Presentación: argumentos y salida en consola
├── requirements.txt               # Dependencias de Python
├── README.md                      # Documentación del proyecto
├── .gitignore                     # Excluye archivos generados y entornos virtuales
├── biblioteca/
│   ├── __init__.py
│   ├── dominio.py                 # Configuración, Builder, fórmulas M/M/c, SymPy
│   ├── simulacion.py              # Strategy, Factory, Observer y eventos discretos
│   ├── experimentos.py            # Réplicas, intervalos y recomendación
│   └── reportes.py                # Facade: CSV, gráficas y HTML
├── NetLogo/
│   └── Biblioteca_MMc_NETLOGO7.nlogox
└── tests/
    └── test_biblioteca.py        # Pruebas con unittest
```

Las carpetas `Resultados/` y `Resultados_Graficas/` **aparecen después de ejecutar Python**. No deben agregarse a GitHub, igual que `.venv/` y `__pycache__/`.

## Escenarios

Valores predeterminados del informe:

| Parámetro | Valor |
|---|---|
| Tasa de llegada `λ` | `0.8` usuarios/minuto |
| Tasa de servicio `μ` por puesto | `1/3` usuarios/minuto (3 minutos por usuario) |
| Puestos evaluados `c` | `2,3,4,5,6` |
| Réplicas por escenario | `30` |
| Duración por réplica | `12000` minutos |
| Calentamiento descartado | `1200` minutos |
| Semilla base | `2026` |
| Espera media máxima | `Wq ≤ 2` minutos |
| Utilización máxima | `ρ ≤ 0.85` |

| Puestos (`c`) | Utilización teórica | Condición del escenario |
|---:|---:|---|
| 2 | 1.20 | Inestable |
| 3 | 0.80 | Estable, pero supera el límite de espera |
| **4** | **0.60** | **Menor configuración que cumple ambos criterios** |
| 5 | 0.48 | Cumple; mayor capacidad disponible |
| 6 | 0.40 | Cumple; mayor capacidad disponible |

### Cambiar escenarios sin editar el código

```bash
python main.py --puestos 3,4,5,6
python main.py --lambda-rate 0.1
python main.py --lambda-rate 1.5
python main.py --puestos 2,3,4,5,6,7,8,9,10
python main.py --mu-rate 0.4 --replicas 10
```

Los valores iniciales están definidos en `main.py` (argumentos) y `biblioteca/dominio.py` (configuración). Los experimentos y la elección de puestos se encuentran en `biblioteca/experimentos.py`.

**Protección contra saturación:** el programa no recomienda escenarios inestables (`ρ ≥ 1`) y detiene los escenarios estables demasiado cercanos a saturación (`0.98 ≤ ρ < 1`). Si agregas puestos distintos de 3 a 6, Python podrá analizarlos, pero el modelo NetLogo incluido solo dispone de botones directos para 3, 4, 5 y 6.

## Integrantes

**Autores:**

- Richard Cajas
- Ana Panamito
- Pedro Jimenez
- Santiago Villamagua
