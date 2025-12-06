import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Hotel – Localización y Pagos", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #e8d9c4 !important; }
.block-container { color: #2b1a0f !important; }
h1, h2, h3, h4, h5, h6, p, span, label { color: #2b1a0f !important; }
[data-testid="stSidebar"] { background-color: #7b4a26 !important; }
[data-testid="stSidebar"] * { color: #ffffff !important; }
[data-testid="stHeader"] * { color: #ffffff !important; }
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #5c371c, #7b4a26);
    padding: 12px;
    border-radius: 10px;
    border: 1px solid #3e2723;
}
[data-testid="stMetric"] * { color: #ffffff !important; }
details {
    background-color: #d1b792 !important;
    border-radius: 8px;
    padding: 0.4rem 0.7rem;
    border: 1px solid #8d6e63;
}
summary { font-weight: 700 !important; color: #2b1a0f !important; }
[data-testid="stDataFrame"] { color: #2b1a0f !important; }
</style>
""", unsafe_allow_html=True)

WOOD_COLORS = ["#4b2e1a", "#6d4c3d", "#8d6e63", "#a1887f", "#3e2723"]
px.defaults.color_discrete_sequence = WOOD_COLORS


def style_fig(fig):
    fig.update_layout(
        paper_bgcolor="#c7ab85",
        plot_bgcolor="#e1c39b",
        font_color="#1c130d",
        title_font_color="#1c130d",
        xaxis=dict(title_font_color="#1c130d", tickfont=dict(color="#1c130d")),
        yaxis=dict(title_font_color="#1c130d", tickfont=dict(color="#1c130d")),
    )
    return fig


DB_URI = "mysql+pymysql://root@localhost:3306/proyecto"


@st.cache_data(ttl=600)
def load_data(db_uri: str):
    engine = create_engine(db_uri)
    query = """
        SELECT 
            r.id_reserva,
            r.fecha_reserva,
            r.monto_total,
            r.estado_reserva,
            r.localizacion_reserva,
            
            p.id_pago,
            p.monto AS monto_pago,
            p.estado_pago AS estado_pago_sistema,
            p.fecha_pago,
            
            ep.nombre_estado_pago,
            
            mp.id_metodo_pago,
            mp.nombre AS metodo_pago_nombre
        FROM reserva r
        LEFT JOIN pago p
            ON p.id_reserva = r.id_reserva
        LEFT JOIN detalle_pago dp
            ON dp.id_detalle_pago = p.id_detalle_pago
        LEFT JOIN metodo_pago mp
            ON mp.id_metodo_pago = dp.id_metodo_pago
        LEFT JOIN estado_pago ep
            ON ep.id_estado_pago = p.id_estado_pago;
    """
    df = pd.read_sql(query, engine)
    df["fecha_reserva"] = pd.to_datetime(df["fecha_reserva"])
    df["fecha_pago"] = pd.to_datetime(df["fecha_pago"])
    df["monto_total"] = df["monto_total"].astype(float)
    df["monto_pago"] = df["monto_pago"].astype(float)
    df["localizacion_reserva"] = df["localizacion_reserva"].fillna("Sin localización")
    df["metodo_pago_nombre"] = df["metodo_pago_nombre"].fillna("Sin método")
    df["nombre_estado_pago"] = df["nombre_estado_pago"].fillna("Sin estado")
    df["mes_anio"] = df["fecha_reserva"].dt.to_period("M").astype(str)
    return df


df = load_data(DB_URI)

if df.empty:
    st.warning("No se pudo cargar la información.")
    st.stop()

st.sidebar.header("Filtros – Localización y pagos")

fecha_min = df["fecha_reserva"].min().date()
fecha_max = df["fecha_reserva"].max().date()

rango = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max],
                              min_value=fecha_min, max_value=fecha_max)
if isinstance(rango, (list, tuple)) and len(rango) == 2:
    fi, ff = rango
else:
    fi = ff = fecha_min

localizaciones = st.sidebar.multiselect(
    "Localización",
    sorted(df["localizacion_reserva"].unique().tolist())
)

metodos = st.sidebar.multiselect(
    "Método de pago",
    sorted(df["metodo_pago_nombre"].unique().tolist())
)

estados_pago = st.sidebar.multiselect(
    "Estado del pago",
    sorted(df["nombre_estado_pago"].unique().tolist())
)

df_fil = df[df["fecha_reserva"].dt.date.between(fi, ff)]

if localizaciones:
    df_fil = df_fil[df_fil["localizacion_reserva"].isin(localizaciones)]
if metodos:
    df_fil = df_fil[df_fil["metodo_pago_nombre"].isin(metodos)]
if estados_pago:
    df_fil = df_fil[df_fil["nombre_estado_pago"].isin(estados_pago)]

if df_fil.empty:
    st.warning("No se encontraron resultados.")
    st.stop()

st.title("Localización y pagos")

c1, c2, c3, c4 = st.columns(4)

reservas = df_fil["id_reserva"].nunique()
monto_total = df_fil.drop_duplicates("id_reserva")["monto_total"].sum()
pagos_realizados = df_fil["id_pago"].nunique()
monto_pagado = (
    df_fil.dropna(subset=["id_pago"])
    .drop_duplicates("id_pago")["monto_pago"]
    .sum()
)

c1.metric("Reservas únicas", reservas)
c2.metric("Monto total (reservas)", f"${monto_total:,.2f}")
c3.metric("Pagos registrados", pagos_realizados)
c4.metric("Monto total pagado", f"${monto_pagado:,.2f}")

st.markdown("---")

st.subheader("Reservas y pagos filtrados")
st.dataframe(df_fil, use_container_width=True)

st.markdown("---")

st.subheader("Visualizaciones")

with st.expander("📊 Monto total por localización"):
    df_loc = (
        df_fil
        .drop_duplicates("id_reserva")
        .groupby("localizacion_reserva", as_index=False)["monto_total"]
        .sum()
        .sort_values("monto_total", ascending=False)
    )
    fig1 = px.bar(df_loc, x="localizacion_reserva", y="monto_total",
                  title="Monto total por localización")
    fig1.update_layout(xaxis_title="Localización", yaxis_title="Monto total")
    st.plotly_chart(style_fig(fig1), use_container_width=True)

with st.expander("📊 Monto pagado por método de pago"):
    df_mp = (
        df_fil
        .dropna(subset=["id_pago"])
        .drop_duplicates("id_pago")
        .groupby("metodo_pago_nombre", as_index=False)["monto_pago"]
        .sum()
        .sort_values("monto_pago", ascending=False)
    )
    fig2 = px.bar(df_mp, x="metodo_pago_nombre", y="monto_pago",
                  title="Monto pagado por método de pago")
    fig2.update_layout(xaxis_title="Método de pago", yaxis_title="Monto pagado")
    st.plotly_chart(style_fig(fig2), use_container_width=True)

with st.expander("📊 Distribución de montos por estado de pago"):
    df_pe = (
        df_fil
        .dropna(subset=["id_pago"])
        .drop_duplicates("id_pago")
        .groupby("nombre_estado_pago", as_index=False)["monto_pago"]
        .sum()
    )
    fig3 = px.pie(df_pe, values="monto_pago", names="nombre_estado_pago",
                  title="Distribución de montos por estado de pago")
    st.plotly_chart(style_fig(fig3), use_container_width=True)

st.caption("UNIVALLE – Proyecto Hotel – Página Localización y Pagos")