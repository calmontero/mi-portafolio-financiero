import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os

# --- CONFIGURACIÓN v3.5.0 ---
st.set_page_config(page_title="Portafolio Financiero  v.3.5.0", layout="wide")

st.markdown("""
    <style>
    .main { background: #05070a; color: #f8fafc; }
    [data-testid="stMetricValue"] > div { color: white !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] > div { color: #8892b0 !important; font-size: 1rem !important; }
    [data-testid="stMetricDelta"] > div { color: white !important; }
    [data-testid="stMetricDelta"] svg { fill: white !important; }
    div[data-testid="stMetric"] { background: rgba(30, 41, 59, 0.7); border: 1px solid #38bdf8; border-radius: 15px; padding: 20px; }
    .alert-box { padding: 15px; border-radius: 10px; margin-bottom: 10px; font-weight: bold; text-align: center; }
    .tax-box { background: rgba(50, 255, 126, 0.1); border: 1px solid #32ff7e; padding: 15px; border-radius: 15px; margin-top: 10px; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- PERSISTENCIA ---
PORTFOLIO_FILE = "mi_portafolio.json"
def guardar_json(data):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f)
def cargar_json():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = cargar_json()

# --- MOTOR DE DATOS BLINDADO ---
@st.cache_data(ttl=300)
def fetch_prices(tickers):
    if not tickers: return pd.DataFrame()
    data = yf.download(tickers, period="2y", progress=False)
    if data.empty: return pd.DataFrame()
    if len(tickers) == 1:
        # Fix definitivo para dimensiones
        return pd.DataFrame({tickers[0]: data['Close'].values.flatten()}, index=data.index)
    return data['Close']

# --- SIDEBAR (ACTUALIZACIÓN REAL-TIME) ---
st.sidebar.title("⚡ Panel de Control v3.5.0")

# Formulario solo para AGREGAR activos (para que no borre lo que escribes)
with st.sidebar.form("add_form"):
    st.subheader("🛒 Agregar Activo")
    tk_in = st.text_input("Ticker", value="").upper().strip()
    inv_in = st.number_input("Inversión de Hoy ($)", min_value=0.0, value=1000.0)
    cont_in = st.number_input("Aporte Mensual ($)", min_value=0.0, value=0.0)
    save_btn = st.form_submit_button("Guardar en Portafolio")

if save_btn and tk_in:
    st.session_state.portfolio[tk_in] = {"inv": inv_in, "cont": cont_in}
    guardar_json(st.session_state.portfolio)
    st.rerun()

# FUERA DEL FORMULARIO para actualización instantánea de la proyección
st.sidebar.markdown("---")
años_proy = st.sidebar.slider("Años a Proyectar", 1, 30, 10)
edad_actual = st.sidebar.number_input("Edad Actual", min_value=18, value=49)

if st.sidebar.button("🗑️ Limpiar Portafolio"):
    st.session_state.portfolio = {}
    guardar_json({})
    st.rerun()

# --- LÓGICA DE CÁLCULO ---
tickers = list(st.session_state.portfolio.keys())
prices_df = fetch_prices(tickers)

total_actual = sum(v['inv'] for v in st.session_state.portfolio.values())
total_mensual = sum(v['cont'] for v in st.session_state.portfolio.values())
r_anual = 0.095

# Cálculo dinámico
final_bruto = total_actual * (1 + r_anual)**años_proy + total_mensual * 12 * (((1 + r_anual)**años_proy - 1) / r_anual)
ganancia = max(final_bruto - (total_actual + (total_mensual * 12 * años_proy)), 0)
impuestos = ganancia * 0.15
final_neto = final_bruto - impuestos

# --- DISEÑO MAIN ---
st.title("PORTAFOLIO FINANCIERO")

# 1. MÉTRICAS PRINCIPALES
c1, c2, c3 = st.columns(3)
with c1: st.metric("Inversión Inicial", f"${total_actual:,.0f}")
with c2: st.metric(f"Patrimonio a {años_proy} años", f"${final_bruto:,.0f}", delta=f"Neto: ${final_neto:,.0f}")
with c3: st.metric("Retiro Mensual (4%)", f"${(final_neto * 0.04 / 12):,.0f}")

# 2. RECUADROS DE SEÑALES (RESTAURADOS)
st.divider()
st.subheader("🔔 Señales de Mercado (Estrategia SMA 200)")
if tickers and not prices_df.empty:
    cols_alert = st.columns(len(tickers) if len(tickers) < 4 else 4)
    for i, tk in enumerate(tickers):
        with cols_alert[i % 4]:
            if tk in prices_df.columns:
                current_p = float(prices_df[tk].iloc[-1])
                sma200 = float(prices_df[tk].rolling(200).mean().iloc[-1])
                if current_p > sma200:
                    st.markdown(f'<div class="alert-box" style="background: rgba(50, 255, 126, 0.2); border: 1px solid #32ff7e; color: #32ff7e;">🚀 {tk}: COMPRA</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="alert-box" style="background: rgba(255, 82, 82, 0.2); border: 1px solid #ff5252; color: #ff5252;">⚠️ {tk}: PRECAUCIÓN</div>', unsafe_allow_html=True)

# 3. GRÁFICAS TÉCNICAS
st.divider()
if tickers:
    selected = st.selectbox("🔍 Analizar Activo en Detalle", tickers)
    hist = yf.Ticker(selected).history(period="1y")
    fig_t = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_width=[0.2, 0.8])
    fig_t.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="Velas"), row=1, col=1)
    for m in [20, 50, 100, 200]:
        fig_t.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(m).mean(), name=f"SMA {m}"), row=1, col=1)
    
    # RSI
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = 100 - (100 / (1 + (gain/loss)))
    fig_t.add_trace(go.Scatter(x=hist.index, y=rsi, name="RSI", line=dict(color='orange')), row=2, col=1)
    fig_t.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_t, width='stretch')

# 4. ORIGEN DE FONDOS
st.divider()
st.subheader("📊 Origen de Fondos Proyectados")
df_origin = pd.DataFrame({"Origen": ["Inversión Inicial", "Aportes en el tiempo"], "Monto ($)": [total_actual, (total_mensual * 12 * años_proy)]})
fig_origin = px.bar(df_origin, x='Origen', y='Monto ($)', color='Origen', color_discrete_sequence=['#38bdf8', '#fbbf24'], text_auto='$,.0f')
fig_origin.update_layout(template="plotly_dark", height=350, showlegend=False)
st.plotly_chart(fig_origin, width='stretch')

st.sidebar.caption("Portafolio Financiero Versión 3.5.0")
