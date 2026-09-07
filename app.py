import math
import pandas as pd
import streamlit as st
import ta
import yfinance as yf

st.set_page_config(
    page_title="Auditoría de Riesgo & Swing",
    page_icon="📊",
    layout="centered",
)

st.title("📊 Auditoría de Riesgo & Swing Trading")

tickers_input = st.text_input(
    "Tickers (separados por coma):", "MSFT, NU, MU, YPF, GGAL, BTC-USD"
)

if st.button("EVALUAR MERCADO", type="primary"):
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    # Evaluar estado de SPY
    spy_alcista = True
    try:
        spy_hist = yf.Ticker("SPY").history(period="1y")
        if not spy_hist.empty and len(spy_hist) >= 200:
            spy_alcista = (
                spy_hist["Close"].iloc[-1]
                > spy_hist["Close"].rolling(200).mean().iloc[-1]
            )
    except Exception:
        pass

    for t in tickers:
        try:
            ticker_clean = t
            if ticker_clean in ["GAL", "GALICIA"]:
                ticker_clean = "GGAL"
            elif ticker_clean in ["BTC", "BTCUSD"]:
                ticker_clean = "BTC-USD"

            is_crypto = "-USD" in ticker_clean
            stock = yf.Ticker(ticker_clean)
            hist = stock.history(period="1y")

            if hist.empty or len(hist) < 50:
                st.warning(
                    f"No se encontraron suficientes datos para {ticker_clean}"
                )
                continue

            precio_actual = hist["Close"].iloc[-1]
            maximo_52w = hist["High"].max()
            rsi = (
                ta.momentum.RSIIndicator(close=hist["Close"], window=14)
                .rsi()
                .iloc[-1]
            )
            volatilidad = (hist["Close"].pct_change().dropna().std()) * (
                252**0.5
            )

            volumen_hoy = hist["Volume"].iloc[-1]
            volumen_prom_20 = hist["Volume"].tail(20).mean()
            rvol = (
                (volumen_hoy / volumen_prom_20) if volumen_prom_20 > 0 else 1.0
            )

            sma_200 = hist["Close"].rolling(window=200).mean().iloc[-1]
            tendencia = (
                "ALCISTA" if precio_actual > sma_200 else "BAJISTA / REBOTE"
            )

            vol_diaria = hist["Close"].pct_change().dropna().std()
            stop_loss = precio_actual * (1 - (1.5 * vol_diaria))
            riesgo_por_accion = max(precio_actual - stop_loss, 0.01)

            acciones_posicion = math.floor(100 / riesgo_por_accion)
            monto_inversion = acciones_posicion * precio_actual

            target_val = None
            if not is_crypto:
                try:
                    info_dict = stock.info
                    if info_dict and "targetMeanPrice" in info_dict:
                        target_val = info_dict["targetMeanPrice"]
                except Exception:
                    pass

            puntos_riesgo = 0
            motivos = []

            if not spy_alcista and not is_crypto:
                puntos_riesgo += 2
                motivos.append("SPY debajo de SMA 200.")

            if target_val and precio_actual > target_val:
                puntos_riesgo += 2
                motivos.append(
                    f"Por encima del Target Price (${target_val:.2f})."
                )

            if (precio_actual / maximo_52w) > 0.96:
                puntos_riesgo += 2
                motivos.append("Cerca del máximo anual (52 sem).")

            if rsi > 68:
                puntos_riesgo += 2
                motivos.append(f"RSI en sobrecompra ({rsi:.1f}).")

            if volatilidad > 0.50:
                puntos_riesgo += 2
                motivos.append(f"Volatilidad alta ({volatilidad*100:.1f}%).")

            if rvol < 0.7:
                puntos_riesgo += 1
                motivos.append(f"Bajo volumen relativo ({rvol:.2f}x).")

            if tendencia == "BAJISTA / REBOTE":
                puntos_riesgo += 1
                motivos.append("Debajo de SMA 200.")

            if puntos_riesgo == 0:
                veredicto = "🟢 COMPRA SWING (OK)"
            elif puntos_riesgo <= 2:
                veredicto = "🟡 SWING EN ESPERA"
            else:
                veredicto = "🔴 NO COMPRAR"

            corto = (
                "FAVORABLE"
                if (rsi < 65 and rvol >= 1.0)
                else ("DESFAVORABLE" if rsi >= 68 else "NEUTRO")
            )
            mediano = "FAVORABLE" if tendencia == "ALCISTA" else "DESFAVORABLE"

            # Renderizado
            st.markdown(f"### {ticker_clean} — ${precio_actual:,.2f}")
            st.subheader(veredicto)

            col1, col2, col3 = st.columns(3)
            col1.metric("RSI (14)", f"{rsi:.1f}")
            col2.metric("RVOL", f"{rvol:.2f}x")
            col3.metric("Tendencia", tendencia)

            st.write(
                f"**Horizontes:** Corto plazo: **{corto}** | Mediano plazo: **{mediano}**"
            )
            st.write(
                f"**Gestión de Riesgo:** Stop-Loss en **${stop_loss:,.2f}** | "
                f"Comprar **{acciones_posicion} nominales** (~${monto_inversion:,.2f}) para arriesgar $100."
            )

            if motivos:
                st.warning("⚠️ **Alertas detectadas:** " + " | ".join(motivos))
            else:
                st.success("✅ Sin factores de riesgo graves detectados.")

            st.divider()

        except Exception as e:
            st.error(f"Error procesando {t}: {e}")
