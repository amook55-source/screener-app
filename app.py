import math
import pandas as pd
import streamlit as st
import ta
import yfinance as yf

st.set_page_config(
    page_title="Screener Pre-Earnings, Swing & Cripto",
    page_icon="📈",
    layout="wide",
)

st.title("Screener Pre-Earnings, Swing Trading & Cripto")
st.caption("AUDITORÍA DE RIESGO, VOLUMEN & TENDENCIA")

tickers_input = st.text_input(
    "Tickers:", "MU, NU, IBM, YPF, MSFT, DELL, GGAL, BTC-USD"
)

if st.button("EVALUAR MERCADO", type="primary"):
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

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

    tabla_datos = []
    diagnosticos = {}

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
            target_str = "N/A"
            ratio_rr_str = "N/A"

            if not is_crypto:
                try:
                    info_dict = stock.info
                    if info_dict and "targetMeanPrice" in info_dict:
                        target_val = info_dict["targetMeanPrice"]
                        if target_val:
                            target_str = f"${target_val:.2f}"
                            ganancia = target_val - precio_actual
                            if riesgo_por_accion > 0 and ganancia > 0:
                                ratio_rr_str = f"1:{ganancia/riesgo_por_accion:.2f}"
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
                    f"Por encima del Precio Objetivo ({target_str})."
                )

            if (precio_actual / maximo_52w) > 0.96:
                puntos_riesgo += 2
                motivos.append("Cerca del máximo anual.")

            if rsi > 68:
                puntos_riesgo += 2
                motivos.append(f"RSI en sobrecompra ({rsi:.1f}).")

            if volatilidad > 0.50:
                puntos_riesgo += 2
                motivos.append(f"Volatilidad alta ({volatilidad*100:.1f}%).")

            if rvol < 0.7:
                puntos_riesgo += 1
                motivos.append(f"Bajo volumen ({rvol:.2f}x).")

            if tendencia == "BAJISTA / REBOTE":
                puntos_riesgo += 1
                motivos.append("Debajo de SMA 200.")

            if puntos_riesgo == 0:
                veredicto = "COMPRA SWING (OK)"
            elif puntos_riesgo <= 2:
                veredicto = "SWING EN ESPERA"
            else:
                veredicto = "NO (ALGORITMO SALVA)"

            corto = (
                "FAVORABLE"
                if (rsi < 65 and rvol >= 1.0)
                else ("DESFAVORABLE" if rsi >= 68 else "NEUTRO / EN ESPERA")
            )
            mediano = "FAVORABLE" if tendencia == "ALCISTA" else "DESFAVORABLE"

            tabla_datos.append(
                {
                    "Ticker": ticker_clean,
                    "Precio": f"${precio_actual:,.2f}",
                    "RSI": f"{rsi:.1f}",
                    "Volumen (RVOL)": f"{rvol:.2f}x",
                    "Volatilidad": f"{volatilidad*100:.1f}%",
                    "Tendencia": tendencia,
                    "Veredicto": veredicto,
                }
            )

            diagnosticos[ticker_clean] = {
                "veredicto": veredicto,
                "corto": corto,
                "mediano": mediano,
                "stop": stop_loss,
                "ratio": ratio_rr_str,
                "nominales": acciones_posicion,
                "monto": monto_inversion,
                "motivos": motivos,
            }

        except Exception as e:
            st.error(f"Error procesando {t}: {e}")

    # Guardar estado de análisis
    st.session_state["df"] = pd.DataFrame(tabla_datos)
    st.session_state["diagnosticos"] = diagnosticos

# Mostrar resultados si existen
if "df" in st.session_state and not st.session_state["df"].empty:
    df = st.session_state["df"]
    diagnosticos = st.session_state["diagnosticos"]

    # Función para colorear según semáforo
    def colorear_filas(row):
        v = row["Veredicto"]
        if "COMPRA SWING" in v:
            color = (
                "background-color: #1e4620; color: #a3e635;"  # Verde oscuro
            )
        elif "ESPERA" in v:
            color = (
                "background-color: #5c3d00; color: #fde047;"  # Amarillo/Ocre
            )
        else:
            color = (
                "background-color: #4a151b; color: #fca5a5;"  # Rojo oscuro
            )
        return [color] * len(row)

    df_styled = df.style.apply(colorear_filas, axis=1)

    st.subheader("Oportunidades y Estado de Mercado")
    st.caption("Tocá cualquier fila para seleccionar el activo:")

    # Tabla interactiva con selección de fila completa
    event = st.dataframe(
        df_styled,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # Detalle dinámico del ticker seleccionado
    selected_rows = event.selection.get("rows", [])
    st.divider()

    if selected_rows:
        idx = selected_rows[0]
        ticker_sel = df.iloc[idx]["Ticker"]
        item = diagnosticos[ticker_sel]

        st.subheader(f"🔍 DIAGNÓSTICO DETALLADO: {ticker_sel}")
        st.write(f"**Veredicto:** {item['veredicto']}")
        st.write(f"• **Corto plazo:** {item['corto']}")
        st.write(f"• **Mediano plazo:** {item['mediano']}")
        st.write(
            f"• **Stop-Loss Técnico:** ${item['stop']:,.2f} | **R/R:** {item['ratio']}"
        )
        st.write(
            f"• **Posición ($100 riesgo):** {item['nominales']} nominales (~${item['monto']:,.2f})"
        )

        if item["motivos"]:
            st.warning("⚠️ **Alertas:** " + " | ".join(item["motivos"]))
        else:
            st.success("✅ Sin factores de riesgo graves detectados.")
    else:
        st.info("💡 Seleccioná una fila arriba para ver el desglose técnico.")
