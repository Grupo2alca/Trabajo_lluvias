# ======================================
# LLUVIAS_INHAMI.PY – ANÁLISIS DE LLUVIA
# MÉTODO DE PATRONES NORMALIZADOS
# ======================================

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pyreadstat
import io
import tempfile

st.set_page_config(page_title="Análisis de Lluvia - INHAMI", layout="wide")
st.title("💧 Aplicación de Análisis de Lluvia - Método de Patrones")

uploaded_file = st.file_uploader("📂 Sube tu archivo .sav de precipitaciones", type=["sav"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_file_path = tmp_file.name

    df, meta = pyreadstat.read_sav(tmp_file_path)
    df = df.rename(columns={'valor': 'Precipitacion', 'fecha': 'Fecha'})

    fecha_inicio = pd.to_datetime('2000-01-01 00:00:00')
    df['Fecha_Correcta'] = fecha_inicio + pd.to_timedelta(np.arange(len(df)) * 5, unit='min')

    st.subheader("📊 Datos Cargados")
    st.dataframe(df[['Fecha_Correcta', 'Precipitacion']].head(10))

    duraciones = {
        '1_Hora': 60,
        '1_Semana': 60 * 24 * 7,
        '1_Mes': 60 * 24 * 30,
        '1_Año': 60 * 24 * 365
    }

    intervalo = 5
    pasos_duracion = {k: v // intervalo for k, v in duraciones.items()}
    resumen_eventos = []
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for nombre, pasos in pasos_duracion.items():
            eventos = []
            for i in range(len(df) - pasos):
                segmento = df.iloc[i:i + pasos].copy()
                if segmento['Precipitacion'].sum() > 0:
                    segmento.reset_index(drop=True, inplace=True)
                    segmento['Tiempo Normalizado'] = np.linspace(0, 1, len(segmento))
                    segmento['Precipitación Acumulada'] = segmento['Precipitacion'].cumsum()
                    segmento['Precipitación Normalizada'] = segmento['Precipitación Acumulada'] / segmento['Precipitación Acumulada'].iloc[-1]
                    segmento['ID_Evento'] = f"{nombre}_{i}"
                    eventos.append(segmento)

            if eventos:
                df_eventos = pd.concat(eventos, ignore_index=True)
                df_eventos.to_excel(writer, sheet_name=nombre[:31], index=False)

                evento_max = df_eventos.groupby('ID_Evento').agg({
                    'Precipitación Acumulada': 'max',
                    'Fecha_Correcta': 'first'
                }).sort_values('Precipitación Acumulada', ascending=False).iloc[0]
                id_max = evento_max.name
                evento_plot = df_eventos[df_eventos['ID_Evento'] == id_max].copy()

                curva_interp = np.interp(np.linspace(0, 1, 100), evento_plot['Tiempo Normalizado'], evento_plot['Precipitación Normalizada'])
                coef = np.polyfit(np.linspace(0, 1, 100), curva_interp, 2)

                resumen_eventos.append({
                    'Duración': nombre,
                    'Inicio': evento_plot['Fecha_Correcta'].iloc[0],
                    'Fin': evento_plot['Fecha_Correcta'].iloc[-1],
                    'Precipitación Total': round(evento_plot['Precipitación Acumulada'].iloc[-1], 2),
                    'Pico Máximo': round(evento_plot['Precipitacion'].max(), 2),
                    'Coef a': round(coef[0], 4),
                    'Coef b': round(coef[1], 4),
                    'Coef c': round(coef[2], 4)
                })

        df_resumen = pd.DataFrame(resumen_eventos)
        df_resumen.to_excel(writer, sheet_name='Resumen', index=False)

        st.subheader("📥 Descargar Resultados")
        output.seek(0)
        st.download_button(
            label="⬇️ Descargar Excel",
            data=output,
            file_name='resultados_lluvias_inhami.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
