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
| 8 | `frontend/public/` (favicon, iconos, assets de marca, `diag.html`, `mobile-check.html`) nunca se había commiteado — un clone limpio se quedaba sin ellos. | `1cdd1f4` (local, **pendiente de push manual**, ver nota abajo) |
| 9 | **Path traversal en subida de documentos** — `file.filename` ya no se usa para construir la ruta en disco; el nombre en disco ahora es siempre `{uuid}{extensión}` (extensión validada contra allowlist). También se cerró el bypass de validación cuando el archivo no tiene extensión, y ahora `ALLOWED_TYPES` sí se usa para rechazar `content_type` que no matchea ninguno de los permitidos (aceptando genéricos como `application/octet-stream`). Defensa en profundidad en `delete_document` (verifica que la ruta resuelta esté dentro de `upload_dir` antes de borrar). | local, pendiente de push |
| 10 | **Rollback faltante en el worker de indexación** — ahora se hace `db.rollback()` antes de intentar marcar `status="failed"`, y ese segundo intento también está protegido con try/except (si falla, se loguea en vez de perder la excepción original silenciosamente). | local, pendiente de push |
| 11 | **CSV con `;` (Chile/LatAm) rompía el pipeline** — `parse_csv` ahora usa `csv.Sniffer()` para detectar el delimitador real (`,`, `;`, tab o `\|`) en vez de asumir `,` siempre. | local, pendiente de push |
| 12 | **XLSX/CSV: `_split_text` fusionaba filas** — ya no colapsa `\n` a espacio; solo colapsa espacios/tabs repetidos y líneas vacías consecutivas. Esto es justo lo que `document_analytics.py` (`content.split("\n")`) y `vendor_rows.py` (`re.split(r"[\n\r]+", text)`) necesitan para no fusionar cifras de filas distintas. | local, pendiente de push |
| 13 | **`SECRET_KEY` por defecto sin validar** — `Settings` ahora falla al arrancar (`ValueError`) si `SECRET_KEY` es el valor por defecto o está vacía; si es muy corta (<16 chars) solo advierte por log (no se quiso adivinar un mínimo estricto sin poder ver el valor real). Verificado con un test aislado usando valores ficticios (no se leyó ni expuso el `.env` real en ningún momento). | local, pendiente de push |

### Detalle del punto 7 (control de acceso)
- `run_itplus.py` — `ModulePermissionMiddleware` ya no deja pasar peticiones sin token, con token inválido, o hacia rutas no mapeadas: ahora responde 401.
- `chat_bot.py` (ITPlusBot) y `chat_query.py` (Consulta RAG) — ya no usan `get_optional_user` (eliminado de `deps.py`, quedó sin uso); ahora exigen `get_current_user` en los 5 + 1 endpoints.
- `ConversationService.get_conversation` / `send_message` / `finish_conversation_manually`, y `SummaryService.get_summary` — ahora filtran por `user_id`, no solo por `conversation_id`.
- `AssistantService._prepare_turn` (Asistente Gerencial) — ahora compara `conversation.user_id != user_id` antes de tocar la conversación, igual que ya hacía `close_conversation`.
- Verificado en vivo: 401 sin token/con token basura en los 3 motores; un usuario ("victima") no puede ser leído/escrito por otro ("admin") en ITPlusBot ni en el Asistente Gerencial (404 en ambos, y en el Asistente se bloquea *antes* de llamar al LLM); acceso legítimo del propio dueño, `/auth/me`, historial y navegación completa del frontend siguen funcionando sin errores.
- **Nota de producto sin resolver**: con este fix, un Administrador tampoco puede leer la conversación de otro usuario (antes nadie podía). Si se quiere que admin tenga visibilidad de auditoría, es un permiso a agregar deliberadamente.

---

## 🔴 Pendiente — Crítico

### Confiabilidad de las cifras (toca directo el pedido original del usuario)
- [ ] **Tres motores de analítica (CRISP-DM, `document_analytics.py`, `tabular_insights.py`) pueden calcular cifras distintas para la misma pregunta y mandar ambas al LLM en el mismo prompt**, cada una con instrucción de "usar exactamente esta cifra". *(Pendiente — requiere decidir cuál motor es la fuente de verdad o unificar cálculos; no se tocó en esta sesión.)*

### Seguridad / configuración
- [ ] **Credenciales admin (`admin@itplus.cl`/`admin123`) se siembran automáticamente en cada arranque** y están documentadas en el README sin aviso de rotarlas — `seed_admin.py`, `docker-compose.yml:48`.
- [ ] **Postgres y Redis expuestos en `0.0.0.0` sin autenticación real** si el host tiene IP pública — contraseña Postgres = usuario, Redis sin password — `docker-compose.yml:8-9,20-21`.

---

## 🟠 Pendiente — Alto

**Documentos / archivos**
- [ ] Borrar/reindexar documentos no verifica dueño ni rol adicional — cualquier usuario con acceso al módulo "documentos" puede borrar documentos de otros (`documents.py:123-157`). *(Puede ser diseño intencional de base de conocimiento compartida — confirmar con el usuario antes de restringir.)*
- [ ] Validación de tipo de archivo evadible: el bypass "sin extensión" y el `content_type` sin usar ya se arreglaron (ver tabla "Hecho", punto 9); **sigue faltando verificación real de magic bytes** (un `.pdf` con contenido arbitrario dentro sigue pasando si la extensión y el content-type declarado coinciden).
- [ ] Lectura completa del archivo en memoria antes de validar tamaño máximo (riesgo de agotar memoria).
- [ ] Archivos `.duckdb`/`_import.csv` del análisis CRISP nunca se limpian al borrar el documento — fuga de disco.
- [ ] Race condition en reindexado concurrente (doble clic → chunks duplicados o borrados a medias).
- [ ] Categoría inválida deja el archivo huérfano en disco (se valida después de escribirlo).

**Chat / LLM**
- [ ] ITPlusBot sin manejo de errores del LLM — si Groq falla, se pierde el mensaje del usuario y da 500 (`conversation.py:241`).
- [ ] Sin timeout configurado en las llamadas al proveedor LLM — puede agotar el pool de threads de toda la API bajo carga (`llm_provider.py`).
- [ ] Generación de resúmenes: si el LLM falla, el placeholder de error queda para siempre como "el resumen" (nunca se reintenta) — `summary.py:29-38`.
- [ ] Condición de carrera al mandar 2 mensajes rápido a la misma conversación (respuestas que no se ven entre sí).
- [ ] Streaming: una respuesta cortada a mitad se persiste como si fuera completa, sin indicárselo al cliente — `assistant.py:436-457`.
- [ ] Historial sin paginación real; `total` no refleja el total real de chats del usuario — `history.py:25-40`.

**Frontend**
- [ ] **Sin ningún React Error Boundary** — un error de render después del arranque deja pantalla en blanco total sin recuperación.
- [ ] `AuthContext.tsx:52` — si `getMe()` falla al arrancar, se limpia `localStorage` pero no el estado `user` en memoria → UI sigue mostrando sesión inválida.
- [ ] `streamAssistantMessage` usa `fetch()` manual que no pasa por el interceptor de 401 del cliente axios — token expirado durante streaming da "no se pudo conectar" en vez de redirigir a login.
- [ ] Llamadas API duplicadas en cada navegación (`Layout.tsx` no usa react-query, a diferencia de Roles/Usuarios/Sesiones que sí).
- [ ] JWT en `localStorage` sin CSP definido.

**Infraestructura**
- [ ] Los dos `requirements.txt` divergen — falta `duckdb` en `itplus/requirements.txt`, que es el que usa el README para desarrollo local sin Docker → rompe justo el análisis de documentos.
- [ ] `alembic` instalado pero nunca usado — migraciones a mano con `ALTER TABLE IF NOT EXISTS` sin lock, riesgo de condición de carrera en arranques concurrentes (`init_db()` se llama 2 veces por arranque: desde `seed_admin.py` y desde el evento `startup`).
- [ ] Sin `healthcheck`/`restart` en los contenedores `api`/`worker`/`frontend` — si `init_db()` falla, el contenedor muere y nadie lo reinicia.
- [ ] `nginx.conf` sin `client_max_body_size` — subir un archivo >1MB en producción (detrás de nginx) da 413, aunque en desarrollo funcione.
- [ ] Sin `.dockerignore` en la raíz — el de `frontend/` no aplica a los builds reales (`context: .`), puede terminar copiando `.git/`, `uploads/`, `Claude Setup.exe` al contexto de build.

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

En la máquina local (Windows) no había `git` instalado — se instaló vía `winget`. El `git push` automático a través de una shell se queda colgado esperando una ventana interactiva de Git Credential Manager que el agente no puede completar. **Los commits de esta sesión quedaron listos localmente pero sin pushear** — hay que hacer `git push origin claude/managerial-assistant-fixes-1ihttl` manualmente (por ejemplo desde GitHub Desktop, que ya tiene sesión iniciada como `shiiiro0`) y luego confirmar con `git log origin/claude/managerial-assistant-fixes-1ihttl -1`.

## Cómo retomar esto en una sesión nueva

1. `git log --oneline -10` en la rama `claude/managerial-assistant-fixes-1ihttl` para ver qué de la tabla "Hecho" ya está en GitHub (ojo: en esta sesión un fix se perdió una vez porque el push falló y el contenedor se cerró antes de reintentarlo — **siempre confirmar con `git log origin/<rama> -1` que lo que se cree pusheado realmente está en remoto**).
2. Este archivo es la fuente de verdad de qué falta — no repetir la auditoría completa desde cero, solo actualizar esta tabla a medida que se resuelva algo.
