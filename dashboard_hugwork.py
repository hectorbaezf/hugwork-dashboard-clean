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

# limpiar nombres columnas
df.columns = df.columns.str.strip()

# ========================
# DETECTAR COLUMNAS (ROBUSTO)
# ========================
col_fecha = [c for c in df.columns if "reserva" in c.lower()][0]
col_ingreso = [c for c in df.columns if "ingreso" in c.lower()][0]
col_cliente = [c for c in df.columns if "cliente" in c.lower()][0]
col_servicio = [c for c in df.columns if "servicio" in c.lower()][0]

# ========================
# FORMATO
# ========================
df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce")
df[col_ingreso] = pd.to_numeric(df[col_ingreso], errors="coerce").fillna(0)

df["Mes"] = df[col_fecha].dt.to_period("M")

# ========================
# CLASIFICACIÓN PRODUCTO
# ========================
def clasificar(servicio):
    s = str(servicio).lower()

    if "mensual" in s or "60 horas" in s:
        return "Plan Mensual"
    elif "pack" in s or "horas" in s:
        return "Pack Horas"
    else:
        return "Hora"

df["tipo"] = df[col_servicio].apply(clasificar)

# ========================
# RESUMEN
# ========================
resumen = df.groupby(["Mes","tipo"])[col_ingreso].sum().unstack().fillna(0)
resumen_total = df.groupby("Mes")[col_ingreso].sum()

# ========================
# SELECTOR
# ========================
meses = sorted(resumen.index)

mes_sel = st.selectbox("Selecciona mes", meses, index=len(meses)-1)

df_mes = df[df["Mes"] == mes_sel]

ingresos_mes = df_mes[col_ingreso].sum()
reservas_mes = len(df_mes)

# ========================
# PROYECCIÓN
# ========================
dia_max = df_mes[col_fecha].dt.day.max()
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
# GRÁFICO HISTÓRICO
# ========================
fig, ax = plt.subplots(figsize=(12,5))

x = np.arange(len(resumen.index))

hora = resumen.get("Hora", pd.Series(0, index=resumen.index)) / 1e6
pack = resumen.get("Pack Horas", pd.Series(0, index=resumen.index)) / 1e6
plan = resumen.get("Plan Mensual", pd.Series(0, index=resumen.index)) / 1e6

ax.bar(x, hora, label="Hora")
ax.bar(x, pack, bottom=hora, label="Pack Horas")
ax.bar(x, plan, bottom=hora + pack, label="Plan Mensual")

# PROYECCIÓN SOLO EN MES SELECCIONADO
idx = list(resumen.index).index(mes_sel)

ax.bar(
    idx,
    faltante/1e6,
    bottom=(hora.iloc[idx] + pack.iloc[idx] + plan.iloc[idx]),
    color="gray",
    label="Proyección restante"
)

ax.set_xticks(x)
ax.set_xticklabels([str(m) for m in resumen.index], rotation=45)
ax.set_ylabel("Millones CLP")
ax.set_title("Ingresos históricos por tipo de arriendo + proyección")

ax.legend()

st.pyplot(fig)

# ========================
# TOP CLIENTES
# ========================
st.subheader("Top 5 clientes por reservas")

top = df_mes[col_cliente].value_counts().head(5).reset_index()
top.columns = ["Cliente","Reservas"]

st.dataframe(top, use_container_width=True)

# ========================
# RECOMENDACIÓN DE PACK
# ========================
precio_hora = 6000
pack_10 = 50000

df_hora = df_mes[df_mes["tipo"] == "Hora"]

uso = df_hora.groupby(col_cliente).agg(
    reservas=(col_cliente,"count"),
    gasto=(col_ingreso,"sum")
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

# FORMATO CORRECTO (SIN ERROR)
tabla["pago_actual"] = tabla["gasto"].apply(lambda x: f"${int(x):,}".replace(",","."))
tabla["pago_pack"] = tabla["costo_pack"].apply(lambda x: f"${int(x):,}".replace(",","."))
tabla["ahorro_fmt"] = tabla["ahorro"].apply(lambda x: f"${int(x):,}".replace(",", "."))

st.subheader("Clientes con oportunidad de cambio a plan")

st.dataframe(
    tabla[[
        col_cliente,
        "reservas",
        "pago_actual",
        "recomendacion",
        "pago_pack",
        "ahorro_fmt"
    ]].rename(columns={col_cliente: "Cliente"}),
    use_container_width=True
)