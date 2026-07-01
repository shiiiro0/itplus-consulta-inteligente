# Frontend — Sistema de Análisis (Canontex)

Panel web del sistema de análisis y operaciones: Monitoreo de Tiendas, Analytics de
APIs, Análisis de Scraping, Consulta de Precios y **Operaciones → Quiebres**.

Stack: **React 19 + TypeScript + Vite + Material UI (MUI 9)**, datos con
**TanStack Query**, gráficos con **recharts**, HTTP con **Axios**.

---

## Requisitos

- Node.js 20 o superior (incluye npm)

## Comandos

```bash
npm install      # instala dependencias
npm run dev      # servidor de desarrollo en http://localhost:5173
npm run build    # compila a /dist (producción)
npm run preview  # sirve el build de producción
npm run lint     # ESLint
```

## Variables de entorno

Las variables se definen en un archivo `.env` (ver `.env.example`). Solo las que
empiezan con `VITE_` quedan expuestas al frontend, y su valor se **hornea en el
build** (`npm run build`), no se lee en runtime.

| Variable | Descripción |
|----------|-------------|
| `VITE_FRESHDESK_BASE` | Base de Freshdesk para enlazar tickets en el módulo de Quiebres (`<base>/a/tickets/<id>`). Si se deja vacía, los tickets se muestran como chip no clickeable. |

## Backend, proxy y puerto 8443

- El cliente HTTP (`src/api/client.ts`) usa `baseURL: '/api'` (rutas **relativas**),
  por lo que el frontend es **agnóstico al puerto**: servirlo bajo
  `https://<host>:8443` funciona sin cambios en el código.
- En **desarrollo**, Vite hace proxy de `/api` hacia el backend FastAPI. Se
  configura en `vite.config.ts` (no es variable de entorno):

  ```ts
  server: { proxy: { '/api': { target: 'http://TU-BACKEND:8000', changeOrigin: true } } }
  ```

- En **producción**, el backend sirve los archivos estáticos del build y expone
  `/api` en el mismo origen, de modo que todo queda detrás del único puerto
  publicado (**8443**).

## Estructura

- `src/pages/`        páginas por módulo (Dashboard, Monitoreo, Quiebres, etc.)
- `src/components/`    componentes reutilizables (Layout/sidebar, `SortableDataTable`, etc.)
- `src/api/`          cliente Axios y llamadas tipadas a la API
- `src/contexts/`     estado global (auth)
- `src/theme.ts`      tema Material UI

---

## Módulo Quiebres — funcionalidades y mejoras recientes

Ruta: `src/pages/QuiebresPage.tsx`. Pestañas: **Activos, Resueltos, Métricas,
Campaña WhatsApp, Reporte de Gestión, Detalle técnico**.

Mejoras implementadas:

1. **Notificaciones con color** — el Snackbar usa `Alert` con `severity`
   (verde éxito / rojo error).
2. **Confirmación de campaña** — "Enviar campaña" pide confirmación e indica
   cuántas OCs saldrán antes de disparar el correo real.
3. **Paginación "Cargar más"** en Activos y Resueltos (sube el límite de a 500;
   evita perder filas más allá del tope inicial).
4. **Responsable con autocompletado** — `Autocomplete` (freeSolo) con sugerencias
   Dahianna/Romina y autosugerencia según la decisión del cliente.
5. **Ticket Freshdesk clickeable** — `TicketChip` reutilizable; enlaza si
   `VITE_FRESHDESK_BASE` está definido.
6. **Selector de período robusto** — Detalle técnico clampa a 30 días (no queda
   en blanco al venir de 60/90).
7. **Gráfico de decisiones** (recharts) en Métricas.
8. **Auto-refresh** — `refetchInterval` de 60s en KPIs (resumen) y Activos.
9. **Exportar a Excel** en Reporte de Gestión.
10. **Manejo de error unificado** con `apiErrorMessage` (muestra el detalle real
    del backend) en Resueltos, Métricas, Detalle técnico y Gestión.
11. **Columnas compartidas** — `quiebreCommonColumns()` evita duplicación entre
    Activos y Resueltos.
12. **Vistas de "enviados" aclaradas** — distinción entre histórico completo
    (máx. 500) y el período de N días.

### Campaña WhatsApp — filtro canónico

La *Vista previa* y el contador del botón "Enviar campaña" usan el **mismo filtro
que el job real del bot** (`EXCEL_PENDING_WHERE_SQL` en el backend): `DETECTED`
+ WhatsApp no vacío + sin exportar + familia no excluida
(`PCA, PCL, PMD, PBA, BEE, PCB, CAMAS, COLCHONES, MUEBLES`) + sin gestión previa
del bot. Así la previa coincide con lo que efectivamente se envía.
