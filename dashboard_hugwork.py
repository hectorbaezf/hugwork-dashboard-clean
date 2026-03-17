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
# FECHAS
# ========================
df["Fecha de reserva"] = pd.to_datetime(df["Fecha de reserva"])
df["Mes"] = df["Fecha de reserva"].dt.to_period("M")

# ========================
# INGRESOS (CLAVE)
# ========================
# USA EXACTAMENTE ESTA COLUMNA (validada contigo)
df["Ingreso"] = df["Ingreso"].astype(float)

# ========================
# CLASIFICACIÓN CORRECTA
# ========================
def clasificar(servicio):
    s = str(servicio).lower()

    if "mensual" in s or "60 horas" in s:
        return "Plan Mensual"
    elif "pack" in s or "horas" in s:
        return "Pack Horas"
    else:
        return "Hora"

df["tipo"] = df["Nombre del servicio"].apply(clasificar)

# ========================
# RESUMEN
# ========================
resumen = df.groupby(["Mes","tipo"])["Ingreso"].sum().unstack().fillna(0)
resumen_total = df.groupby("Mes")["Ingreso"].sum()

# ========================
# SELECTOR
# ========================
meses = sorted(resumen.index)
mes_sel = st.selectbox("Selecciona mes", meses, index=len(meses)-1)

df_mes = df[df["Mes"] == mes_sel]

ingresos_mes = df_mes["Ingreso"].sum()
reservas_mes = len(df_mes)

# ========================
# PROYECCIÓN
# ========================
dia_max = df_mes["Fecha de reserva"].dt.day.max()
dias_mes = calendar.monthrange(mes_sel.year, mes_sel.month)[1]

proyeccion = ingresos_mes / dia_max * dias_mes if dia_max > 0 else ingresos_mes
faltante = max(proyeccion - ingresos_mes, 0)

# ========================
# KPIs
# ========================
col1, col2 = st.columns(2)

col1.metric("Ingresos del mes", f"${int(ingresos_mes):,}".replace(",","."))
col2.metric("Reservas", reservas_mes)

# ========================
# GRAFICO
# ========================
fig, ax = plt.subplots(figsize=(12,5))

x = np.arange(len(resumen.index))

hora = resumen.get("Hora", pd.Series(0, index=resumen.index)) / 1e6
pack = resumen.get("Pack Horas", pd.Series(0, index=resumen.index)) / 1e6
plan = resumen.get("Plan Mensual", pd.Series(0, index=resumen.index)) / 1e6

ax.bar(x, hora, label="Hora")
ax.bar(x, pack, bottom=hora, label="Pack Horas")
ax.bar(x, plan, bottom=hora+pack, label="Plan Mensual")

# SOLO ÚLTIMO MES
idx = list(resumen.index).index(mes_sel)

ax.bar(
    idx,
    faltante/1e6,
    bottom=(hora.iloc[idx]+pack.iloc[idx]+plan.iloc[idx]),
    color="gray",
    label="Proyección"
)

ax.set_xticks(x)
ax.set_xticklabels([str(m) for m in resumen.index], rotation=45)
ax.set_ylabel("Millones CLP")
ax.set_title("Ingresos históricos + proyección")
ax.legend()

st.pyplot(fig)

# ========================
# TOP CLIENTES (CORREGIDO)
# ========================
st.subheader("Top 5 clientes")

top = df_mes["Nombre del cliente"].value_counts().head(5).reset_index()
top.columns = ["Cliente","Reservas"]

st.dataframe(top, use_container_width=True)

# ========================
# PACK RECOMENDACIÓN
# ========================

precio_hora = 6000
pack_10 = 50000

df_hora = df_mes[df_mes["tipo"] == "Hora"]

uso = df_hora.groupby("Nombre del cliente").agg(
    reservas=("Nombre del cliente","count"),
    gasto=("Ingreso","sum")
).reset_index()

def evaluar(row):
    horas = row["reservas"]
    gasto = row["gasto"]

    if horas >= 10:
        ahorro = gasto - pack_10
        return pd.Series(["Pack 10", pack_10, ahorro])
    else:
        return pd.Series(["Sin pack", gasto, 0])

uso[["recomendacion","costo_pack","ahorro"]] = uso.apply(evaluar, axis=1)

tabla = uso[uso["recomendacion"] != "Sin pack"].sort_values("ahorro", ascending=False)

# formato
tabla["pago_actual"] = tabla["gasto"].apply(lambda x: f"${int(x):,}".replace(",","."))
tabla["pago_pack"] = tabla["costo_pack"].apply(lambda x: f"${int(x):,}".replace(",","."))
tabla["ahorro_fmt"] = tabla["ahorro"].apply(lambda x: f"${int(x):,}".replace(",","."))

st.subheader("Clientes con oportunidad de cambio a plan")

st.dataframe(
    tabla[[
        "Nombre del cliente",
        "reservas",
        "pago_actual",
        "recomendacion",
        "pago_pack",
        "ahorro_fmt"
    ]],
    use_container_width=True
)