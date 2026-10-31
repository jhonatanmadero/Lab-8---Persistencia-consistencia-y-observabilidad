# Evidencias · ARSW-EQP-07

## Entorno

- **Sistema operativo:** Windows 11 Home Single Language (10.0.26300), comandos ejecutados desde Git Bash
- **CPU:** 13th Gen Intel Core i5-13450HX (16 hilos visibles para Docker)
- **RAM visible para Docker:** ~15,5 GiB (Docker Desktop, backend WSL2)
- **Versiones:** Docker 29.6.1 · Docker Compose v5.2.0
- **Ajuste local:** el puerto 8080 estaba bloqueado por Windows (`bind: forbidden by its access permissions`, rango reservado), así que el frontend se publicó en `WEB_PORT=18080`. Las herramientas internas usan la red de Compose y no se ven afectadas.
- **Ajuste Git Bash:** `MSYS_NO_PATHCONV=1` al ejecutar `psql -f /lab/evidence.sql`; sin esa variable, Git Bash convierte la ruta del contenedor en una ruta de Windows.

## Registro

Todas las horas están en **UTC** del 2026-10-31. Para los resultados de `tools`, la hora proviene del nombre del archivo (momento en que se guardó) y del registro de comandos de la sesión.

| Experimento | Inicio / fin y zona horaria | Archivo / captura | Resultado observado | Interpretación |
|---|---|---|---|---|
| Baseline | ≈12:49:15 – 12:49:37 UTC | `evidencias/baseline-20261031T124937796770Z.json` | `arranque` true; `ediciones_concurrentes`, `permiso_revocado` y `presencia_expira` en **false**; código de salida 0 | Defectos de la base: dos PUT con la misma versión guardan ambos (edición perdida); la caché permite escribir a Luis revocado; la presencia no expira |
| Restricciones SQL y rollback | 12:57:51 – 12:57:52 UTC | `evidencias/sql-evidence.txt` | Revocación de Luis visible dentro de la transacción (`can_edit=f`) y revertida tras `ROLLBACK` (`t`). `INSERT` duplicado → `memberships_pkey`; `INSERT` con usuario inexistente → `memberships_user_id_fkey` | La PK compuesta garantiza una sola membresía por (tablero, usuario); la FK impide membresías de usuarios inexistentes; la transacción garantiza que un cambio no confirmado no se observa fuera de ella |
| Acceptance corregido | ≈12:50:00 – 12:50:18 UTC (repetido después de restaurar las dependencias, ≈12:51, también con código 0) | `evidencias/acceptance-20261031T125018954672Z.json` | Los cuatro escenarios en **true**, código de salida 0 | El control optimista produce exactamente un 200 y un 409; la escritura consulta la autoridad y rechaza a Luis con 403; la presencia expira a los 20 s |
| Redis detenido y recuperación | ≈12:50:30 – 12:50:44 UTC; `redis-cli ping` → `PONG` después de `start` | `evidencias/redis-down-20261031T125043922100Z.json` | `edit_status: 200`, `presence_status: 200`, `{"available":false,"ttl_seconds":null}` | Degradación controlada: la presencia deja de estar disponible y lo informa sin mentir; el contenido sigue funcionando porque Redis no es fuente de verdad |
| Autoridad detenida y recuperación | ≈12:50:47 – 12:50:55 UTC; Gestión reiniciada después | `evidencias/authority-down-20261031T125054992778Z.json` | `edit_status: 503`, "No se puede validar el permiso; escritura no autorizada" | No disponibilidad deliberada (*fail closed*): aunque exista un permiso en caché, no se escribe sin confirmar con la autoridad |
| Carga k6 | 12:53:01 – 12:54:51 UTC | `evidencias/k6-carga-summary-solucion.json` | 1974 req (19,7 req/s), `http_req_failed` 0 %, checks 100 %, P95 cliente **11,4 ms**, máx. 37,5 ms | Umbrales de clase cumplidos (P95 < 500 ms, errores < 1 %). Solo hay una medición, con la solución: la carga es de solo lectura y no se conservó una corrida con el código base |
| Eventos para paneles | 12:55:11 – 12:55:37 UTC | Dashboard (captura) | Dos PUT con versión 1 → 200 y 409; 3 consultas de permiso; 3 heartbeats con Redis detenido → `available:false`; Redis restaurado (`PONG`) | Generan muestras para los paneles de conflictos, caché y presencia degradada |

### Segunda ventana con capturas · 13:38 – 13:47 UTC (08:38 – 08:47 hora de Colombia)

Los experimentos se repitieron en una segunda ventana para tomar capturas PNG con la hora visible. Las capturas se tomaron con Microsoft Edge (headless, mediante Playwright) en zona horaria `America/Bogota`. El registro de cada acción y su respuesta está en `evidencias/capturas/registro-capturas.txt`.

| Experimento | Inicio / fin (UTC) | Archivo / captura | Resultado observado |
|---|---|---|---|
| Redis detenido (prueba automatizada) | ≈13:38:36 – 13:38:50 | `evidencias/redis-down-20261031T133849954175Z.json` | `degradacion_redis` true |
| Autoridad detenida (prueba automatizada) | ≈13:39:00 – 13:39:10 | `evidencias/authority-down-20261031T133909921367Z.json` | `autoridad_no_disponible` true |
| Acceptance después de restaurar | ≈13:39:30 – 13:39:48 | `evidencias/acceptance-20261031T133948069760Z.json` | cuatro escenarios en true |
| Carga k6 | 13:39:48 – 13:41:30 | `evidencias/k6-carga-summary-capturas.json` | 1966 req (19,7 req/s), 0 % errores, checks 100 %, P95 cliente **11,5 ms** |
| Exp. 1 · dos pestañas | 13:44:28 – 13:44:35 | `capturas/01-dos-pestanas-ana-200.png`, `capturas/02-dos-pestanas-luis-409.png` | Ana (pestaña 1) guarda: **200**, versión 1 → 2. Luis (pestaña 2, aún con versión 1): **409** "Versión obsoleta… recargue antes de editar" |
| Exp. 2 · Redis detenido en el frontend | 13:44:38 – 13:44:54 | `capturas/03-redis-caido-presencia-degradada.png`, `capturas/04-redis-caido-edicion-200.png` | Presencia: **200** `{"available":false,"ttl_seconds":null}`. Edición: **200**, versión 2 |
| Exp. 3 · autoridad detenida con permiso en caché | 13:45:01 – 13:45:18 | `capturas/05-autoridad-caida-503.png` | Permiso consultado dos veces (`can_edit:true`, en caché). Con Gestión detenida, el PUT responde **503** "No se puede validar el permiso; escritura no autorizada" |
| Acceptance final | ≈13:45:45 – 13:46:02 | `evidencias/acceptance-20261031T134602356463Z.json` | cuatro escenarios en true; `redis-cli ping` → `PONG` |
| Dashboard | captura 13:46:52 (últimos 30 min) | `capturas/06-grafana-dashboard-completo.png` | Los 8 paneles con datos (ver abajo) |
| Targets de Prometheus | 13:46:52 | `capturas/07-prometheus-targets.png` | content y management **UP** tras la restauración |

Un 409 o un 503 esperado no es una caída: el servidor respondió y aplicó la regla de negocio. El 409 evita una edición perdida; el 503 evita escribir con un permiso que no se pudo verificar.

## Preguntas de los fallos controlados (Bloque C)

**¿Qué funcionalidad degradó de forma controlada?**
La **presencia**. Con Redis detenido, el heartbeat respondió HTTP 200 con `{"available":false,"ttl_seconds":null}`: el sistema informa que no pudo registrar la presencia, en vez de fingir que la registró o de fallar con 503. La métrica `lab_degraded_total{feature="presence"}` subió (capturas 03 y 06). La caché de permisos de la interfaz también se degrada: con Redis caído cuenta un `error` y consulta directamente a Gestión. Mientras tanto, la edición siguió con 200 (captura 04), porque Redis no participa en la garantía de escritura.

**¿Cuál dejó de estar disponible deliberadamente?**
La **edición del tablero** cuando Gestión (la autoridad de permisos) no responde. El PUT respondió **503** "No se puede validar el permiso; escritura no autorizada" aunque había un permiso `can_edit:true` en caché (captura 05). Es una decisión de *fail closed*: preferimos no aceptar escrituras antes que aceptarlas con una concesión que quizás ya fue revocada. La lectura del tablero (GET) siguió disponible.

**¿Qué garantía protege ese comportamiento?**
- Para la escritura: **solo la autoridad durable (PostgreSQL vía Gestión) puede autorizar**. `permission_for_write` llama a `authoritative_permission` y deja propagar su 503; nunca convierte un error en permiso concedido. Así, una escritura que comienza después de confirmada una revocación recibe 403, y sin autoridad recibe 503, nunca 200.
- Para la presencia: Redis se trata como **capacidad opcional**. `touch_presence` captura solo `RedisError` y devuelve `False`, así que una falla de Redis no se propaga al flujo principal y tampoco se informa una presencia que no existe.
- Para el contenido: el **control optimista de versión** sigue vigente en cualquier escenario, porque está en la misma operación atómica de MongoDB.

**¿Qué cambia si la falla es MongoDB?**
MongoDB es la **fuente de verdad del contenido**, así que no hay degradación posible para el tablero: lectura y edición responden **503** "MongoDB no disponible" (el código captura `PyMongoError`). El cliente tiene `serverSelectionTimeoutMS=1500`, así que cada petición espera hasta ≈1,5 s antes del 503; eso subiría el P95 y la tasa de 5xx en el dashboard, y `lab_dependency_up{dependency="mongo"}` bajaría a 0. La presencia (Redis) y la consulta de permisos (Gestión/PostgreSQL) seguirían funcionando, pero sin contenido no hay nada útil que editar. A diferencia de Redis, aquí no se puede degradar de forma útil: perder la fuente de verdad implica perder la funcionalidad. *Esta respuesta se basa en el código del servicio; no se ejecutó un experimento con MongoDB detenido.*

## Observabilidad

Dashboard exportado en `entrega/dashboard.json` (uid `arsw-eqp-persistencia`, 8 paneles). Valores observados en Prometheus en la ventana 12:41–12:56 UTC:

| Panel | Observación |
|---|---|
| Servicios observables (`up`) | Ambos en 1 con Redis caído. Bajan a 0 solo cuando el proceso no responde a Prometheus: content durante su reinicio para aplicar los cambios (≈12:50) y management mientras estuvo detenido en `authority-down` |
| Solicitudes/s | Pico ≈ 3,4 req/s en una serie durante k6 (tasa por servicio con ventana de 1 min) |
| P95 backend | ≈ 46–88 ms según servicio (estimación por buckets) |
| Errores técnicos 5xx | Serie presente, tasa observada 0 (ver Problemas pendientes) |
| Dependencias | `content → redis` baja a 0 en los experimentos con Redis detenido; `content → management` baja a 0 durante `authority-down`; `content → mongo` y `management → postgres` se mantienen en 1 |
| Aciertos de caché | Hasta ≈ 0,26 |
| Conflictos | > 0 tras el PUT con versión obsoleta |
| Presencia degradada | > 0 tras los heartbeats con Redis detenido |

En la segunda ventana (captura `06-grafana-dashboard-completo.png`, 08:17–08:47 hora de Colombia):

| Panel | Observación |
|---|---|
| `up` | Dos caídas breves a 0 de management (≈08:39 y ≈08:45), justo cuando se detuvo para el experimento de autoridad |
| Solicitudes/s | Pico ≈ 24 req/s en content durante k6 (08:40–08:41) |
| P95 backend | Picos ≈ 4 s durante los experimentos de falla: con Redis detenido, cada operación espera el timeout del cliente Redis (0,3 s), y con Gestión detenida la validación de permiso espera el timeout HTTP de 2 s (`httpx`, `timeout=2`). Como esas latencias caen en el bucket 2–5 s, `histogram_quantile` interpola ≈ 4 s. Durante k6, con todo sano, vuelve a valores bajos. Fallar cerrado tiene un costo de latencia, no solo de disponibilidad |
| Errores 5xx | **Visibles**: ≈ 0,036 req/s (≈08:39) y ≈ 0,018 req/s (≈08:45), que corresponden a los 503 deliberados sin autoridad |
| Dependencias | `content → redis` y `content → management` bajan a 0 en sus experimentos; mongo y postgres se mantienen en 1 |
| Aciertos de caché | Sube hasta 100 % al repetir consultas de permiso dentro del TTL de 60 s |
| Conflictos | Picos ≈ 0,02–0,035/s tras los 409 de acceptance y de las dos pestañas |
| Presencia degradada | Picos con Redis detenido, aunque las respuestas fueron HTTP 200 |

**1. ¿Por qué puede subir el contador de conflictos mientras baja la pérdida de cambios?**
Porque el 409 **es** el mecanismo que evita la pérdida. Antes, la segunda edición sobrescribía a la primera en silencio, sin conflictos registrados y con una edición perdida. Ahora el filtro por versión detecta la carrera, rechaza la escritura obsoleta y cuenta un conflicto. Más conflictos bajo concurrencia significan más pérdidas evitadas, no una falla del servidor.

**2. ¿Por qué el panel de caché no demuestra que una escritura fue autorizada correctamente?**
Porque mide aciertos de la caché de la **interfaz**, no la decisión de autorización. Después de la corrección, las escrituras no consultan la caché: van a la autoridad. Un hit ratio alto solo indica que la UI ahorró consultas a Gestión. Incluso un 100 % de aciertos podría estar sirviendo un permiso ya revocado. La corrección de la autorización se demuestra con el escenario `permiso_revocado` (403) y con `authority-down` (503).

**3. ¿Qué ve Grafana cuando Redis cae, pero la API sigue contestando 200?**
`up` de content sigue en 1, porque Prometheus puede leer `/metrics`, y las solicitudes siguen con 200. (En nuestra ventana, `up` sí baja a 0 en otros momentos: cuando content se reinicia y cuando management se detiene. Es decir, `up` refleja si el proceso responde, no si la funcionalidad está completa.) Lo que cambia es `lab_dependency_up{dependency="redis"}`, que pasa a 0, y el panel de presencia degradada, que sube. Esto muestra que `up=1` y HTTP 200 no equivalen a disponibilidad funcional completa: la API responde, pero una capacidad (presencia) no está disponible.

**4. ¿Por qué el P95 de k6 y el P95 del backend no tienen necesariamente el mismo valor?**
Miden cosas distintas con instrumentos distintos. k6 mide el recorrido completo desde el cliente (red de Docker, Nginx y servicio) con cada muestra exacta. El backend mide solo el procesamiento dentro del servicio y estima el percentil interpolando dentro de buckets fijos (`0.025, 0.05, 0.1…`). Con pocas muestras o latencias concentradas en un bucket ancho, `histogram_quantile` puede dar un valor bastante distinto al real. Aquí k6 reporta 11,4 ms y el backend estima ≈ 46–88 ms; la diferencia viene de la interpolación por buckets y de la ventana de `rate`, no de que un número sea "el correcto".

## Problemas pendientes

- **Panel de 5xx en 0 en la primera ventana a pesar del 503 de `authority-down`:** cuando un contador con una combinación de labels nueva aparece por primera vez con valor 1, Prometheus no tiene una muestra previa, así que `rate`/`increase` no cuentan ese primer evento. En la segunda ventana la serie `status="503"` ya existía y el panel **sí** muestra los 503 (captura 06), lo que confirma la explicación. La ausencia de muestras no es evidencia de ausencia de errores. Una mejora sería inicializar las series en 0 al arrancar el servicio.
- **Sin k6 del código base:** solo existe la medición con la solución. No se reporta una comparación inventada.
- **Ventana de revocación concurrente:** no está cubierta por las pruebas (ver ADR-001, Consecuencias).
