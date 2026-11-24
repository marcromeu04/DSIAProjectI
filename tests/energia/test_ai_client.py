import sys
import types

import pytest

from energia_app.ai_client import (
    DEFAULT_HF_MODEL, AIClient, AIClientError, ExplainRequest, build_prompt,
)


@pytest.fixture
def req():
    return ExplainRequest(
        id_factura="F1", sector="taller", potencia_contratada_kw=30, potencia_optima_kw=15,
        ahorro_potencia_eur=31.5, penalizacion_reactiva_eur=6.8, mejores_horas=["13:00", "14:00"],
    )


def test_mock_usa_las_cifras_exactas(req):
    resp = AIClient("mock").explain(req)

    assert resp.provider == "mock"
    assert "31.50 EUR" in resp.text and "6.80 EUR" in resp.text
    assert "13:00, 14:00" in resp.text


def test_mock_es_determinista(req):
    assert AIClient("mock").explain(req) == AIClient("mock").explain(req)


def test_prompt_lleva_todas_las_cifras(req):
    prompt = build_prompt(req)

    for cifra in ["30 kW", "15 kW", "31.50 EUR", "6.80 EUR", "13:00"]:
        assert cifra in prompt


def test_modo_desconocido_falla():
    with pytest.raises(AIClientError, match="no soportado"):
        AIClient("gpt")


def test_hf_sin_token_falla(req):
    with pytest.raises(AIClientError, match="HF_TOKEN"):
        AIClient("hf", token=None).explain(req)


def test_from_env_lee_las_variables(monkeypatch):
    monkeypatch.setenv("AI_MODE", "hf")
    monkeypatch.setenv("HF_MODEL", "owner/modelo")
    monkeypatch.setenv("HF_TOKEN", "hf_falso")

    client = AIClient.from_env()

    assert (client.mode, client.model, client.token) == ("hf", "owner/modelo", "hf_falso")


def test_from_env_por_defecto_es_mock(monkeypatch):
    monkeypatch.delenv("AI_MODE", raising=False)

    client = AIClient.from_env()

    assert client.mode == "mock" and client.model == DEFAULT_HF_MODEL


def _hf_falso(monkeypatch, comportamiento):
    """Sustituye huggingface_hub por un módulo falso: el test no sale a internet."""
    class FakeClient:
        def __init__(self, api_key, provider):
            self.api_key = api_key

        def chat_completion(self, messages, model, max_tokens, temperature):
            return comportamiento(messages, model)

    monkeypatch.setitem(sys.modules, "huggingface_hub", types.SimpleNamespace(InferenceClient=FakeClient))


def test_hf_devuelve_el_texto_del_modelo(monkeypatch, req):
    def responde(messages, model):
        assert messages[0]["role"] == "system" and "31.50 EUR" in messages[1]["content"]
        msg = types.SimpleNamespace(content="  Te sobran 15 kW.  ")
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    _hf_falso(monkeypatch, responde)

    resp = AIClient("hf", model="owner/modelo", token="hf_falso").explain(req)

    assert (resp.provider, resp.model, resp.text) == ("huggingface", "owner/modelo", "Te sobran 15 kW.")


def test_hf_error_de_red_se_convierte_en_aiclienterror(monkeypatch, req):
    def falla(messages, model):
        raise ConnectionError("sin red")

    _hf_falso(monkeypatch, falla)

    with pytest.raises(AIClientError, match="no ha respondido"):
        AIClient("hf", token="hf_falso").explain(req)
