"""Dashboard del agente de ahorro energético: streamlit run web/app.py

Consume la API real (variable API_URL). No calcula nada por su cuenta: todo lo que
enseña viene de /forecast, /audit, /explain, /quality y /health.
"""

import os

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:5500").rstrip("/")
TIMEOUT = 30

st.set_page_config(page_title="Ahorro energético", layout="wide")


def api_get(ruta: str):
    respuesta = requests.get(f"{API_URL}{ruta}", timeout=TIMEOUT)
    respuesta.raise_for_status()
    return respuesta.json()


def api_post(ruta: str, datos: dict):
    respuesta = requests.post(f"{API_URL}{ruta}", json=datos, timeout=TIMEOUT)
    if respuesta.status_code == 422:
        detalle = respuesta.json().get("detail")
        raise ValueError(detalle if isinstance(detalle, str) else "Faltan datos o hay valores no válidos")
    respuesta.raise_for_status()
    return respuesta.json()


st.title("Agente de ahorro energético")
st.caption(f"Conectado a la API en {API_URL}")

producto, operacion = st.tabs(["Mi factura", "Estado del servicio"])

with producto:
    izquierda, derecha = st.columns([1, 1])

    with izquierda:
        st.subheader("Audita tu factura")
        with st.form("factura"):
            sector = st.selectbox("Sector", ["carpinteria", "taller", "nave", "hosteleria", "instalador"])
            tarifa = st.selectbox("Tarifa", ["3.0TD", "6.1TD"])
            c1, c2 = st.columns(2)
            inicio = c1.date_input("Inicio del periodo", pd.Timestamp("2026-06-01"))
            fin = c2.date_input("Fin del periodo", pd.Timestamp("2026-07-01"))
            contratada = c1.number_input("Potencia contratada (kW)", min_value=0.0, value=30.0)
            maxima = c2.number_input("Potencia máxima registrada (kW)", min_value=0.0, value=18.5)
            consumo = c1.number_input("Consumo (kWh)", min_value=0.0, value=2500.0)
            reactiva = c2.number_input("Energía reactiva (kVArh)", min_value=0.0, value=900.0)
            importe = st.number_input("Importe total (EUR)", min_value=0.0, value=480.0)
            enviar = st.form_submit_button("Calcular ahorro")

        if enviar:
            factura = {
                "id_factura": "WEB", "sector": sector, "tarifa": tarifa,
                "fecha_inicio": str(inicio), "fecha_fin": str(fin),
                "potencia_contratada_kw": contratada, "potencia_maxima_kw": maxima,
                "consumo_kwh": consumo, "reactiva_kvarh": reactiva, "importe_total_eur": importe,
            }
            try:
                auditoria = api_post("/audit", factura)
                m1, m2, m3 = st.columns(3)
                m1.metric("Ahorro por potencia", f"{auditoria['ahorro_potencia_eur']:.2f} €")
                m2.metric("Penalización reactiva", f"{auditoria['penalizacion_reactiva_eur']:.2f} €")
                m3.metric("Potencia recomendada", f"{auditoria['potencia_optima_kw']:.0f} kW",
                          delta=f"{auditoria['potencia_optima_kw'] - contratada:.0f} kW", delta_color="inverse")
                with st.spinner("Redactando la explicación…"):
                    explicacion = api_post("/explain", factura)
                st.info(explicacion["text"])
                st.caption(f"Texto generado por: {explicacion['provider']} ({explicacion['model']})")
            except ValueError as exc:
                st.error(f"La factura no es válida: {exc}")
            except requests.RequestException as exc:
                st.error(f"No se puede contactar con la API: {exc}")

    with derecha:
        st.subheader("Precio previsto para mañana")
        try:
            prevision = api_get("/forecast")
            tabla = pd.DataFrame(prevision["horas"]).set_index("hora")
            st.bar_chart(tabla, y="precio_eur_mwh", y_label="EUR/MWh")
            st.success(f"Mejores horas para consumir el {prevision['dia']}: "
                       + ", ".join(prevision["mejores_horas"]))
        except requests.RequestException as exc:
            st.warning(f"No hay previsión disponible: {exc}")

with operacion:
    try:
        salud = api_get("/health")
        estado = "Funcionando" if salud["status"] == "ok" else "Degradado"
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Estado de la API", estado)
        s2.metric("Modelo", salud.get("model") or "—")
        s3.metric("Horas de precio cargadas", f"{salud['price_hours']:,}".replace(",", "."))
        s4.metric("Datos hasta", (salud["prices_until"] or "—")[:10])

        calidad = api_get("/quality")
        st.subheader("Error real del modelo, últimos 7 días")
        q1, q2 = st.columns(2)
        q1.metric("MAE modelo (EUR/MWh)", calidad["mae_modelo_media"])
        q2.metric("MAE baseline \"igual que ayer\"", calidad["mae_baseline_media"])
        st.dataframe(pd.DataFrame(calidad["dias"]), hide_index=True, use_container_width=True)
    except requests.RequestException as exc:
        st.error(f"La API no responde: {exc}")
