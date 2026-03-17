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
# DETECCIÓN COLUMNAS
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

# 🚨 DEBUG CLAVE (puedes borrar después)
st.write("Filas totales:", len(df))

# ========================
# CLASIFICACIÓN
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
# SELECTOR
# ========================
meses = sorted(df["Mes"].dropna().unique())

mes_sel = st.selectbox("Selecciona mes", meses, index=len(meses)-1)

df_mes = df[df["Mes"] == mes_sel]

# DEBUG
st.write("Filas mes seleccionado:", len(df_mes))

ingresos_mes = df_mes[col_ingreso].sum()
reservas_mes = len(df_mes)

# ========================
# KPIs
# ========================
col1, col2 = st.columns(2)

col1.metric("Ingresos del mes", f"${int(ingresos_mes):,}".replace(",","."))
col2.metric("Reservas", reservas_mes)

# ========================
# PROYECCIÓN
# ========================
dia_max = df_mes[col_fecha].dt.day.max()
dias_mes = calendar.monthrange(mes_sel.year, mes_sel.month)[1]

proyeccion = ingresos_mes / dia_max * dias_mes if dia_max > 0 else ingresos_mes
faltante = max(proyeccion - ingresos_mes, 0)

# ========================
# HISTÓRICO
# ========================
resumen = df.groupby(["Mes","tipo"])[col_ingreso].sum().unstack().fillna(0)

fig, ax = plt.subplots(figsize=(12,5))

x = np.arange(len(resumen.index))

hora = resumen.get("Hora", 0) / 1e6
pack = resumen.get("Pack Horas", 0) / 1e6
plan = resumen.get("Plan Mensual", 0) / 1e6

ax.bar(x, hora, label="Hora")
ax.bar(x, pack, bottom=hora, label="Pack Horas")
ax.bar(x, plan, bottom=hora+pack, label="Plan Mensual")

# SOLO mes seleccionado
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
# TORTAS (AGREGADAS DE NUEVO)
# ========================
colA, colB = st.columns(2)

# espacio
if "Nombre de la agenda" in df_mes.columns:
    espacio = df_mes.groupby("Nombre de la agenda")[col_ingreso].sum()

    colA.subheader("Ingresos por espacio")
    colA.pyplot(espacio.plot.pie(autopct="%1.1f%%", figsize=(4,4)).figure)

# tipo
tipo_mes = df_mes.groupby("tipo")[col_ingreso].sum()

colB.subheader("Ingresos por tipo de arriendo")
colB.pyplot(tipo_mes.plot.pie(autopct="%1.1f%%", figsize=(4,4)).figure)

# ========================
# TOP CLIENTES
# ========================
st.subheader("Top 5 clientes")

top = df_mes[col_cliente].value_counts().head(5).reset_index()
top.columns = ["Cliente","Reservas"]

st.dataframe(top, use_container_width=True)

# ========================
# RECOMENDACIÓN
# ========================
df_hora = df_mes[df_mes["tipo"] == "Hora"]

uso = df_hora.groupby(col_cliente).agg(
    reservas=(col_cliente,"count"),
    gasto=(col_ingreso,"sum")
).reset_index()

def evaluar(row):
    if row["reservas"] >= 10:
        ahorro = row["gasto"] - 50000
        return pd.Series(["Pack 10", 50000, ahorro])
    else:
        return pd.Series(["Sin pack", row["gasto"], 0])

uso[["plan","costo","ahorro"]] = uso.apply(evaluar, axis=1)

tabla = uso[uso["plan"] != "Sin pack"].sort_values("ahorro", ascending=False)

tabla["actual"] = tabla["gasto"].apply(lambda x: f"${int(x):,}".replace(",","."))
tabla["plan_fmt"] = tabla["costo"].apply(lambda x: f"${int(x):,}".replace(",","."))
tabla["ahorro_fmt"] = tabla["ahorro"].apply(lambda x: f"${int(x):,}".replace(",",".") )

st.subheader("Clientes con oportunidad de ahorro")

st.dataframe(
    tabla[[col_cliente,"reservas","actual","plan","plan_fmt","ahorro_fmt"]]
    .rename(columns={col_cliente:"Cliente"}),
    use_container_width=True
)