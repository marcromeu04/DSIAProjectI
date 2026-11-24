"""API del agente de ahorro energético: uvicorn api.main:app --port 5500

Expone el núcleo de energia_app sin reescribirlo:
  GET  /health    estado del servicio, del modelo y de los datos
  GET  /forecast  precio previsto para cada hora de mañana y mejores horas
  POST /audit     una factura → ahorro por potencia y penalización por reactiva
  POST /explain   una factura → explicación en lenguaje llano (mock o Hugging Face)
  GET  /quality   error real del modelo en los últimos 7 días con datos
  GET  /metrics   métricas para Prometheus
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

from energia_app import metrics
from energia_app.ai_client import AIClient, AIClientError
from energia_app.cli import explain_request
from energia_app.features.builder import price_series
from energia_app.loader import load_prices
from energia_app.modeling.bundle import ModelBundle
from energia_app.validator import validate_invoices, validate_prices

logger = logging.getLogger("energia_api")


class InvoiceIn(BaseModel):
    """Una factura, con las mismas columnas que el CSV del Proyecto I."""

    id_factura: str = "WEB"
    sector: str = Field(examples=["carpinteria"])
    provincia: str = ""
    tarifa: str = Field(examples=["3.0TD"])
    fecha_inicio: str = Field(examples=["2026-06-01"])
    fecha_fin: str = Field(examples=["2026-07-01"])
    potencia_contratada_kw: float = Field(examples=[30])
    potencia_maxima_kw: float = Field(examples=[18.5])
    consumo_kwh: float = Field(examples=[2500])
    reactiva_kvarh: float = Field(examples=[900])
    importe_total_eur: float = Field(examples=[480.0])


class Metrics:
    """Métricas Prometheus en un registro propio (así cada app de test empieza de cero)."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests = Counter("energia_requests_total", "Peticiones por endpoint y código",
                                ["endpoint", "status"], registry=self.registry)
        self.latency = Histogram("energia_request_latency_seconds", "Latencia por endpoint",
                                 ["endpoint"], registry=self.registry)
        self.forecasts = Counter("energia_forecast_count_total", "Previsiones de precio servidas",
                                 registry=self.registry)
        self.audits = Counter("energia_audit_count_total", "Facturas auditadas", registry=self.registry)
        self.mae_model = Gauge("energia_model_mae_7d", "MAE real del modelo, media de 7 días (EUR/MWh)",
                               registry=self.registry)
        self.mae_baseline = Gauge("energia_baseline_mae_7d", "MAE del baseline, media de 7 días (EUR/MWh)",
                                  registry=self.registry)


def create_app(prices_path: Path | None = None, model_path: Path | None = None) -> FastAPI:
    """Crea la app. Las rutas llegan por argumento (tests) o por entorno (Docker/Kubernetes)."""
    load_dotenv()
    prices_path = Path(prices_path or os.getenv("PRICES_PATH", "data/raw/precios_pvpc.csv"))
    model_path = Path(model_path or os.getenv("MODEL_PATH", "models/modelo_precio.joblib"))
    m = Metrics()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Se carga una sola vez al arrancar; si algo falta, el servicio arranca "degraded"
        app.state.prices, app.state.model, app.state.quality = None, None, None
        try:
            app.state.model = ModelBundle.load(model_path)
            app.state.prices = price_series(validate_prices(load_prices(prices_path)).valid, app.state.model.target)
            app.state.quality = app.state.model.backtest(app.state.prices, n_days=7)
            m.mae_model.set(app.state.quality["mae_modelo_media"])
            m.mae_baseline.set(app.state.quality["mae_baseline_media"])
        except Exception as exc:  # datos o modelo ausentes: /health lo dirá
            logger.error("Arranque incompleto: %s", exc)
        yield

    app = FastAPI(title="Agente de ahorro energético", version="1.0", lifespan=lifespan)

    @app.middleware("http")
    async def observar(request: Request, call_next):
        # Cada petición cuenta y se cronometra; /metrics no se mide a sí mismo
        inicio = time.perf_counter()
        response = await call_next(request)
        if request.url.path != "/metrics":
            m.requests.labels(request.url.path, str(response.status_code)).inc()
            m.latency.labels(request.url.path).observe(time.perf_counter() - inicio)
        return response

    def _requiere(*partes: str) -> None:
        if "prices" in partes and app.state.prices is None:
            raise HTTPException(503, "No hay precios cargados")
        if "model" in partes and app.state.model is None:
            raise HTTPException(503, "No hay modelo cargado: ejecuta python -m energia_app.train")

    def _forecast() -> pd.DataFrame:
        return app.state.model.predict_next_day(app.state.prices)

    def _auditar(factura: InvoiceIn) -> pd.DataFrame:
        result = validate_invoices(pd.DataFrame([factura.model_dump()]))
        if result.n_invalid:
            raise HTTPException(422, f"Factura no válida: {result.invalid['motivo'].iloc[0]}")
        return result.valid

    @app.get("/health")
    def health() -> dict:
        ok = app.state.prices is not None and app.state.model is not None
        return {
            "status": "ok" if ok else "degraded",
            "model_loaded": app.state.model is not None,
            "price_hours": 0 if app.state.prices is None else len(app.state.prices),
            "prices_until": None if app.state.prices is None else str(app.state.prices.index.max()),
            "model": None if app.state.model is None else app.state.model.metadata.get("ganador"),
        }

    @app.get("/forecast")
    def forecast() -> dict:
        _requiere("prices", "model")
        prevision = _forecast()
        m.forecasts.inc()
        baratas = prevision.nsmallest(3, "precio_previsto_eur_mwh")
        return {
            "dia": str(prevision["fecha_hora"].iloc[0].date()),
            "horas": [{"hora": f"{t:%H:%M}", "precio_eur_mwh": float(p)}
                      for t, p in zip(prevision["fecha_hora"], prevision["precio_previsto_eur_mwh"])],
            "mejores_horas": [f"{t:%H:%M}" for t in baratas["fecha_hora"]],
        }

    @app.post("/audit")
    def audit(factura: InvoiceIn) -> dict:
        fila = metrics.with_savings(_auditar(factura)).iloc[0]
        m.audits.inc()
        return {
            "id_factura": factura.id_factura,
            "potencia_contratada_kw": float(fila["potencia_contratada_kw"]),
            "potencia_optima_kw": float(fila["potencia_optima_kw"]),
            "ahorro_potencia_eur": round(float(fila["ahorro_potencia_eur"]), 2),
            "penalizacion_reactiva_eur": round(float(fila["penalizacion_reactiva_eur"]), 2),
        }

    @app.post("/explain")
    def explain(factura: InvoiceIn) -> dict:
        valid = _auditar(factura)
        horas: list[str] = []
        if app.state.prices is not None and app.state.model is not None:
            horas = [f"{t:%H:%M}" for t in _forecast().nsmallest(3, "precio_previsto_eur_mwh")["fecha_hora"]]
        try:
            resp = AIClient.from_env().explain(explain_request(valid, factura.id_factura, horas))
        except AIClientError as exc:
            raise HTTPException(502, str(exc)) from exc
        return {"provider": resp.provider, "model": resp.model, "text": resp.text}

    @app.get("/quality")
    def quality() -> dict:
        _requiere("prices", "model")
        return app.state.quality

    @app.get("/metrics")
    def prometheus_metrics() -> Response:
        return Response(generate_latest(m.registry), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
