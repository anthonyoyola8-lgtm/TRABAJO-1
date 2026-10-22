import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from parser import parse_export

st.set_page_config(page_title="Nivel de Servicio Proveedores", page_icon="📦", layout="wide")

# ---------- Utilidades ----------
def fmt_int(x):
    return f"{x:,.0f}".replace(",", ".")

def pct(x):
    return f"{x:.1%}"

def agregar(df, por):
    g = df.groupby(por, as_index=False)[
        ["Solicitado", "Recibido", "No Recibido",
         "Solicitado_ant", "Recibido_ant"]].sum()
    g["% Cumplimiento"] = (g["Recibido"] / g["Solicitado"]).where(g["Solicitado"] > 0)
    g["% Cumpl. Anterior"] = (g["Recibido_ant"] / g["Solicitado_ant"]).where(g["Solicitado_ant"] > 0)
    g["Var. (pp)"] = (g["% Cumplimiento"] - g["% Cumpl. Anterior"]) * 100
    return g

def estilo_tabla(g, meta):
    def color(v):
        if pd.isna(v):
            return ""
        if v >= meta:
            return "background-color:#d4edda;color:#155724"
        if v >= meta - 0.05:
            return "background-color:#fff3cd;color:#856404"
        return "background-color:#f8d7da;color:#721c24"
    return (g.style
            .map(color, subset=["% Cumplimiento"])
            .format({"Solicitado": fmt_int, "Recibido": fmt_int, "No Recibido": fmt_int,
                     "Solicitado_ant": fmt_int, "Recibido_ant": fmt_int,
                     "% Cumplimiento": "{:.1%}", "% Cumpl. Anterior": "{:.1%}",
                     "Var. (pp)": "{:+.1f}"}, na_rep="-"))

def a_excel(hojas: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for nombre, d in hojas.items():
            d.to_excel(w, sheet_name=nombre[:31], index=False)
    return buf.getvalue()

@st.cache_data(show_spinner="Procesando archivo...")
def cargar(bytes_):
    return parse_export(io.BytesIO(bytes_))

# ---------- Carga ----------
st.title("📦 Nivel de Servicio de Proveedores")
archivo = st.file_uploader("Sube el Excel exportado (Solicitado / Recibido por proveedor)", type=["xlsx"])

if not archivo:
    st.info("Sube un archivo Excel para comenzar.")
    st.stop()

try:
    df = cargar(archivo.getvalue())
except Exception as e:
    st.error(f"No pude leer el archivo con el formato esperado: {e}")
    st.stop()

if df.empty:
    st.warning("El archivo no contiene datos de proveedores con el formato esperado.")
    st.stop()

# ---------- Filtros ----------
with st.sidebar:
    st.header("Filtros")
    sucs = sorted(df["Sucursal"].unique())
    f_suc = st.multiselect("Sucursal", sucs, default=sucs)
    ests = sorted(df["Estadístico"].dropna().unique())
    f_est = st.multiselect("Estadístico", ests, default=ests)
    buscar = st.text_input("Buscar proveedor")
    meta = st.slider("Meta de nivel de servicio", 0.50, 1.00, 0.95, 0.01, format="%.2f")
    min_sol = st.number_input("Solicitado mínimo para rankings", min_value=0, value=0, step=100,
                              help="Oculta proveedores con muy poco volumen en los gráficos.")

d = df[df["Sucursal"].isin(f_suc) & df["Estadístico"].isin(f_est)]
if buscar:
    d = d[d["Proveedor"].str.contains(buscar, case=False, na=False)]
if d.empty:
    st.warning("No hay datos con los filtros seleccionados.")
    st.stop()

# ---------- KPIs ----------
sol, rec, norec = d["Solicitado"].sum(), d["Recibido"].sum(), d["No Recibido"].sum()
sol_a, rec_a = d["Solicitado_ant"].sum(), d["Recibido_ant"].sum()
ns = rec / sol if sol else 0
ns_a = rec_a / sol_a if sol_a else None

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Solicitado", fmt_int(sol))
c2.metric("Recibido", fmt_int(rec))
c3.metric("No recibido", fmt_int(norec))
c4.metric("Nivel de servicio", pct(ns),
          f"{(ns - ns_a) * 100:+.1f} pp vs anterior" if ns_a is not None else None)
c5.metric("Proveedores", d["Proveedor"].nunique())

tab1, tab2, tab3, tab4 = st.tabs(["Por proveedor", "Por estadístico", "Proveedor × Sucursal", "Detalle por producto"])

# ---------- Tab 1: proveedor ----------
with tab1:
    gp = agregar(d, "Proveedor").sort_values("% Cumplimiento")
    gp_chart = gp[gp["Solicitado"] >= min_sol]

    n = st.slider("Proveedores a mostrar en el gráfico", 5, min(50, max(5, len(gp_chart))),
                  min(15, max(5, len(gp_chart))))
    orden = st.radio("Mostrar", ["Peores", "Mejores"], horizontal=True)
    top = gp_chart.head(n) if orden == "Peores" else gp_chart.tail(n)

    fig = px.bar(top, x="% Cumplimiento", y="Proveedor", orientation="h",
                 text=top["% Cumplimiento"].map(lambda v: f"{v:.1%}"),
                 color="% Cumplimiento", color_continuous_scale="RdYlGn", range_color=[0.5, 1])
    fig.add_vline(x=meta, line_dash="dash", line_color="gray", annotation_text=f"Meta {meta:.0%}")
    fig.update_layout(height=max(350, 28 * len(top)), coloraxis_showscale=False,
                      xaxis_tickformat=".0%", yaxis_title=None, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # Solicitado vs recibido
    top2 = gp_chart.sort_values("Solicitado", ascending=False).head(15)
    fig2 = go.Figure()
    fig2.add_bar(name="Solicitado", x=top2["Proveedor"], y=top2["Solicitado"])
    fig2.add_bar(name="Recibido", x=top2["Proveedor"], y=top2["Recibido"])
    fig2.update_layout(barmode="group", title="Solicitado vs Recibido — 15 proveedores con más volumen",
                       height=420, margin=dict(l=0, r=0, t=40, b=0), xaxis_title=None)
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Tabla por proveedor")
    st.dataframe(estilo_tabla(gp, meta), use_container_width=True, hide_index=True)
    st.download_button("⬇️ Descargar tabla", a_excel({"Proveedores": gp}),
                       "nivel_servicio_proveedores.xlsx")

# ---------- Tab 2: estadístico ----------
with tab2:
    ge = agregar(d, "Estadístico").sort_values("% Cumplimiento")
    colA, colB = st.columns([1, 1])
    with colA:
        fig = px.bar(ge, x="Estadístico", y="% Cumplimiento",
                     text=ge["% Cumplimiento"].map(lambda v: f"{v:.1%}"))
        fig.add_hline(y=meta, line_dash="dash", line_color="gray")
        fig.update_layout(yaxis_tickformat=".0%", height=380, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with colB:
        m = ge.melt(id_vars="Estadístico", value_vars=["Solicitado", "Recibido", "No Recibido"],
                    var_name="Concepto", value_name="Cantidad")
        fig = px.bar(m, x="Estadístico", y="Cantidad", color="Concepto", barmode="group")
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(estilo_tabla(ge, meta), use_container_width=True, hide_index=True)

    st.subheader("Proveedor × Estadístico")
    pe = agregar(d, ["Proveedor", "Estadístico"]).sort_values(["Estadístico", "% Cumplimiento"])
    st.dataframe(estilo_tabla(pe, meta), use_container_width=True, hide_index=True)

# ---------- Tab 3: sucursal ----------
with tab3:
    gs = agregar(d, "Sucursal")
    st.subheader("Por sucursal")
    st.dataframe(estilo_tabla(gs, meta), use_container_width=True, hide_index=True)

    ps = agregar(d, ["Proveedor", "Sucursal"])
    piv = ps.pivot(index="Proveedor", columns="Sucursal", values="% Cumplimiento")
    piv["_t"] = piv.mean(axis=1)
    piv = piv.sort_values("_t").drop(columns="_t")
    st.subheader("Mapa de calor: nivel de servicio por proveedor y sucursal")
    fig = px.imshow(piv, color_continuous_scale="RdYlGn", zmin=0.5, zmax=1, aspect="auto",
                    labels=dict(color="NS"))
    fig.update_layout(height=max(400, 22 * len(piv)), margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

# ---------- Tab 4: producto ----------
with tab4:
    provs = sorted(d["Proveedor"].unique())
    sel = st.selectbox("Proveedor", provs)
    dp = agregar(d[d["Proveedor"] == sel], ["Estadístico", "Producto"]).sort_values("% Cumplimiento")
    solo_falla = st.checkbox("Solo productos con faltante", value=False)
    if solo_falla:
        dp = dp[dp["No Recibido"] > 0]
    k1, k2, k3 = st.columns(3)
    k1.metric("Productos", len(dp))
    k2.metric("Con faltante", int((dp["No Recibido"] > 0).sum()))
    k3.metric("No recibido", fmt_int(dp["No Recibido"].sum()))
    st.dataframe(estilo_tabla(dp, meta), use_container_width=True, hide_index=True)
