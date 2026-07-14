"""Roadmap phases for continuous improvement of the platform."""

from __future__ import annotations

CURRENT_PHASE = 2

ROADMAP_PHASES: list[dict] = [
    {
        "id": 1,
        "key": "documents_assistant",
        "title": "Asistente sobre documentos",
        "status": "completed",
        "description": (
            "Conversación gerencial sobre la base de conocimiento: subir documentos, "
            "indexarlos y consultar en lenguaje natural con citas y trazabilidad."
        ),
        "capabilities": [
            "Asistente conversacional con historial",
            "Conector de documentos activo",
            "Categorías de conocimiento (ventas, productos, etc.)",
            "Arquitectura de conectores lista para ampliar",
        ],
    },
    {
        "id": 2,
        "key": "analytics_documents",
        "title": "Análisis y comparativos en documentos",
        "status": "active",
        "description": (
            "Motor analítico CRISP-DM con DuckDB/SQL: perfila CSV/Excel al indexar, "
            "calcula cifras de forma determinista y entrega gráficos y tablas en la respuesta."
        ),
        "capabilities": [
            "Perfilado de datasets tabulares (CRISP-DM)",
            "Consultas SQL deterministas vía DuckDB",
            "Gráficos y tablas en respuestas gerenciales",
            "Indicador de fases CRISP-DM durante el análisis",
        ],
    },
    {
        "id": 3,
        "key": "erp_api_connectors",
        "title": "Conectores ERP y APIs",
        "status": "planned",
        "description": (
            "Integración con sistemas en vivo (ERP, CRM, APIs REST) para consultas "
            "sobre ventas, vendedores y productos en tiempo real."
        ),
        "capabilities": [
            "Conector ERP/API configurable",
            "Capa semántica de negocio",
            "Permisos por área y vendedor",
        ],
    },
    {
        "id": 4,
        "key": "proactive_insights",
        "title": "Insights proactivos",
        "status": "planned",
        "description": (
            "Alertas y resúmenes automáticos para gerencia: desviaciones, "
            "tendencias y recomendaciones."
        ),
        "capabilities": [
            "Dashboard gerencial",
            "Alertas configurables",
            "Resúmenes periódicos",
        ],
    },
]

KNOWLEDGE_CATEGORIES: list[dict[str, str]] = [
    {"key": "general", "label": "General"},
    {"key": "ventas", "label": "Ventas"},
    {"key": "productos", "label": "Productos"},
    {"key": "operaciones", "label": "Operaciones"},
    {"key": "politicas", "label": "Políticas y procedimientos"},
    {"key": "finanzas", "label": "Finanzas"},
    {"key": "soporte", "label": "Soporte técnico"},
]

BOT_KNOWLEDGE_CATEGORIES: list[dict[str, str]] = [
    {"key": "soporte", "label": "Soporte técnico"},
    {"key": "politicas", "label": "Políticas y procedimientos"},
    {"key": "operaciones", "label": "Operaciones"},
    {"key": "general", "label": "Toda la base"},
]

RAG_KNOWLEDGE_CATEGORIES: list[dict[str, str]] = [
    {"key": "general", "label": "Toda la base"},
    {"key": "politicas", "label": "Políticas y procedimientos"},
    {"key": "soporte", "label": "Soporte técnico"},
    {"key": "ventas", "label": "Ventas"},
    {"key": "productos", "label": "Productos"},
    {"key": "operaciones", "label": "Operaciones"},
    {"key": "finanzas", "label": "Finanzas"},
]
