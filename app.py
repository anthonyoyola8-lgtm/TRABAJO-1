import io
import pandas as pd
import plotly.express as px
import streamlit as st

from parser import parse_export

st.set_page_config(page_title="Nivel de Servicio Proveedores", page_icon="📦", layout="wide")


def fmt_int(x):
    return f"{x:,.0f}".replace(",", ".")


def calcular(df, por):
    g = df.groupby(por, as_index=False)[["Solicitado", "Recibido", "No Recibido"]].sum()
    g["% Cumplimiento"] = (g["Recibido"] / g["Solicitado"]).where(g["Solicitado"] > 0)
    return g


def estilo(g, meta):
    def color(v):
        if pd.isna(v):
            return ""
        if v >= meta:
            return "background-color:#d4edda;color:#155724"
        if v >= meta - 0.05:
            return "background-color:#fff3cd;color:#856404"
        return "background-color:#f8d7da;color:#721c24"
    return (g.style.map(color, subset=["% Cumplimiento"])
            .format({"Solicitado": fmt_int, "Recibido": fmt_int, "No Recibido": fmt_int,
                     "% Cumplimiento": "{:.1%}"}, na_rep="-"))


def a_excel(df):
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


@st.cache_data(show_spinner="Procesando archivo...")
def cargar(b):
    return parse_export(io.BytesIO(b))


st.title("📦 Nivel de Servicio de Proveedores")
archivo = st.file_uploader("Sube el Excel exportado", type=["xlsx"])
if not archivo:
    st.info("Sube un archivo Excel para comenzar.")
    st.stop()

try:
    prov, est = cargar(archivo.getvalue())
except Exception as e:
    st.error(f"No pude leer el archivo con el formato esperado: {e}")
    st.stop()
if prov.empty:
    st.warning("No encontré proveedores en el archivo.")
    st.stop()

with st.sidebar:
    meta = st.slider("Meta de nivel de servicio", 0.50, 1.00, 0.95, 0.01, format="%.2f")

tab1, tab2 = st.tabs(["1️⃣ Nivel de servicio por proveedor", "2️⃣ Detalle por estadístico"])

# ---------- Reporte 1 ----------
with tab1:
    t = calcular(prov, ["Código", "Proveedor"]).sort_values("% Cumplimiento")
    sol, rec = t["Solicitado"].sum(), t["Recibido"].sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Solicitado", fmt_int(sol))
    c2.metric("Recibido", fmt_int(rec))
    c3.metric("No recibido", fmt_int(sol - rec))
    c4.metric("Nivel de servicio", f"{rec / sol:.1%}" if sol else "-")

    buscar = st.text_input("Buscar proveedor (código o nombre)", key="b1")
    v = t
    if buscar:
        v = t[t["Código"].str.contains(buscar, case=False) | t["Proveedor"].str.contains(buscar, case=False)]

    top = v.head(20)
    fig = px.bar(top, x="% Cumplimiento", y="Proveedor", orientation="h",
                 text=top["% Cumplimiento"].map(lambda x: f"{x:.1%}"),
                 color="% Cumplimiento", color_continuous_scale="RdYlGn", range_color=[0.5, 1],
                 title="20 proveedores con menor nivel de servicio")
    fig.add_vline(x=meta, line_dash="dash", line_color="gray")
    fig.update_layout(height=max(300, 28 * len(top)), coloraxis_showscale=False,
                      xaxis_tickformat=".0%", yaxis_title=None, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(estilo(v, meta), use_container_width=True, hide_index=True)
    st.download_button("⬇️ Descargar", a_excel(v), "nivel_servicio_proveedores.xlsx")

# ---------- Reporte 2 ----------
with tab2:
    opciones = ["Todos"] + [f"{c} - {n}" for c, n in
                            prov[["Código", "Proveedor"]].drop_duplicates().sort_values("Código").values]
    sel = st.selectbox("Proveedor", opciones)
    e = est if sel == "Todos" else est[est["Cód. Proveedor"] == sel.split(" - ")[0]]

    buscar2 = st.text_input("Buscar estadístico (código o descripción)", key="b2")
    if buscar2:
        e = e[e["Estadístico"].str.contains(buscar2, case=False) | e["Descripción"].str.contains(buscar2, case=False)]

    solo = st.checkbox("Solo estadísticos con faltante (no recibido > 0)")
    if solo:
        e = e[e["No Recibido"] > 0]

    cols = ["Estadístico", "Descripción", "Cód. Proveedor", "Proveedor",
            "Solicitado", "Recibido", "No Recibido"]
    e = e[cols].copy()
    e["% Cumplimiento"] = (e["Recibido"] / e["Solicitado"]).where(e["Solicitado"] > 0)
    e = e.sort_values("No Recibido", ascending=False)

    c1, c2, c3 = st.columns(3)
    c1.metric("Estadísticos", len(e))
    c2.metric("Solicitado", fmt_int(e["Solicitado"].sum()))
    c3.metric("Recibido", fmt_int(e["Recibido"].sum()))

    st.dataframe(estilo(e, meta), use_container_width=True, hide_index=True)
    st.download_button("⬇️ Descargar", a_excel(e), "detalle_estadisticos.xlsx")
