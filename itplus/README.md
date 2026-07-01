# ITPlus — Plataforma Universal de Consulta Inteligente

Plataforma modular que combina **ITPlusBot** (asistente conversacional para describir problemas) y **Consulta RAG** (preguntas sobre documentos con citas y trazabilidad).

## Arquitectura

```
React Frontend  →  FastAPI /api/v1  →  PostgreSQL + pgvector
                                    →  Redis + Celery (indexación)
                                    →  Groq / OpenAI / Ollama (LLM)
```

### Motores de IA

| Motor | Endpoint | Función |
|-------|----------|---------|
| **A — ITPlusBot** | `POST /api/v1/chat/bot` | Conversación guiada, cierre con `CHAT FINALIZADO`, resumen técnico |
| **B — RAG** | `POST /api/v1/chat/query` | Consulta sobre documentos indexados con fuentes citadas |

## Requisitos

- Docker y Docker Compose
- (Opcional) API key de [Groq](https://console.groq.com/) para el LLM en desarrollo

## Inicio rápido (< 30 min)

### 1. Configurar entorno

```bash
cp itplus/.env.example .env
# Editar .env y agregar AI_API_KEY con tu clave de Groq
```

### 2. Levantar con Docker Compose

```bash
docker compose up --build
```

Servicios:

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| API + Swagger | http://localhost:8000/api/docs |
| Health | http://localhost:8000/api/v1/health |

### 3. Credenciales por defecto

- **Email:** `admin@itplus.cl`
- **Contraseña:** `admin123`

### 4. Uso

1. Iniciar sesión en http://localhost:3000/itplus/login
2. **ITPlusBot:** describir un problema → el bot parafrasea y confirma → al cerrar genera resumen técnico
3. **Documentos:** subir PDFs/DOCX → esperar estado `ready`
4. **Consulta:** preguntar sobre los documentos → respuesta con bloque de fuentes

## Desarrollo local (sin Docker)

### Backend

```bash
pip install -r itplus/requirements.txt
# PostgreSQL con pgvector y Redis deben estar corriendo
export DATABASE_URL=postgresql://itplus:itplus@localhost:5432/consulta_db
export REDIS_URL=redis://localhost:6379/0
export AI_API_KEY=tu_clave_groq

python itplus/scripts/seed_admin.py
uvicorn run_itplus:app --reload --port 8000

# En otra terminal — worker de indexación
celery -A itplus.app.workers.celery_app:celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Abrir http://localhost:5173/itplus/login
```

## Estructura del módulo ITPlus

```
itplus/
├── app/
│   ├── api/v1/          # Endpoints REST
│   ├── core/            # Config, DB, seguridad
│   ├── models/          # SQLAlchemy (users, conversations, documents...)
│   ├── schemas/         # Pydantic
│   ├── services/        # LLM, RAG, conversación, embeddings
│   ├── prompts/         # System prompts ITPlusBot y RAG
│   └── workers/         # Celery (indexación, resúmenes)
├── scripts/seed_admin.py
└── requirements.txt
```

## Endpoints principales

### Auth
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

### Motor A — ITPlusBot
- `POST /api/v1/chat/bot`
- `POST /api/v1/chat/bot/conversations`
- `GET /api/v1/chat/bot/conversations/{id}`
- `GET /api/v1/chat/bot/conversations/{id}/summary`

### Motor B — RAG
- `POST /api/v1/documents` (upload)
- `GET /api/v1/documents`
- `DELETE /api/v1/documents/{id}`
- `POST /api/v1/chat/query`
- `GET /api/v1/chat/query/history`

### Sistema
- `GET /api/v1/health`

## Variables de entorno

Ver `itplus/.env.example` para la lista completa.

| Variable | Descripción | Default |
|----------|-------------|---------|
| `AI_DRIVER` | Proveedor LLM (`groq`, `openai`, `ollama`) | `groq` |
| `AI_API_KEY` | API key del proveedor | — |
| `AI_MODEL` | Modelo LLM | `llama-3.3-70b-versatile` |
| `DATABASE_URL` | PostgreSQL + pgvector | — |
| `REDIS_URL` | Redis para Celery | — |
| `EMBEDDING_MODEL` | Modelo de embeddings local | `all-MiniLM-L6-v2` |

## Coexistencia con Canontex ERP

Este repositorio contiene también el ERP Canontex (`api/`, `modulos/`). ITPlus es un módulo independiente:

- **ITPlus standalone:** `uvicorn run_itplus:app` o `docker compose up`
- **ERP existente:** `python run_api.py` (sin cambios)

Las rutas ITPlus viven bajo `/api/v1/*` y el frontend en `/itplus/*`.

## Criterios de éxito MVP

- [x] ITPlusBot con historial y cierre `CHAT FINALIZADO`
- [x] Resumen técnico al cerrar conversación
- [x] Multi-proveedor LLM (Groq default)
- [x] Upload de documentos con indexación async
- [x] Consulta RAG con citas
- [x] Respuesta explícita cuando no hay información
- [x] `docker compose up` levanta todo

## Licencia

Uso interno ITPlus.
