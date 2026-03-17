import streamlit as st
import pandas as pd
import glob
import matplotlib.pyplot as plt
import calendar
import numpy as np

st.set_page_config(layout="wide")

# ========================
# CARGA
# ========================
archivos = glob.glob("data/ingresos/*.xlsx")
df = pd.concat([pd.read_excel(f) for f in archivos], ignore_index=True)

df.columns = df.columns.str.strip()

# ========================
# NORMALIZACIÓN (CLAVE 🔥)
# ========================

# FECHA
col_fecha = [c for c in df.columns if "reserva" in c.lower()][0]

# CLIENTE
col_cliente = [c for c in df.columns if "cliente" in c.lower()][0]

# SERVICIO
col_servicio = [c for c in df.columns if "servicio" in c.lower()][0]

# 🔥 INGRESO CORRECTO (PRIORIDAD)
if "Precio del servicio $CLP" in df.columns:
    df["Ingreso_final"] = pd.to_numeric(df["Precio del servicio $CLP"], errors="coerce")
elif "Ingreso" in df.columns:
    df["Ingreso_final"] = pd.to_numeric(df["Ingreso"], errors="coerce")
else:
    # fallback automático
    col_ingreso = [c for c in df.columns if "ingreso" in c.lower()][0]
    df["Ingreso_final"] = pd.to_numeric(df[col_ingreso], errors="coerce")

df["Ingreso_final"] = df["Ingreso_final"].fillna(0)

# ========================
# FORMATO
# ========================
df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce")
df["Mes"] = df[col_fecha].dt.to_period("M")

# ========================
# CLASIFICACIÓN (MISMA QUE JUPYTER)
# ========================
def clasificar(servicio):
    s = str(servicio).lower()

    if "mensual" in s or "60 horas" in s:
        return "Plan Mensual"
    elif "pack" in s or "horas" in s or "factura" in s:
        return "Pack Horas"
    else:
        return "Hora"

df["tipo"] = df[col_servicio].apply(clasificar)

# ========================
# SELECTOR
# ========================
meses = sorted(df["Mes"].dropna().unique())
mes_sel = st.selectbox("Selecciona mes", meses, index=len(meses)-1)

df_mes = df[df["Mes"] == mes_sel].copy()

# ========================
# KPIs
# ========================
ingresos_mes = df_mes["Ingreso_final"].sum()
reservas_mes = len(df_mes)

col1, col2 = st.columns(2)

col1.metric("Ingresos del mes", f"${int(ingresos_mes):,}".replace(",","."))
col2.metric("Reservas", reservas_mes)

# ========================
# HISTÓRICO
# ========================
resumen = df.groupby(["Mes","tipo"])["Ingreso_final"].sum().unstack().fillna(0)

for col in ["Hora","Pack Horas","Plan Mensual"]:
    if col not in resumen.columns:
        resumen[col] = 0

resumen = resumen[["Hora","Pack Horas","Plan Mensual"]]

fig, ax = plt.subplots(figsize=(12,5))

x = np.arange(len(resumen.index))

hora = resumen["Hora"] / 1e6
pack = resumen["Pack Horas"] / 1e6
plan = resumen["Plan Mensual"] / 1e6

ax.bar(x, hora, label="Hora")
ax.bar(x, pack, bottom=hora, label="Pack Horas")
ax.bar(x, plan, bottom=hora+pack, label="Plan Mensual")

# PROYECCIÓN
dia_max = df_mes[col_fecha].dt.day.max()
dias_mes = calendar.monthrange(mes_sel.year, mes_sel.month)[1]

proyeccion = ingresos_mes / dia_max * dias_mes if dia_max > 0 else ingresos_mes
faltante = max(proyeccion - ingresos_mes, 0)

idx = list(resumen.index).index(mes_sel)

ax.bar(idx, faltante/1e6,
       bottom=(hora.iloc[idx]+pack.iloc[idx]+plan.iloc[idx]),
       color="gray", label="Proyección")

ax.set_xticks(x)
ax.set_xticklabels([str(m) for m in resumen.index], rotation=45)
ax.set_ylabel("Millones CLP")
ax.set_title("Ingresos históricos + proyección")

ax.legend()
st.pyplot(fig)

# ========================
# TORTAS CORRECTAS
# ========================
colA, colB = st.columns(2)

if "Nombre de la agenda" in df_mes.columns:
    espacio = df_mes.groupby("Nombre de la agenda")["Ingreso_final"].sum()

    fig1, ax1 = plt.subplots()
    ax1.pie(espacio, labels=espacio.index, autopct="%1.1f%%")
    ax1.set_title("Ingresos por espacio")
    colA.pyplot(fig1)

tipo_mes = df_mes.groupby("tipo")["Ingreso_final"].sum()

fig2, ax2 = plt.subplots()
ax2.pie(tipo_mes, labels=tipo_mes.index, autopct="%1.1f%%")
ax2.set_title("Ingresos por tipo de arriendo")

colB.pyplot(fig2)

# ========================
# DEBUG FINAL (puedes borrar después)
# ========================
st.write("Ingreso validación:", ingresos_mes)