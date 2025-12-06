import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Hotel – Servicios especiales", layout="wide")

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
            
            dr.id_detalle_reserva,
            dr.check_in,
            dr.check_out,
            
            se.id_servicios_especiales,
            se.nombre AS nombre_servicio_especial,
            se.precio AS precio_servicio_catalogo,
            
            drs.precio_unitario AS precio_servicio_reserva,
            drs.subtotal,
            drs.hora
        FROM reserva r
        JOIN detalle_reserva dr 
            ON dr.id_reserva = r.id_reserva
        LEFT JOIN detalle_reserva_servicios_especiales drs
            ON drs.id_detalle_reserva = dr.id_detalle_reserva
        LEFT JOIN servicios_especiales se
            ON se.id_servicios_especiales = drs.id_servicios_especiales;
    """
    df = pd.read_sql(query, engine)
    df["fecha_reserva"] = pd.to_datetime(df["fecha_reserva"])
    df["hora"] = pd.to_datetime(df["hora"])
    df["precio_servicio_catalogo"] = df["precio_servicio_catalogo"].astype(float)
    df["precio_servicio_reserva"] = df["precio_servicio_reserva"].astype(float)
    df["subtotal"] = df["subtotal"].astype(float)
    df["nombre_servicio_especial"] = df["nombre_servicio_especial"].fillna("Sin servicio")
    df["localizacion_reserva"] = df["localizacion_reserva"].fillna("Sin localización")
    df["mes_anio"] = df["fecha_reserva"].dt.to_period("M").astype(str)
    return df


df = load_data(DB_URI)

if df.empty:
    st.warning("No se pudo cargar la información.")
    st.stop()

st.sidebar.header("Filtros – Servicios especiales")

fecha_min = df["fecha_reserva"].min().date()
fecha_max = df["fecha_reserva"].max().date()

rango = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max],
                              min_value=fecha_min, max_value=fecha_max)
if isinstance(rango, (list, tuple)) and len(rango) == 2:
    fi, ff = rango
else:
    fi = ff = fecha_min

servicios = st.sidebar.multiselect(
    "Servicio especial",
    sorted(df["nombre_servicio_especial"].unique().tolist())
)

localizaciones = st.sidebar.multiselect(
    "Localización",
    sorted(df["localizacion_reserva"].unique().tolist())
)

df_fil = df[df["fecha_reserva"].dt.date.between(fi, ff)]

if servicios:
    df_fil = df_fil[df_fil["nombre_servicio_especial"].isin(servicios)]
if localizaciones:
    df_fil = df_fil[df_fil["localizacion_reserva"].isin(localizaciones)]

if df_fil.empty:
    st.warning("No se encontraron resultados.")
    st.stop()

st.title("Servicios especiales")

c1, c2, c3, c4 = st.columns(4)

servicios_usados = df_fil["id_servicios_especiales"].nunique()
reservas_con_servicio = df_fil["id_reserva"].nunique()
monto_catalogo = df_fil["precio_servicio_catalogo"].sum()
monto_reserva = df_fil["precio_servicio_reserva"].sum()

c1.metric("Servicios distintos utilizados", servicios_usados)
c2.metric("Reservas con servicios especiales", reservas_con_servicio)
c3.metric("Monto catálogo (teórico)", f"${monto_catalogo:,.2f}")
c4.metric("Monto aplicado en reservas", f"${monto_reserva:,.2f}")

st.markdown("---")

st.subheader("Detalle de servicios especiales en reservas filtradas")
st.dataframe(df_fil, use_container_width=True)

st.markdown("---")

st.subheader("Visualizaciones")

with st.expander("📊 Monto total por servicio especial"):
    df_serv = (
        df_fil
        .groupby("nombre_servicio_especial", as_index=False)["precio_servicio_reserva"]
        .sum()
        .sort_values("precio_servicio_reserva", ascending=False)
    )
    fig1 = px.bar(df_serv, x="nombre_servicio_especial", y="precio_servicio_reserva",
                  title="Monto total por servicio especial")
    fig1.update_layout(xaxis_title="Servicio especial", yaxis_title="Monto total")
    st.plotly_chart(style_fig(fig1), use_container_width=True)

with st.expander("📊 Servicios por localización"):
    df_loc = (
        df_fil
        .groupby(["localizacion_reserva", "nombre_servicio_especial"], as_index=False)["precio_servicio_reserva"]
        .sum()
    )
    fig2 = px.bar(
        df_loc, x="localizacion_reserva", y="precio_servicio_reserva",
        color="nombre_servicio_especial",
        title="Monto por servicios especiales según localización",
        barmode="stack"
    )
    fig2.update_layout(xaxis_title="Localización", yaxis_title="Monto total")
    st.plotly_chart(style_fig(fig2), use_container_width=True)

with st.expander("📊 Ingresos por servicios especiales en el tiempo"):
    df_ts = (
        df_fil
        .groupby("fecha_reserva", as_index=False)["precio_servicio_reserva"]
        .sum()
        .sort_values("fecha_reserva")
    )
    fig3 = px.line(df_ts, x="fecha_reserva", y="precio_servicio_reserva",
                   title="Ingresos por servicios especiales en el tiempo")
    fig3.update_layout(xaxis_title="Fecha", yaxis_title="Monto servicios")
    st.plotly_chart(style_fig(fig3), use_container_width=True)

st.caption("UNIVALLE – Proyecto Hotel – Página Servicios Especiales")