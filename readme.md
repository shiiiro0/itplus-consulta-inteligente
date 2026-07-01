# ITPlus — Plataforma Universal de Consulta Inteligente

Repositorio **standalone**: solo ITPlus (ITPlusBot + RAG). Sin código del ERP Canontex.

## Inicio rápido

```bash
cp .env.example .env
# Editar AI_API_KEY (Groq: https://console.groq.com/)

docker compose up --build
```

| Servicio | URL |
|----------|-----|
| App | http://localhost:3000 |
| API + Swagger | http://localhost:8000/api/docs |
| Login | http://localhost:3000/login |

**Credenciales por defecto:** `admin@itplus.cl` / `admin123`

## Desarrollo local

```bash
# Backend
pip install -r requirements.txt
python itplus/scripts/seed_admin.py
uvicorn run_itplus:app --reload --port 8000

# Worker (otra terminal)
celery -A itplus.app.workers.celery_app:celery_app worker --loglevel=info

# Frontend (otra terminal)
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

## Estructura

```
├── itplus/app/          # Backend FastAPI (api, services, models, workers)
├── frontend/            # React (ITPlusBot, Consulta RAG, Documentos)
├── run_itplus.py        # Entry point API
├── docker-compose.yml
├── Dockerfile           # API
├── Dockerfile.worker    # Celery
├── Dockerfile.frontend  # Nginx + React build
└── requirements.txt
```

## Motores de IA

| Motor | Ruta API | Descripción |
|-------|----------|-------------|
| **ITPlusBot** | `POST /api/v1/chat/bot` | Conversación guiada + resumen técnico |
| **RAG** | `POST /api/v1/chat/query` | Consulta sobre documentos con citas |

## Variables de entorno

Ver `.env.example`.

## Publicar en un repositorio GitHub nuevo

Este proyecto se extrajo del monorepo Canontex. Para subirlo a su **propio repo**:

```bash
# 1. Crear repo vacío en GitHub (sin README): ej. itplus-consulta-inteligente

# 2. Desde esta carpeta, con la rama standalone:
git remote rename origin old-origin   # opcional: conservar referencia al repo original
git remote add origin https://github.com/TU_USUARIO/itplus-consulta-inteligente.git

# 3. Subir como main del repo nuevo
git push -u origin cursor/itplus-standalone-c0eb:main
```

O usar el script incluido:

```bash
./scripts/push-to-new-repo.sh https://github.com/TU_USUARIO/itplus-consulta-inteligente.git
```

## Relación con el ERP Canontex

Este repo es **independiente**. Actualizaciones aquí no afectan al ERP y viceversa, salvo que decidas fusionar manualmente cambios entre repos.
