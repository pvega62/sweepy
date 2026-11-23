                                  ████  █   █  ████  ████  ████  █   █
                                  █     █   █  █     █     █  █  █   █
                                  ████  █ █ █  ███   ███   ████   █ █ 
                                    █  ██ ██  █     █     █       █  
                                  ████  █   █  ████  ████  █       █  
<h1 align="center">Sweepy: búsqueda de empleo y puntuación con varios motores</h1>

<p align="center">
  <strong>Busca con más inteligencia, mejor, más rápido y más fuerte.</strong><br>
  Extracción paralela de ofertas en las principales plataformas, puntuación automática del currículum y reportes ordenados por relevancia.
</p>

<p align="center">
  <a href="https://github.com/pvega62/sweepy/actions"><img src="https://github.com/pvega62/sweepy/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10 o superior"></a>
  <a href="../LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="Licencia MIT"></a>
  <a href="https://m8ven.ai/mcp/pvega62-sweepy-07ewva?s=readme"><img src="https://m8ven.ai/badge/mcp/pvega62-sweepy-07ewva?v=a2ea0bac35a4ed6e7512771f55ab2271" alt="Puntuación de M8ven"></a>
</p>

<p align="center">
  <a href="#quick-start"><strong>Inicio rápido</strong></a> ·
  <a href="#features">Funcionalidades</a> ·
  <a href="#job-engines">Motores de empleo</a> ·
  <a href="#portfolio-support">Soporte de portafolio</a> ·
  <a href="#documentation">Documentación</a> ·
  <a href="https://github.com/pvega62/sweepy/issues/new">Informar de un problema</a>
</p>

<p align="center">
  <a href="../README.md">English</a> · <strong>Español</strong> · <a href="README.fr.md">Français</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.ja.md">日本語</a> · <a href="README.ar.md">العربية</a> · <a href="README.zh.md">简体中文</a>
</p>

---

Sweepy es una herramienta gratuita que busca en portales de empleo y puntúa cada oferta frente a tu currículum. Lee sitios de empleo de empresas y portales de ofertas, descarta los anuncios duplicados y los caducados y, después, escribe un reporte ordenado por relevancia. Puedes desactivar la comprobación de duplicados en una búsqueda sin cambiar tu perfil. El asistente de configuración abre un panel de inicio para búsquedas, configuración del perfil, ajuste de las búsquedas y tareas de la Caja de herramientas de Sweepy, como la gestión de motores y agregadores.

> Consulta **[CHANGELOG.md](../CHANGELOG.md)** para ver la versión actual y el historial de versiones.

## <a name="features"></a>Funcionalidades

- **Busca en muchos sitios a la vez.** Recopila ofertas de Greenhouse, Ashby, Lever, Workable, Built In NYC, LinkedIn, Indeed, Glassdoor y ZipRecruiter. Cada una de estas fuentes funciona sin clave de API.
- **Ejecuta cada motor en paralelo.** Los motores habilitados arrancan a la vez. Una búsqueda tarda entonces más o menos lo que el motor más lento, no la suma de todos.
- **Sigue adelante cuando falla un portal.** Cada motor tiene un tiempo de espera y un cortacircuitos. Un endpoint que falla no puede atascar la ejecución ni repetir la misma petición cinco veces.
- **Añade más motores cuando los necesites.** Instala HireHunt, openroles, jobdrop o Apify desde el asistente sin salir de la terminal.
- **Puntúa cada oferta frente a tu currículum.** Lee el texto de tu currículum en PDF o Word y mide qué parte coincide con la oferta.
- **Descarta los enlaces caducados.** Comprueba cada URL y elimina las ofertas que ya no existen.
- **Detecta ofertas duplicadas entre portales.** Compara el título del puesto, la empresa y la ubicación normalizados, aunque los portales usen URLs distintas. Pasa `--no-dedupe` para conservar el anuncio de cada portal en una ejecución.
- **Omite las ofertas que ya has visto.** Una búsqueda diaria informa de puestos nuevos en lugar de la lista de ayer. Sweepy suprime las ofertas reportadas durante una ventana de cuatro días. Pasa `--include-seen` para recuperarlas en una ejecución.
- **Te lleva al currículum correcto.** Envía cada empleo a la versión del currículum que escribiste para ese puesto y etiqueta la tarjeta con una insignia de color.
- **Hace que tu portafolio cuente en cada decisión.** Apunta Sweepy a un portafolio en línea o a un archivo local PDF, Word, Markdown, texto o HTML. Cada tarjeta lista las piezas de ese portafolio. Cuando te presentas a más de un tipo de puesto, mantén un portafolio por versión del currículum.
- **Genera un reporte que puedes usar.** Produce un PDF con una tarjeta por página y enlaces clicables, además de archivos CSV y JSON para tu propio seguimiento.
- **Convierte el CSV en un registro de candidaturas.** El CSV termina con `date_applied`, `status`, `interview_stage`, `offer_amount`, `offer_date`, `follow_up_date`, `contact` y `notes`. Rellena esas columnas desde Excel, Google Sheets o Notion. Sweepy copia tus entradas en búsquedas posteriores del mismo perfil. El PDF te da una lista de lectura ordenada por relevancia con enlaces para enviar la candidatura en cada tarjeta. La hoja de cálculo conserva los puestos que quedan fuera del límite de tarjetas del PDF y registra qué hiciste con cada uno. Desactiva las columnas con `export.tracking: false`.

## <a name="quick-start"></a>Inicio rápido

Necesitas **Python 3.10 o superior**. En Python 3.13, algunos paquetes se compilan desde el código fuente. Puede que antes necesites Microsoft C++ Build Tools. Consulta [Instalar Sweepy](https://pvega62.github.io/software/docs/sweepy/installation).

```bash
git clone https://github.com/pvega62/sweepy.git
cd sweepy
pip install -e .
sweepy
```

`pip install -e .` instala todas las dependencias del núcleo y registra el comando `sweepy` en tu carpeta Scripts de Python. Vuelve a abrir la terminal una vez para que el shell recoja esa carpeta del PATH. Ejecuta `sweepy` para abrir el asistente o añade una opción al comando, como `sweepy --run`. También puedes ejecutar el script directamente con `python swee.py`.

Ese único comando te da los dos motores integrados. El asistente ofrece los cuatro motores opcionales cuando los necesitas, y nunca tienes que instalar a mano un segundo archivo de requisitos.

Para descargar de una vez todos los motores compatibles, añade un indicador al mismo comando:

```bash
pip install -e ".[all-engines]"
```

Eso añade HireHunt, openroles y Apify en una sola resolución. `jobdrop` queda fuera porque sus metadatos no se resuelven junto a JobSpy. Instálalo con `sweepy --install-engines jobdrop --allow-engine-conflicts` cuando quieras sus 33 portales. La sección [Motores de empleo](#job-engines) cubre las dos vías.

Ejecutar `sweepy` abre el panel de inicio por mosaicos del asistente. Usa las teclas de flecha para moverte entre **Start Sweep**, **Build Profile**, **Load Profile**, **Sweep Settings**, **Sweepy's Toolbox** y **Exit Sweepy**, y pulsa Enter. Los subtítulos de cada mosaico describen la acción con palabras llanas, como en **Run your job search now** o **Open a search you saved**. **Load Profile** te permite elegir un perfil guardado para la siguiente búsqueda. La caja de herramientas contiene edición de perfiles, gestión de motores, registro de depuración, ayuda, registros recientes, conversión de documentos y actualizaciones. **Build Profile** recopila tu nombre, los títulos de puesto que buscas, la ubicación y la ruta del currículum. El asistente guarda el perfil cuando terminas. Ejecuta `sweepy --setup --profile profiles/your_profile.yaml` para editar un perfil directamente.

Los submenús se abren con **← Back**, que vuelve al menú que los abrió. Esc hace lo mismo. En una pregunta, Esc reabre la respuesta anterior. Dentro de un submenú, Esc sube un nivel. En el panel de inicio, Esc sale. Ctrl+C cierra desde cualquier punto.

Para descargar código nuevo cuando se publica una versión, ejecuta:

```bash
sweepy --update
```

Sweepy comprueba tu remoto de Git y avanza el checkout. Reinstala `requirements.txt` y los motores opcionales que ya tengas instalados. Se niega a modificar un checkout con cambios sin confirmar. Prefiere `sweepy --check-update` para comprobar si hay una versión nueva sin cambiar nada.

Después, ejecuta tu primera búsqueda:

```bash
sweepy --run
```

`--run` busca con el último perfil que guardaste. Para indicar otro perfil, usa `sweepy --profile profiles/your_profile.yaml`.

Desactiva la comprobación de duplicados en una ejecución sin editar un ajuste del perfil:

```bash
sweepy --run --no-dedupe
sweepy --profile profiles/your_profile.yaml --no-dedupe
```

De forma predeterminada, Sweepy conserva una sola oferta cuando distintos portales listan el mismo título, empresa y ubicación normalizados. La herramienta `run_sweep` del Model Context Protocol (MCP) acepta `deduplicate=false` para el mismo ajuste de una sola ejecución.

Sweepy también oculta las ofertas de búsquedas anteriores. Revísalas de nuevo o empieza de cero:

```bash
sweepy --run --include-seen      # report earlier postings too
sweepy --run --reset-history     # forget them, then sweep
sweepy --reset-history           # forget the last profile's history and exit
```

Crea o actualiza un perfil sin preguntas cuando automatizas Sweepy:

```bash
sweepy --setup --non-interactive \
  --name "Alex Rivera" \
  --titles "Technical Writer,UX Writer" \
  --location "New York, NY" \
  --resume C:/resumes/alex.pdf \
  --sources jobspy,openroles \
  --openroles-companies figma,stripe,notion \
  --timeout 120 --no-cache
```

Sweepy valida los motores habilitados antes de escribir el archivo. Un campo obligatorio que falta falla de inmediato con el motivo. En el asistente interactivo, deja en blanco los slugs de empresa de OpenRoles para omitir ese motor. OpenRoles solo busca en portales de empresa con nombre. Los perfiles no interactivos que habilitan OpenRoles siguen necesitando `--openroles-companies`. Los indicadores no interactivos cubren `--sources`, `--jobspy-sites`, `--hirehunt-sources`, `--jobdrop-sites`, `--openroles-companies`, `--apify-actor`, `--timeout`, `--cache-ttl`, `--no-cache`, `--history-days`, `--no-history` y `--job-tracking` / `--no-job-tracking`.

Rellena un archivo de perfil cuando prefieras un editor a las preguntas y las llamadas a herramientas:

```bash
cp profiles/template_custom.yaml profiles/my_search.yaml
# replace the four REQUIRED values, then run the copy
sweepy --profile profiles/my_search.yaml
```

La plantilla documenta cada ajuste con su valor predeterminado. Sweepy imprime tu nombre, tus títulos y tu ubicación antes de que empiece el descubrimiento. Un error tipográfico aparece en la primera línea de salida.

Convierte un currículum o un archivo de notas a PDF sin abrir el asistente:

```bash
sweepy --convert path/to/resume.docx
```

`--convert` acepta archivos `.docx`, `.doc`, `.txt`, `.md` y `.pdf`. Escribe el PDF junto al archivo original e imprime la ruta final.

Una búsqueda tarda de 30 a 90 segundos. Sweepy imprime su progreso mientras trabaja:

1. **Carga tu perfil.**
2. **Descubre vacantes** en las plataformas que activaste.
3. **Valida los enlaces** y descarta los caducados.
4. **Puntúa cada puesto** frente a tu currículum.
5. **Escribe tu reporte.**

## <a name="what-you-get"></a>Qué obtienes

Cada ejecución escribe archivos con la fecha en la carpeta `results/`. Los reportes anteriores se quedan donde están. Una búsqueda que se ejecuta a través de MCP añade `mcp` al nombre del archivo, como en `paralegal_nyc_mcp_2026-10-27-223115.pdf`. La marca sigue el reloj de tu máquina. Ajusta `export.timezone` para nombrar archivos en otra zona.

- **Un reporte PDF.** Una tarjeta por puesto, ordenadas por puntuación de coincidencia, con salario, beneficios y un enlace para enviar la candidatura.
- **Un archivo CSV.** Todos los campos de la tarjeta, el cuerpo completo de la oferta y ocho columnas de seguimiento de empleo que Sweepy copia en búsquedas posteriores. Ábrelo en Excel, Google Sheets o Notion. Ajusta `export.description_chars` a un número positivo cuando quieras archivos más pequeños. Un cuerpo recortado termina con una nota que cuenta los caracteres omitidos.
- **Un archivo JSON.** Los mismos datos en un formato que otras herramientas pueden leer.

Abre el [PDF de muestra](../docs/sample_report.pdf) o mira la [página 1 como imagen](../docs/sample_report.png).

## <a name="job-engines"></a>Motores de empleo

Sweepy incluye dos motores y puede descargar cuatro más. El motor `ats` lee directamente los sistemas de seguimiento de candidaturas (ATS). Cada motor funciona detrás del mismo adaptador. Los perfiles se ven igual, sea cual sea el motor que encontró la oferta.

| Motor | Disponibilidad | Qué extrae | Proxies | User-Agent | Descripciones |
|---|---|---|---|---|---|
| `jobspy` | Integrado | LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs, Bayt, Naukri, BDJobs | Sí | Sí | Alternable |
| `ats` | Integrado | Greenhouse, Ashby, Lever, Workable, BuiltinNYC | No | No | Siempre |
| `hirehunt` | Descarga | LinkedIn, Indeed, Naukri, Shine, Internshala, Unstop y seis portales de empresa (Google Careers, Amazon, Meta, Apple, Netflix, Microsoft) | No | No | Siempre |
| `openroles` | Descarga | Portales de Greenhouse, Lever, Ashby y Workday que nombres | No | No | Siempre |
| `jobdrop` | Descarga | 33 portales, entre ellos Google, Wellfound, Workday, iCIMS, Dice y USAJobs | Sí | Sí | Alternable |
| `apify` | Descarga | Actores gestionados, LinkedIn de forma predeterminada | Gestionado por el actor | Gestionado por el actor | Según el actor |

`jobdrop` informa de un conflicto de metadatos con JobSpy: fija `curl-cffi<0.8`, mientras que JobSpy requiere `curl_cffi>=0.16.2`. La restricción está obsoleta. `jobdrop` funciona sin problemas con la biblioteca más reciente, que todavía incluye todos los perfiles de suplantación que usa (`safari17_2_ios`, `chrome120`, `chrome124`).

Un `pip install` normal de ambos sigue fallando. `--install-engines all` deja `jobdrop` fuera. Añade `--allow-engine-conflicts` para instalarlo de la forma admitida. Sweepy instala `jobdrop` con `--no-deps` y después resuelve sus otros requisitos, así que `curl_cffi` se queda en la versión de JobSpy y los dos motores funcionan.

```bash
sweepy --install-engines all
sweepy --install-engines openroles,apify
sweepy --install-engines jobdrop --allow-engine-conflicts
```

`pip check` sigue informando del límite superior obsoleto de `jobdrop` después de esa instalación. La advertencia describe los metadatos, no el código en ejecución.

O abre el asistente y elige **Sweepy's Toolbox** y luego **Download job engines**. Esa pantalla lista los portales y el estado de instalación de cada motor. Pregunta antes de ejecutar `pip`. Si eliges un motor que falta mientras creas un perfil, el asistente ofrece la misma descarga. Sweepy nunca ejecuta una instalación sin tu confirmación.

### <a name="disk-footprint"></a>Huella en disco

Medido en Windows con Python 3.13:

| Instalación | Paquetes en disco | Notas |
|---|---|---|
| Núcleo (`requirements.txt`) | 283 MB | 53 paquetes, entre ellos pandas, pymupdf y el SDK de MCP |
| `hirehunt` | +13 MB | Añade rich y markdown-it-py |
| `openroles` | +0.3 MB | Solo la biblioteca estándar de Python |
| `apify-client` | +14 MB | Añade impit y more-itertools |
| `jobdrop` | +406 MB | Con scipy a la cabeza (134 MB), playwright (113 MB), tls-client (93 MB) y selenium (34 MB) |

Una instalación completa de los motores compatibles ocupa unos **310 MB**. Añadir `jobdrop` lleva el total a unos **716 MB** antes de que descargue un navegador.

Los binarios del navegador viven fuera del entorno de Python y llegan en el primer uso:

- La compilación de Chromium de Playwright ocupa unos **710 MB** (Chromium más su shell sin interfaz gráfica).
- Un conjunto completo de Playwright, con Firefox y WebKit, ocupa unos **1.2 GB**.
- Camoufox, que `jobdrop` usa para su ruta sigilosa, descarga un Firefox parcheado en el primer arranque.

Sweepy ejecuta todos los motores integrados sin navegador. La instalación del núcleo no necesita nada de ese espacio.

Lista los motores y su estado de instalación en cualquier momento:

```bash
sweepy --list-engines
```

`openroles` lee los portales que nombres y requiere slugs de empresa. `apify` lee una variable de entorno `APIFY_TOKEN` y factura a tu cuenta de Apify.

Instalar un motor no lo activa. Añádelo a un perfil de una de estas tres formas:

1. **Asistente.** Ejecuta `sweepy`, elige **Sweepy's Toolbox**, luego **Manage job engines** y después **Choose engines and settings**. Los motores instalados muestran una etiqueta `[installed]`. Marca uno y el asistente te pide sus ajustes.
2. **Edición del perfil.** Carga el perfil y elige **Manage job engines** en la pantalla de revisión.
3. **Línea de comandos.** Nombra el motor en `--sources` y facilita sus ajustes:

```bash
sweepy --setup --non-interactive --profile profiles/your_profile.yaml \
  --sources jobspy,ats,jobdrop --jobdrop-sites linkedin,indeed,wellfound
```

Cada vía valida los ajustes del motor antes de escribir el archivo. Un valor que falta, como los slugs de empresa de `openroles`, falla con el motivo en lugar de guardar un perfil roto.

### <a name="choosing-boards"></a>Elegir portales

El paso de plataformas del asistente de perfil lista todos los portales en los que Sweepy puede buscar, agrupados bajo el motor que los lee. Los 63 portales aparecen en un solo sitio en lugar de solo los 13 integrados.

| Grupo | Portales | Etiqueta |
|---|---|---|
| `jobspy` (8) | LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs, Bayt, Naukri, BDJobs | `built in` |
| `ats` (5) | Greenhouse, Ashby, Lever, Workable, BuiltinNYC | `built in` |
| `hirehunt` (12) | LinkedIn, Indeed, Naukri, Shine, Internshala, Unstop, Google Careers, Amazon, Meta, Apple, Netflix, Microsoft | `needs download` hasta que se instala |
| `openroles` (4) | Greenhouse, Lever, Ashby, Workday | `needs download`, y necesita slugs de empresa |
| `jobdrop` (33) | Google, Wellfound, Workday, iCIMS, Dice, USAJobs, Handshake y más | `needs download`, y entra en conflicto con JobSpy |
| `apify` (1) | LinkedIn a través de un actor de Apify | `needs download`, y necesita un `APIFY_TOKEN` |

Cada fila muestra su motor y su estado de instalación, como `Indeed  [jobspy · built in]` o `Wellfound  [jobdrop · needs download]`. Ves la etiqueta antes de confirmar la elección. Marca un portal de un motor sin instalación local y el asistente imprime el comando que lo instala. Un motor instalado muestra `installed` en su lugar. Al reabrir un perfil guardado, sus portales actuales ya aparecen marcados. Sweepy conserva en el perfil un portal de un motor no instalado, y la búsqueda omite ese motor con una advertencia hasta que termina la instalación.

### <a name="engine-settings"></a>Ajustes de los motores

```yaml
sources:
  enabled: [jobspy, ats, openroles]
  greenhouse:
    discovery: broad
    concurrency: 20
  openroles:
    ats: [greenhouse, lever, ashby, workday]
    companies: [figma, stripe, notion]
  jobdrop:
    sites: [linkedin, indeed, google, glassdoor]
    headless: true
    fetch_descriptions: true
    proxies: ["user:pass@host:port"]
cache:
  enabled: true
  ttl_seconds: 3600
history:
  enabled: true
  retention_days: 4
  match: url+role
  path: null
orchestrator:
  timeout_per_source_seconds: 180
  circuit_breaker:
    failure_threshold: 5
    cooldown_seconds: 30
```

Los perfiles antiguos siguen funcionando. Los booleanos de portal bajo `sources.jobspy` siguen activando y desactivando portales concretos de JobSpy. Cualquier perfil sin una lista `sources.enabled` usa JobSpy más los lectores ATS integrados de forma predeterminada.

- **Las descripciones siguen activadas de forma predeterminada.** La puntuación compara el texto de la oferta con tu currículum. Desactiva `fetch_descriptions` solo si aceptas coincidencias más flojas a cambio de una búsqueda más rápida.
- **Greenhouse lee una lista de portales más amplia si se lo pides.** `sources.greenhouse.boards` nombra los portales que quieres. Ajusta `sources.greenhouse.discovery: broad` para recorrer además la lista incluida de 619 slugs en `data/sources/greenhouse_slugs_broad.txt`, y Sweepy añade cualquier portal que tu perfil ya nombre. `sources.greenhouse.concurrency` fija cuántos portales lee Sweepy a la vez: 20 en modo amplio y 1 en el resto. Un sondeo amplio genera muchas respuestas HTTP 404 por diseño. Sweepy informa del recuento de fallos y de los diez primeros slugs en una sola advertencia en lugar de una línea por portal.
- **Los proxies siguen siendo opcionales en cada motor.** El asistente los lee de un archivo o acepta uno en línea, oculta la contraseña mientras escribes y nunca imprime el contenido. `hirehunt` no ofrece opción de proxy, así que Sweepy registra una advertencia cuando un perfil configura uno.
- **La caché arranca activada.** Una consulta repetida con los mismos motores y ajustes devuelve los resultados anteriores durante una hora. Desactívala con `cache.enabled: false` o acorta `ttl_seconds`.
- **Los tiempos de espera se detienen en el límite.** Python no puede detener un hilo que ya está bloqueado dentro de una llamada a una biblioteca. Sweepy deja de esperar y sigue adelante, y cada biblioteca aplica por debajo sus propios tiempos de espera HTTP.
- **El cortacircuitos omite un motor que falla.** Después de cinco fallos consecutivos, Sweepy deja de llamar a ese motor durante 30 segundos y lo informa en `skipped_sources`.

### <a name="reported-postings"></a>Ofertas reportadas

Sweepy registra cada oferta que reporta y omite la misma oferta en la búsqueda siguiente. Sweepy guarda el registro en `~/.sweepy/history.db`, con alcance por perfil. Define `SWEEPY_HISTORY_PATH` para guardarlo en otro sitio. La pantalla **Sweep Settings** del asistente ofrece el interruptor de activación y la ventana de retención.

```yaml
history:
  enabled: true
  retention_days: 4   # 0 reports every posting on every run
  match: url+role     # url (strict) or url+role (default)
  path: null          # null uses ~/.sweepy/history.db
```

- **La retención es una cadencia de reaparición.** Sweepy suprime una oferta hasta que pasan los `retention_days` y después la reporta otra vez. Un anuncio activo de forma continua vuelve como máximo cada cuatro días.
- **La coincidencia es tolerante de forma predeterminada.** Sweepy compara las URL canónicas después de quitar los parámetros de seguimiento y los fragmentos. Luego recurre al título, la empresa y la ubicación normalizados, así que una republicación en otro portal cuenta como el mismo puesto. Ajusta `match: url` para exigir una coincidencia de URL canónica.
- **Solo cuentan las ofertas activas.** Una oferta entra en el historial después de que su URL pasa la validación. Los enlaces caducados nunca se vuelven invisibles.
- **Quien llama desde MCP obtiene el mismo comportamiento predeterminado.** `run_sweep` informa de `previously_seen_count` y `new_count`. Pasa `include_seen=true` para revisar ofertas anteriores o llama a `clear_history` para olvidarlas. `create_profile` acepta `history_config`.

### <a name="adding-another-engine"></a>Añadir otro motor

1. Crea `engine/adapters/<name>_adapter.py` y define una subclase de `ScraperAdapter`.
2. Define `name`, los tres indicadores `supports_*`, `default_concurrency` y `library`.
3. Escribe `preflight()` para comprobar la configuración y `scrape()` para devolver un DataFrame.
4. Regístralo en `engine/adapters/__init__.py`.
5. Descríbelo en `engine/engines.py` para que el asistente pueda mostrarlo e instalarlo.
6. Añade un bloque de configuración a `engine/sweep_config.py` y una pregunta a `_ENGINE_PROMPTS` en `engine/config.py`.
7. Añade el paquete a `requirements-engines.txt` y a los extras de pyproject.
8. Prueba el adaptador por separado y luego actívalo solo durante una búsqueda.

El orquestador se encarga del resto. Distribuye por nombre y aplica el tiempo de espera. Cualquier DataFrame que devuelva se normaliza.

## <a name="agent-judgment"></a>Juicio del agente

Sweepy puntúa las ofertas por vocabulario compartido, y esa puntuación no llama a un modelo ni usa la red. Las mismas entradas producen la misma puntuación, que mide la redacción, no la idoneidad. El servidor MCP trata la evaluación de un agente como la ruta esperada.

`run_sweep` no llama a un modelo. Devuelve `assessment_mode: "agent"`, `assessment_required: true` y `assessed_count: 0`. El flujo continúa con `get_jobs`, una evaluación independiente de cada puesto frente al currículum, `submit_judgments` y `render_report`. Pasa todos los juicios en una sola lista `judgments` para que una evaluación de 24 puestos quepa en una llamada. Las tarjetas evaluadas muestran `NN% MATCH`. Las tarjetas sin evaluar mantienen `NN% KEYWORD OVERLAP`.

`get_jobs` devuelve `resume_documents` con el texto analizado de cada versión del currículum. Juzga ese texto, no los `must_have_skills` y `synonyms` del perfil, que solo alimentan la pasada determinista de palabras clave. Lee el documento como lo lee una persona de selección: habilidades transferibles, el alcance y la antigüedad que hay detrás de cada punto, el dominio, las herramientas y los resultados que demuestra. Luego puntúalo como lo analiza el sistema de seguimiento de candidaturas de la oferta. Un término que el analizador encuentra en una sección estándar de Experiencia o Aptitudes cuenta como prueba. El mismo término dentro de una tabla, un encabezado, un pie de página, una imagen o una barra lateral de dos columnas puede no llegar nunca a una persona, así que pesa menos. Sweepy nombra la familia de ATS cuando la URL de candidatura la revela, y el juicio registra lo que un analizador perdería.

`match_pct` mide la cualificación, así que la logística del empleo queda fuera. La jornada a tiempo parcial, el tipo de contrato y la ubicación van en `concerns`. Un puesto que la persona candidata puede desempeñar pierde puntos solo cuando las habilidades o la experiencia no coinciden con los requisitos que declara la oferta. Así la clasificación mide la idoneidad y no la disponibilidad.

Evalúa los dos lados del caso. `alignment` recoge el punto fuerte, la prueba más sólida de que la persona candidata encaja. `concerns` recoge lo que juega en contra de la persona candidata. Algunos ejemplos son una cualificación que falta, un hueco de permanencia, una jornada a tiempo parcial, un contrato temporal, una ubicación que exige mudarse o un salario por debajo del mínimo. El reporte imprime la pareja en una línea bajo la fila de requisitos, y el CSV gana una columna `concerns`. Una ejecución solo de palabras clave rellena `concerns` con las palabras clave de la oferta que el currículum no tiene.

`submit_judgments` también acepta `portfolio_highlight`. Pasa las piezas del portafolio para esa oferta y la tarjeta las imprime como **Highlight**. Una tarjeta sin un destacado enviado lista las piezas que encontró Sweepy.

## <a name="portfolio-support"></a>Soporte de portafolio

Sweepy lee un portafolio una vez por búsqueda y lista sus piezas en cada tarjeta. Recopila el portafolio antes de crear el perfil. Dale una URL en línea o un archivo local `.pdf`, `.docx`, `.md`, `.txt` o `.html`. Pasa una entrada por versión del currículum cuando apuntas a más de una familia de puestos.

```yaml
portfolio:
  # One entry per resume track. An entry without `track` serves every track.
  sources:
    - track: "UX Writer Resume"
      url: "https://example.com/work"
    - track: "Technical Writer Resume"
      path: "C:/portfolios/technical-writing.pdf"
  pieces_per_card: 3
```

Sweepy descarga un portafolio en línea para leer sus encabezados y enlaces. Cuando una página bloquea la petición, la tarjeta conserva el enlace y omite la lista de piezas. La tarjeta PDF muestra el portafolio y sus piezas. Las exportaciones CSV y JSON añaden `portfolio_url`, `portfolio_pieces` y `portfolio_highlight`.

Para adjuntar un portafolio a un perfil guardado, llama a `set_portfolio` desde el MCP o responde al paso de portafolio del asistente. Una configuración sin interfaz acepta `--portfolio` y `--portfolio-track`.

`render_report` acepta un argumento `playbook` para el cuadro de estrategia de cierre. Escribe prosa simple. Sweepy escapa los ampersands y convierte los saltos de línea en saltos de línea HTML. `**bold**` se renderiza como texto en negrita, y los corchetes angulares pasan a ser texto simple. Sweepy guarda el playbook con la sesión, y una renderización posterior lo reutiliza en lugar del generado. Empezar una búsqueda nueva lo borra.

En el modo `agent`, `render_report` se niega a crear un reporte mixto. Devuelve un error que lista los identificadores de los puestos sin evaluar. El asistente lee esa lista y envía juicios para los identificadores que faltan. Los perfiles que quieren reportes solo de palabras clave definen `report.assessment: "keyword"`. Una ejecución desde la línea de comandos también informa del solapamiento de palabras clave, ya que ningún agente aporta juicios. Define `SWEEPY_REQUIRE_JUDGMENTS=1` cuando la barrera deba aplicarse a todos los perfiles y también a `export_report`.

Una búsqueda en vivo extrae portales durante un minuto o más. El servidor MCP la ejecuta en segundo plano. `run_sweep` espera como máximo 45 segundos y después devuelve `sweep_status: "running"` con un `job_id`. Consulta `get_sweep_status` hasta que informe de `completed`. La búsqueda sigue en marcha si el cliente se desconecta. Define `SWEEPY_MCP_WAIT_SECONDS` para reducir la espera en hosts con tiempos de espera de herramientas más ajustados.

- Los perfiles creados desde MCP usan los motores integrados más los motores opcionales instalados que superan sus comprobaciones de configuración predeterminadas.
- Proporciona `sources_config` para elegir motores de forma explícita.
- OpenRoles necesita un slug por empresa.
- Apify necesita una aceptación explícita porque puede generar cargos.

El asistente puede verificar los resultados y cubrir huecos con sus herramientas de búsqueda. Debe contrastar las fuentes omitidas y las ofertas con las páginas de empleo de la empresa. Debe añadir las omisiones verificadas y etiquetar como no verificados los anuncios inaccesibles. Debe avisar cuando no pueda confirmar una cobertura completa.

Lee [Integración con MCP](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration) para ver los pasos de configuración.

Cada herramienta MCP publica indicaciones de solo lectura, destructiva, idempotente y de mundo abierto. Los hosts compatibles leen esas indicaciones antes de llamar a la herramienta.

## <a name="before-you-upload-your-resume"></a>Antes de subir tu currículum

Tu diseño decide cuánto texto puede leer Sweepy. Un diseño a dos columnas, una tabla o una página escaneada desordena el texto que lee el motor y baja tus puntuaciones. Una sola columna limpia de texto real se extrae con más fiabilidad, y los sistemas de seguimiento de candidaturas la leen igual.

Lee [Consejos de formato para el currículum](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips) antes de tu primera búsqueda.

## <a name="documentation"></a>Documentación

### <a name="getting-started"></a>Primeros pasos

- [Introducción](https://pvega62.github.io/software/docs/sweepy/intro)
- [Instalación](https://pvega62.github.io/software/docs/sweepy/installation)
- [Configuración](https://pvega62.github.io/software/docs/sweepy/setup)
- [Ejecutar tu primera búsqueda](https://pvega62.github.io/software/docs/sweepy/first-sweep)
- [Entender tus resultados](https://pvega62.github.io/software/docs/sweepy/understanding-results)

### <a name="resumes-and-match-scores"></a>Currículums y puntuaciones de coincidencia

- [Consejos de formato para el currículum](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips)
- [Puntuación y límites](https://pvega62.github.io/software/docs/sweepy/guides/scoring-and-limits)

### <a name="command-and-configuration-reference"></a>Referencia de comandos y configuración

- [Comandos e indicadores](https://pvega62.github.io/software/docs/sweepy/reference/cli-reference)
- [Referencia de configuración](https://pvega62.github.io/software/docs/sweepy/reference/configuration-reference)
- [Fuentes de empleo y plataformas](https://pvega62.github.io/software/docs/sweepy/reference/sources-and-platforms)
- [Integración con MCP](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration)
- [Referencia de herramientas MCP](https://pvega62.github.io/software/docs/sweepy/reference/mcp-tool-reference)
- [Referencia para desarrolladores](https://pvega62.github.io/software/docs/sweepy/reference/developer-reference)

## <a name="legal-and-responsible-use"></a>Uso legal y responsable

Sweepy extrae datos de portales de empleo públicos y de las API de esos portales. El scraping puede infringir las condiciones de servicio de algunas plataformas. Revisa esas condiciones antes de confiar en la herramienta.

- Úsala para **buscar empleo por tu cuenta**. No la uses para recopilar de forma masiva ni para redistribuir datos.
- Respeta los límites de frecuencia. Sweepy envía un User-Agent cortés y una pausa breve entre peticiones. Aumenta la pausa con la variable de entorno `SWEEPY_SOURCE_DELAY`.
- Sweepy no ofrece asesoramiento legal.

El scraping se ejecuta a través de [`python-jobspy`](https://github.com/Bunsly/JobSpy) y, cuando los instalas, [`hirehunt`](https://pypi.org/project/hirehunt/), [`openroles`](https://pypi.org/project/openroles/), [`jobdrop`](https://pypi.org/project/jobdrop/) y [Apify](https://apify.com/). Cada proyecto publica sus propias notas de uso. El scraping de Google Jobs, LinkedIn, Indeed y Glassdoor puede infringir las condiciones de servicio de esas plataformas. Apify traslada la petición a un servicio gestionado. Eso no cambia el riesgo legal.

## <a name="license"></a>Licencia

Sweepy se publica bajo la [Licencia MIT](../LICENSE).
