# Auditoría ITPlus — estado y pendientes

Registro vivo de la revisión completa del sistema (seguridad, pipeline de documentos/RAG/CRISP-DM, los 3 motores de chat, frontend, infraestructura) y de qué se ha arreglado. Actualizar esta tabla cada vez que se resuelva algo.

Rama de trabajo: `claude/managerial-assistant-fixes-1ihttl`

---

## ✅ Hecho

| # | Qué | Commit |
|---|---|---|
| 1 | `itplus/app/models/` no llegaba a git por un patrón roto en `.gitignore` (`models/` sin `/` inicial ignoraba la carpeta real de modelos SQLAlchemy en cualquier profundidad). Backend no arrancaba desde un clone limpio. | `14cd1dc` |
| 2 | Mismo patrón peligroso en `.gitignore` para `public/` (anclado a `/public/`, latente, aún no había reventado). | `14cd1dc` |
| 3 | Worker de Celery no importaba todos los modelos SQLAlchemy → `NoReferencedTableError` en el primer commit (la FK `documents.uploaded_by → users` no resolvía en el proceso aislado del worker). | `14cd1dc` (`itplus/app/models/__init__.py` ahora importa los 7 submódulos siempre) |
| 4 | `framer-motion` instalado y probado con un componente real (spring + `AnimatePresence`) contra React 19. | `3874ed1` |
| 5 | Animación de burbujas de chat (spring), chip de fuentes con pop, follow-ups con stagger — aplica a los 3 motores vía `ChatPageShell`. | `bfc95f6` |
| 6 | Dashboard: conteo animado en KPIs, tilt 3D en tarjetas de acceso. Historial: tab deslizante con `layoutId`. Documentos: filas con stagger, botón de subida magnético, chip de estado con pop, toast al terminar de indexar. | `2d5e8e7` |
| 7 | **Clúster de control de acceso** (ver detalle abajo) — middleware que fallaba abierto, IDOR en ITPlusBot y Asistente Gerencial, Consulta RAG sin login. | `a222518` — **confirmado pusheado**: `origin/claude/managerial-assistant-fixes-1ihttl` == HEAD local (verificado 2026-09-17 tras instalar git en la máquina local) |
| 8 | `frontend/public/` (favicon, iconos, assets de marca, `diag.html`, `mobile-check.html`) nunca se había commiteado — un clone limpio se quedaba sin ellos. | `1cdd1f4` |
| 9 | **Path traversal en subida de documentos** — `file.filename` ya no se usa para construir la ruta en disco; el nombre en disco ahora es siempre `{uuid}{extensión}` (extensión validada contra allowlist). También se cerró el bypass de validación cuando el archivo no tiene extensión, y ahora `ALLOWED_TYPES` sí se usa para rechazar `content_type` que no matchea ninguno de los permitidos (aceptando genéricos como `application/octet-stream`). Defensa en profundidad en `delete_document` (verifica que la ruta resuelta esté dentro de `upload_dir` antes de borrar). | `4dddd3c` |
| 10 | **Rollback faltante en el worker de indexación** — ahora se hace `db.rollback()` antes de intentar marcar `status="failed"`, y ese segundo intento también está protegido con try/except (si falla, se loguea en vez de perder la excepción original silenciosamente). | `4dddd3c` |
| 11 | **CSV con `;` (Chile/LatAm) rompía el pipeline** — `parse_csv` ahora usa `csv.Sniffer()` para detectar el delimitador real (`,`, `;`, tab o `\|`) en vez de asumir `,` siempre. | `4dddd3c` |
| 12 | **XLSX/CSV: `_split_text` fusionaba filas** — ya no colapsa `\n` a espacio; solo colapsa espacios/tabs repetidos y líneas vacías consecutivas. Esto es justo lo que `document_analytics.py` (`content.split("\n")`) y `vendor_rows.py` (`re.split(r"[\n\r]+", text)`) necesitan para no fusionar cifras de filas distintas. | `4dddd3c` |
| 13 | **`SECRET_KEY` por defecto sin validar** — `Settings` ahora falla al arrancar (`ValueError`) si `SECRET_KEY` es el valor por defecto o está vacía; si es muy corta (<16 chars) solo advierte por log (no se quiso adivinar un mínimo estricto sin poder ver el valor real). Verificado con un test aislado usando valores ficticios (no se leyó ni expuso el `.env` real en ningún momento). | `4dddd3c` |
| 14 | **Postgres/Redis expuestos en `0.0.0.0`** — ambos puertos ahora se publican como `127.0.0.1:puerto:puerto` en `docker-compose.yml`. api/worker siguen conectándose sin problema (usan la red interna de Docker, no el puerto publicado en el host); lo único que cambia es que ya no son alcanzables desde fuera del host. | `62c5300` |
| 15 | **Credenciales admin hardcodeadas sin aviso** — `seed_admin.py` ahora lee `ADMIN_EMAIL`/`ADMIN_PASSWORD` del entorno (con los mismos valores por defecto si no se definen) y loguea una advertencia explícita si detecta que se están usando los valores por defecto. Documentado en `.env.example` y en el README con aviso de que es solo para desarrollo. | `62c5300` |
| 16 | **3 motores de analítica podían dar cifras distintas para la misma pregunta** — causa raíz encontrada: `document_analytics.build_analytics_context()` concatenaba *siempre* el resumen de `tabular_insights.py` (calculado con regex propios sobre texto crudo) junto con los comparativos ya calculados por CRISP o por `build_analytics()`, cada uno con instrucción de "usar exactamente esta cifra". Ahora el resumen genérico de `tabular_insights` solo se usa como *fallback* cuando no hay comparativos/tablas ya calculados — si ya existe un cálculo estructurado, ese es la única fuente de verdad que se manda al LLM. | `62c5300` |
| 17 | **Documentos**: lectura del upload en chunks respetando el límite de tamaño (ya no carga el archivo completo en memoria antes de validar); verificación de "magic bytes" contra la extensión (sin dependencias nuevas — detecta un binario renombrado como `.pdf`/`.docx`/etc., o un `.txt`/`.csv` que en realidad es binario); la categoría se valida *antes* de escribir el archivo a disco (ya no queda huérfano); `reindex` devuelve 409 si el documento ya está `pending`/`processing` (evita el doble-clic → chunks duplicados); el `.duckdb` y el `_import.csv` temporal de CRISP ahora se borran al borrar el documento (antes nunca se limpiaban). | `26b8ebd` |
| 18 | **ITPlusBot sin manejo de errores del LLM** — si el proveedor (Groq) falla, ahora se hace commit del mensaje del usuario (antes se perdía al hacer rollback implícito) y se devuelve un 503 explícito (`LLMUnavailableError`) en vez de un 500 genérico. | `26b8ebd` |
| 19 | **Sin timeout en las llamadas al proveedor LLM** — nuevo setting `AI_TIMEOUT_SECONDS` (default 60s) pasado al cliente OpenAI SDK; antes una llamada colgada podía agotar el pool de threads de la API. | `26b8ebd` |
| 20 | **Resumen con error se quedaba así para siempre** — si el LLM falla generando el resumen, ya no se persiste un `Summary` con el mensaje de error dentro (eso bloqueaba cualquier reintento futuro, porque el chequeo de "ya existe" lo trataba como válido); ahora no se guarda nada y la próxima llamada a `generate_summary()` lo vuelve a intentar de verdad. | `26b8ebd` |
| 21 | **Historial sin paginación real** — `history_service.list_chats()` ya no trunca conversaciones/logs *antes* de fusionar/deduplicar; ahora fusiona todo, calcula el `total` real, y aplica `offset`/`limit` al final. El endpoint `/history/chats` acepta `limit`/`offset`. Esto también corrige el contador de chats mostrado en el Dashboard (`history.total`), que antes subestimaba a cualquier usuario con más chats que el límite interno. | `26b8ebd` |
| 22 | **Sin React Error Boundary** — nuevo `components/ErrorBoundary.tsx` envolviendo toda la app en `App.tsx`; un error de render ya no deja pantalla en blanco total, muestra una pantalla de recuperación con botón "Volver al inicio". | `26b8ebd` |
| 23 | **`AuthContext` no limpiaba el `user` en memoria** — si `getMe()` fallaba al arrancar, ahora se llama `setUser(null)` además de `clearAuth()`; antes la UI seguía mostrando la sesión como válida con el token ya invalidado. | `26b8ebd` |
| 24 | **`streamAssistantMessage` no pasaba por el interceptor de 401** — usa `fetch()` manual (necesario para SSE) que no pasa por axios; ahora detecta un 401 explícitamente y hace el mismo `clearAuth()` + redirect a `/login?expired=1` que el resto de la app, en vez de mostrar "no se pudo conectar". | `26b8ebd` |
| 25 | **`itplus/requirements.txt` no tenía `duckdb`** — ahora coincide con el `requirements.txt` de la raíz; el análisis CRISP de documentos tabulares ya no rompe en un setup local sin Docker. | `26b8ebd` |
| 26 | **`init_db()` sin lock ante arranques concurrentes** — se llama 2 veces por instancia (`seed_admin.py` + evento `startup`) y las migraciones a mano (`ALTER TABLE IF NOT EXISTS`) podían pisarse entre réplicas. Ahora `init_db()` toma un `pg_advisory_lock` de Postgres al inicio y lo libera al final, serializando la inicialización entre procesos. *(No se migró a Alembic todavía — sigue pendiente si se quiere un sistema de migraciones real.)* | `26b8ebd` |
| 27 | **Sin `healthcheck`/`restart` en `api`/`worker`/`frontend`** — los 5 servicios de `docker-compose.yml` ahora tienen `restart: unless-stopped`; `api` chequea `/api/v1/health`, `worker` usa `celery inspect ping`, `frontend` usa `wget --spider` contra nginx. | `26b8ebd` |
| 28 | **`nginx.conf` sin `client_max_body_size`** — ahora en 25m (por encima de `MAX_UPLOAD_MB=20` default); antes cualquier archivo >1MB detrás de nginx en producción daba 413 aunque en desarrollo funcionara. | `26b8ebd` |
| 29 | **Sin `.dockerignore` en la raíz** — nuevo `.dockerignore` excluyendo `.git/`, `uploads/`, `node_modules/`, `.env`, instaladores `.exe` sueltos, etc. del contexto de build (`context: .` en `docker-compose.yml` lo mandaba todo antes). | `26b8ebd` |

### Detalle del punto 7 (control de acceso)
- `run_itplus.py` — `ModulePermissionMiddleware` ya no deja pasar peticiones sin token, con token inválido, o hacia rutas no mapeadas: ahora responde 401.
- `chat_bot.py` (ITPlusBot) y `chat_query.py` (Consulta RAG) — ya no usan `get_optional_user` (eliminado de `deps.py`, quedó sin uso); ahora exigen `get_current_user` en los 5 + 1 endpoints.
- `ConversationService.get_conversation` / `send_message` / `finish_conversation_manually`, y `SummaryService.get_summary` — ahora filtran por `user_id`, no solo por `conversation_id`.
- `AssistantService._prepare_turn` (Asistente Gerencial) — ahora compara `conversation.user_id != user_id` antes de tocar la conversación, igual que ya hacía `close_conversation`.
- Verificado en vivo: 401 sin token/con token basura en los 3 motores; un usuario ("victima") no puede ser leído/escrito por otro ("admin") en ITPlusBot ni en el Asistente Gerencial (404 en ambos, y en el Asistente se bloquea *antes* de llamar al LLM); acceso legítimo del propio dueño, `/auth/me`, historial y navegación completa del frontend siguen funcionando sin errores.
- **Nota de producto sin resolver**: con este fix, un Administrador tampoco puede leer la conversación de otro usuario (antes nadie podía). Si se quiere que admin tenga visibilidad de auditoría, es un permiso a agregar deliberadamente.

---

## 🔴 Pendiente — Crítico

Sin ítems nuevos sin tocar en esta sesión. Los 3 puntos que estaban aquí (motores de analítica con cifras distintas, credenciales admin, Postgres/Redis expuestos) se movieron a "Hecho" (puntos 14-16) — ver notas de alcance abajo.

**Nota de alcance sobre el punto 16 (motores de analítica):** el fix aplicado evita que se manden *dos* bloques con cifras potencialmente distintas al LLM para el mismo cálculo, pero no unifica los 3 motores en un solo pipeline de extracción — si CRISP y `build_analytics()` alguna vez corren en paralelo para la misma pregunta (no debería pasar según la lógica actual de `assistant.py`, pero no hay un test que lo garantice), seguiría existiendo la posibilidad de divergencia entre esos dos. Vale la pena un test de integración que lo verifique antes de considerar esto 100% cerrado.

---

## 🟠 Pendiente — Alto

Todo lo que estaba listado aquí se resolvió en esta sesión (ver puntos 17-29 en "Hecho"), **excepto**:

- [ ] **Borrar/reindexar documentos no verifica dueño ni rol adicional** — cualquier usuario con acceso al módulo "documentos" puede borrar documentos de otros (`documents.py`). *(Es una decisión de producto, no un bug: puede ser diseño intencional de base de conocimiento compartida — confirmar con el usuario antes de restringir.)*
- [ ] Condición de carrera al mandar 2 mensajes rápido a la misma conversación (respuestas que no se ven entre sí). *(No tocado — requiere pensar en un lock por conversación o deduplicar en el frontend.)*
- [ ] Streaming: una respuesta cortada a mitad se persiste como si fuera completa, sin indicárselo al cliente — `assistant.py:436-457`. *(No tocado.)*
- [ ] Llamadas API duplicadas en cada navegación (`Layout.tsx` no usa react-query, a diferencia de Roles/Usuarios/Sesiones que sí). *(No tocado.)*
- [ ] JWT en `localStorage` sin CSP definido. *(No tocado — requiere definir una política de CSP a nivel de nginx/index.html.)*
- [ ] `alembic` instalado pero nunca usado — el punto 26 (advisory lock) mitiga la condición de carrera concreta, pero no migra el proyecto a un sistema de migraciones real con versionado. *(Alcance mayor, no abordado.)*

---

## 🟡 Pendiente — Medio / 🟢 Bajo

Resumen agrupado (detalle completo en el historial de la conversación / se puede volver a listar si se necesita):

- **Accesibilidad**: `CommandPalette` sin focus trap ni semántica ARIA; tabs de `UsuariosPage` sin `role="tablist"` ni sync con la URL; inputs de búsqueda dependen solo del `placeholder`.
- **UX inconsistente**: mensajes de error genéricos/distintos entre pantallas de chat equivalentes; flujo de "¿Olvidaste tu contraseña?" completamente simulado (no llama a ningún API); `azureLogout()` no cierra la sesión SSO real.
- **Código muerto confirmado, candidato a borrar**: `frontend/src/pages/itplus/*`, `components/ItplusLayout.tsx`, `components/ItplusProtectedRoute.tsx`, `contexts/ItplusAuthContext.tsx` (ninguna referencia activa); `require_permiso()` en `deps.py` (nunca usado); `AssistantService.get_active_conversation` (nunca llamado); `_VENDOR_ROW_RE` en `document_analytics.py`.
- **Duplicación**: `_build_context`/`_hits_to_sources` casi idénticos entre `conversation.py` y `rag.py`; `MetricCard` duplicado en `UsuariosPage.tsx` y `SessionsPanel.tsx`; 3 listas de categorías de conocimiento mantenidas a mano y desincronizadas (`phases.py`).
- **Parsing de datos**: `_parse_float` no soporta formato numérico chileno con separador de miles (repetido en 3 archivos); `errors="ignore"` en decodificación de texto pierde tildes/ñ en CSVs Latin-1/Windows-1252; nombre de hoja Excel puramente numérico se confunde con número de página.
- **Otros**: `Claude Setup.exe` (6.7 MB) sigue commiteado en la raíz sin ningún propósito; Swagger/ReDoc siempre públicos en cualquier entorno; `settings.debug` no hace nada (decorativo); enumeración de usuarios por canal lateral de tiempo en `/auth/login`; política de contraseñas inexistente (sin longitud mínima).

---

## ⚠️ Nota de la sesión 2026-09-17

En la máquina local (Windows) no había `git` instalado — se instaló vía `winget`. El `git push` automático a través de una shell se cuelga a veces esperando una ventana interactiva de Git Credential Manager que hay que completar manualmente; suele funcionar al reintentar una vez la sesión ya quedó cacheada. Commits de esta sesión: `1cdd1f4`, `4dddd3c`, `f2b9ee1`, `62c5300` (primera ronda, puntos 1-16) y `26b8ebd` (segunda ronda, puntos 17-29) — **verificar con `git log origin/claude/managerial-assistant-fixes-1ihttl -1` que `26b8ebd` (o el commit posterior de este mismo mensaje actualizando AUDITORIA.md) realmente llegó a remoto** antes de asumir que está pusheado.

**Verificación de esta ronda:** todo el backend tocado pasa `python -m py_compile`; el frontend tocado pasa `tsc --noEmit` y `eslint` sin errores nuevos (los 2 errores de lint preexistentes en `AuthContext.tsx` no son de esta sesión); `docker compose config` valida el `docker-compose.yml` actualizado. No se corrieron tests de integración reales (requieren levantar los contenedores) — recomendable antes de considerar esto verificado en caliente.

**Contenedores reconstruidos y verificados en caliente (2026-09-18):** se corrió `docker compose build && docker compose up -d`. Los 5 servicios quedaron `healthy`. Al probar el healthcheck de `frontend` en vivo se encontró un bug real: `wget --spider http://localhost/` resuelve `localhost` a `::1` (IPv6) primero y nginx solo escucha en `0.0.0.0` → siempre daba "connection refused" aunque nginx funcionara perfecto. Se corrigió usando `http://127.0.0.1/` explícito (commit `3ae527f`), y de paso se subió el `start_period` del healthcheck de `api` a 90s (el arranque en frío real —seed_admin + init_db + primera carga del modelo de embeddings contra HuggingFace— tardó ~95s, más que el `start_period` original de 20s). Smoke test post-fix: `GET /api/v1/health` → `{"status":"ok","checks":{"database":"ok","redis":"ok"}}`; login de admin funcionando; `GET /history/chats?limit=5&offset=5` devuelve una página distinta con `total: 27` consistente (confirma el fix de paginación real).

## Cómo retomar esto en una sesión nueva

1. `git log --oneline -10` en la rama `claude/managerial-assistant-fixes-1ihttl` para ver qué de la tabla "Hecho" ya está en GitHub (ojo: en esta sesión un fix se perdió una vez porque el push falló y el contenedor se cerró antes de reintentarlo — **siempre confirmar con `git log origin/<rama> -1` que lo que se cree pusheado realmente está en remoto**).
2. Este archivo es la fuente de verdad de qué falta — no repetir la auditoría completa desde cero, solo actualizar esta tabla a medida que se resuelva algo.
