import streamlit as st
import pandas as pd
import glob
import matplotlib.pyplot as plt
import calendar
import numpy as np

st.set_page_config(layout="wide")

# ========================
# CARGA DE DATOS
# ========================

archivos = glob.glob("data/ingresos/*.xlsx")

df = pd.concat([pd.read_excel(f) for f in archivos], ignore_index=True)

# ========================
# LIMPIEZA CLAVE
# ========================

df.columns = df.columns.str.strip()

# detectar nombre correcto columna fecha
col_fecha = [c for c in df.columns if "reserva" in c.lower()][0]
df[col_fecha] = pd.to_datetime(df[col_fecha])

df["Mes"] = df[col_fecha].dt.to_period("M")

# detectar ingreso correcto
col_ingreso = [c for c in df.columns if "ingreso" in c.lower()][0]

# ========================
# CLASIFICACION
# ========================

def clasificar(servicio):
    s = str(servicio).lower()
    if "mensual" in s or "60 horas" in s:
        return "Plan Mensual"
    elif "hora" in s:
        return "Hora"
    else:
        return "Hora"

df["tipo"] = df["Nombre del servicio"].apply(clasificar)

# ========================
# RESUMEN
# ========================

resumen = df.groupby(["Mes","tipo"])[col_ingreso].sum().unstack().fillna(0)

resumen_total = df.groupby("Mes")[col_ingreso].sum()

# ========================
# SELECTOR
# ========================

meses = sorted(resumen_total.index)

mes_sel = st.selectbox("Selecciona mes", meses, index=len(meses)-1)

df_mes = df[df["Mes"] == mes_sel]

ingresos_mes = df_mes[col_ingreso].sum()
reservas_mes = len(df_mes)

# ========================
# PROYECCION CORRECTA
# ========================

hoy = df_mes[col_fecha].dt.day.max()
dias_mes = calendar.monthrange(mes_sel.year, mes_sel.month)[1]

proyeccion = ingresos_mes / hoy * dias_mes if hoy > 0 else ingresos_mes
faltante = max(proyeccion - ingresos_mes, 0)

# ========================
# KPIs
# ========================

col1, col2 = st.columns(2)

col1.metric("Ingresos del mes", f"${ingresos_mes:,.0f}".replace(",","."))
col2.metric("Reservas", reservas_mes)

# ========================
# GRAFICO HISTORICO
# ========================

fig, ax = plt.subplots(figsize=(10,5))

x = np.arange(len(resumen.index))

hora = resumen.get("Hora", pd.Series(0, index=resumen.index)) / 1e6
plan = resumen.get("Plan Mensual", pd.Series(0, index=resumen.index)) / 1e6

ax.bar(x, hora, label="Hora")
ax.bar(x, plan, bottom=hora, label="Plan Mensual")

# PROYECCION SOLO EN ULTIMO MES
idx = list(resumen.index).index(mes_sel)

ax.bar(idx, faltante/1e6, bottom=(hora.iloc[idx]+plan.iloc[idx]), color="gray", label="Proyección")

ax.set_xticks(x)
ax.set_xticklabels([str(m) for m in resumen.index], rotation=45)
ax.set_ylabel("Millones CLP")
ax.set_title("Ingresos históricos + proyección")

ax.legend()

st.pyplot(fig)

# ========================
# TOP CLIENTES
# ========================

top = df_mes["Nombre del cliente"].value_counts().head(5)

st.subheader("Top clientes")

st.dataframe(top.reset_index().rename(columns={
    "index":"Cliente",
    "Nombre del cliente":"Reservas"
}))