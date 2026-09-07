import math
import pandas as pd
import streamlit as st
import ta
import yfinance as yf

st.set_page_config(page_title="Screener Trading", layout="wide")

st.title("📊 Auditoría de Riesgo & Swing Trading")

tickers_input = st.text_input(
    "Tickers (separados por coma):",
    "MSFT, NU, MU, YPF, GGAL, BTC-USD"
)

if st.button("EVALUAR MERCADO"):
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    # Verificar SPY
    spy_alcista = True
    try:
        spy_hist = yf.Ticker("SPY").history(period="1y")
        if not spy_hist.empty and len(spy_hist) >= 200:
            spy_alcista = (
                spy_hist["Close"].iloc[-1]
                > spy_hist["Close"].rolling(200).mean().iloc[-1]
            )
    except:
        pass

    for t in tickers:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="1y")
            if hist.empty or len(hist) < 50:
                continue

            precio = hist["Close"].iloc[-1]
            rsi = (
                ta.momentum.RSIIndicator(close=hist["Close"], window=14)
                .rsi()
                .iloc[-1]
            )
            vol_prom = hist["Volume"].tail(20).mean()
            rvol = (hist["Volume"].iloc[-1] / vol_prom) if vol_prom > 0 else 1.0
            sma_200 = hist["Close"].rolling(200).mean().iloc[-1]
            tendencia = "ALCISTA" if precio > sma_200 else "BAJISTA"

            vol_diaria = hist["Close"].pct_change().dropna().std()
            stop_loss = precio * (1 - (1.5 * vol_diaria))
            riesgo = max(precio - stop_loss, 0.01)
            nominales = math.floor(100 / riesgo)
            monto = nominales * precio

            # Tarjeta de resultado
            with st.container():
                st.subheader(f"{t} — ${precio:,.2f}")
                col1, col2, col3 = st.columns(3)
                col1.metric("RSI", f"{rsi:.1f}")
                col2.metric("RVOL", f"{rvol:.2f}x")
                col3.metric("Tendencia", tendencia)

                st.write(
                    f"**Gestion de Riesgo:** Stop-Loss en **${stop_loss:,.2f}** | Comprar **{nominales} nominales** (~${monto:,.2f}) para arriesgar $100."
                )
                st.divider()
        except Exception as e:
            st.error(f"Error analizando {t}: {e}")
