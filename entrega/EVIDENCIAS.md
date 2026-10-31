# Evidencias · ARSW-EQP-__

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

**Capturas:** _(agregar capturas del dashboard "ARSW-EQP-XX · Persistencia" con la ventana horaria visible, cubriendo 12:49–12:56 UTC)_

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

**1. ¿Por qué puede subir el contador de conflictos mientras baja la pérdida de cambios?**
Porque el 409 **es** el mecanismo que evita la pérdida. Antes, la segunda edición sobrescribía a la primera en silencio, sin conflictos registrados y con una edición perdida. Ahora el filtro por versión detecta la carrera, rechaza la escritura obsoleta y cuenta un conflicto. Más conflictos bajo concurrencia significan más pérdidas evitadas, no una falla del servidor.

**2. ¿Por qué el panel de caché no demuestra que una escritura fue autorizada correctamente?**
Porque mide aciertos de la caché de la **interfaz**, no la decisión de autorización. Después de la corrección, las escrituras no consultan la caché: van a la autoridad. Un hit ratio alto solo indica que la UI ahorró consultas a Gestión. Incluso un 100 % de aciertos podría estar sirviendo un permiso ya revocado. La corrección de la autorización se demuestra con el escenario `permiso_revocado` (403) y con `authority-down` (503).

**3. ¿Qué ve Grafana cuando Redis cae, pero la API sigue contestando 200?**
`up` de content sigue en 1, porque Prometheus puede leer `/metrics`, y las solicitudes siguen con 200. (En nuestra ventana, `up` sí baja a 0 en otros momentos: cuando content se reinicia y cuando management se detiene. Es decir, `up` refleja si el proceso responde, no si la funcionalidad está completa.) Lo que cambia es `lab_dependency_up{dependency="redis"}`, que pasa a 0, y el panel de presencia degradada, que sube. Esto muestra que `up=1` y HTTP 200 no equivalen a disponibilidad funcional completa: la API responde, pero una capacidad (presencia) no está disponible.

**4. ¿Por qué el P95 de k6 y el P95 del backend no tienen necesariamente el mismo valor?**
Miden cosas distintas con instrumentos distintos. k6 mide el recorrido completo desde el cliente (red de Docker, Nginx y servicio) con cada muestra exacta. El backend mide solo el procesamiento dentro del servicio y estima el percentil interpolando dentro de buckets fijos (`0.025, 0.05, 0.1…`). Con pocas muestras o latencias concentradas en un bucket ancho, `histogram_quantile` puede dar un valor bastante distinto al real. Aquí k6 reporta 11,4 ms y el backend estima ≈ 46–88 ms; la diferencia viene de la interpolación por buckets y de la ventana de `rate`, no de que un número sea "el correcto".

## Problemas pendientes

- **Panel de 5xx en 0 a pesar del 503 de `authority-down`:** la serie `status="503"` existe, pero `rate()` no muestra el incremento. Cuando un contador con una combinación de labels nueva aparece por primera vez con valor 1, Prometheus no tiene una muestra previa, así que `rate`/`increase` no cuentan ese primer evento. No es evidencia de ausencia de errores: el 503 está registrado en `authority-down-*.json`. Para verlo en el panel habría que provocar varios 503 seguidos o inicializar las series en 0 al arrancar el servicio.
- **Sin k6 del código base:** solo existe la medición con la solución. No se reporta una comparación inventada.
- **Ventana de revocación concurrente:** no está cubierta por las pruebas (ver ADR-001, Consecuencias).
