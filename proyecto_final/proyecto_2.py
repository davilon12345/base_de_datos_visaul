import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Hotel – Habitaciones y Clientes", layout="wide")

st.markdown("""
<style>
.stApp {
    background-color: #e8d9c4 !important;
}
.block-container {
    color: #2b1a0f !important;
}
h1, h2, h3, h4, h5, h6, p, span, label {
    color: #2b1a0f !important;
}
[data-testid="stSidebar"] {
    background-color: #7b4a26 !important;
}
[data-testid="stSidebar"] * {
    color: #ffffff !important;
}
[data-testid="stHeader"] * {
    color: #ffffff !important;
}
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #5c371c, #7b4a26);
    padding: 12px;
    border-radius: 10px;
    border: 1px solid #3e2723;
}
[data-testid="stMetric"] * {
    color: #ffffff !important;
}
details {
    background-color: #d1b792 !important;
    border-radius: 8px;
    padding: 0.4rem 0.7rem;
    border: 1px solid #8d6e63;
}
summary {
    font-weight: 700 !important;
    color: #2b1a0f !important;
}
[data-testid="stDataFrame"] {
    color: #2b1a0f !important;
}
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
            
            c.id_cliente,
            CONCAT(c.nombre, ' ', c.apellido_paterno, ' ', c.apellido_materno) AS nombre_cliente,
            c.ci,
            
            h.id_habitacion,
            h.numero_habitacion,
            h.piso,
            h.precio AS tarifa_noche,
            
            th.id_tipo_habitacion,
            th.tipo_cama,
            th.numero_camas,
            th.descripcion AS descripcion_tipo_habitacion,
            th.capacidad,
            
            dr.id_detalle_reserva,
            dr.cantidad_personas,
            dr.check_in,
            dr.check_out
        FROM reserva r
        JOIN cliente c ON c.id_cliente = r.id_cliente
        JOIN detalle_reserva dr ON dr.id_reserva = r.id_reserva
        JOIN habitacion h ON h.id_habitacion = dr.id_habitacion
        JOIN tipo_habitacion th ON th.id_tipo_habitacion = h.id_tipo_habitacion;
    """
    df = pd.read_sql(query, engine)
    df["fecha_reserva"] = pd.to_datetime(df["fecha_reserva"])
    df["check_in"] = pd.to_datetime(df["check_in"])
    df["check_out"] = pd.to_datetime(df["check_out"])
    df["tarifa_noche"] = df["tarifa_noche"].astype(float)
    df["noches"] = (df["check_out"] - df["check_in"]).dt.days
    df["mes_anio"] = df["fecha_reserva"].dt.to_period("M").astype(str)
    df["descripcion_tipo_habitacion"] = df["descripcion_tipo_habitacion"].fillna("Sin descripción")
    return df


df = load_data(DB_URI)

if df.empty:
    st.warning("No se pudo cargar información.")
    st.stop()

st.sidebar.header("Filtros – Habitaciones y clientes")

fecha_min = df["fecha_reserva"].min().date()
fecha_max = df["fecha_reserva"].max().date()

rango = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max],
                              min_value=fecha_min, max_value=fecha_max)
if isinstance(rango, (list, tuple)) and len(rango) == 2:
    fi, ff = rango
else:
    fi = ff = fecha_min

tipos_h = st.sidebar.multiselect(
    "Tipo de habitación",
    sorted(df["descripcion_tipo_habitacion"].unique().tolist())
)

df_fil = df[df["fecha_reserva"].dt.date.between(fi, ff)]

if tipos_h:
    df_fil = df_fil[df_fil["descripcion_tipo_habitacion"].isin(tipos_h)]

if df_fil.empty:
    st.warning("No se encontraron resultados con los filtros.")
    st.stop()

st.title("Habitaciones y clientes")

c1, c2, c3, c4 = st.columns(4)

hab_distintas = df_fil["id_habitacion"].nunique()
tipos_distintos = df_fil["id_tipo_habitacion"].nunique()
clientes_distintos = df_fil["id_cliente"].nunique()
noches_prom = df_fil.drop_duplicates("id_reserva")["noches"].mean()

c1.metric("Habitaciones distintas reservadas", hab_distintas)
c2.metric("Tipos de habitación utilizados", tipos_distintos)
c3.metric("Clientes distintos", clientes_distintos)
c4.metric("Promedio de noches por reserva", f"{noches_prom:,.2f}")

st.markdown("---")

st.subheader("Reservas filtradas – detalle de habitaciones y clientes")
st.dataframe(df_fil, use_container_width=True)

st.markdown("---")

st.subheader("Visualizaciones")

with st.expander("📊 Monto total por tipo de habitación"):
    df_tipo = (
        df_fil
        .drop_duplicates("id_reserva")
        .groupby("descripcion_tipo_habitacion", as_index=False)["monto_total"]
        .sum()
        .sort_values("monto_total", ascending=False)
    )
    fig1 = px.bar(df_tipo, x="descripcion_tipo_habitacion", y="monto_total",
                  title="Monto total por tipo de habitación")
    fig1.update_layout(xaxis_title="Tipo de habitación", yaxis_title="Monto total")
    st.plotly_chart(style_fig(fig1), use_container_width=True)

with st.expander("📊 Top 10 clientes por noches reservadas"):
    df_noches = (
        df_fil
        .drop_duplicates("id_reserva")
        .groupby("nombre_cliente", as_index=False)["noches"]
        .sum()
        .sort_values("noches", ascending=False)
        .head(10)
    )
    fig2 = px.bar(df_noches, x="nombre_cliente", y="noches",
                  title="Top 10 clientes por noches reservadas")
    fig2.update_layout(xaxis_title="Cliente", yaxis_title="Noches")
    st.plotly_chart(style_fig(fig2), use_container_width=True)

with st.expander("📊 Relación tarifa noche vs cantidad de personas"):
    fig3 = px.scatter(
        df_fil.drop_duplicates("id_detalle_reserva"),
        x="tarifa_noche",
        y="cantidad_personas",
        color="descripcion_tipo_habitacion",
        title="Tarifa por noche vs cantidad de personas",
        hover_data=["numero_habitacion", "nombre_cliente"]
    )
    fig3.update_layout(xaxis_title="Tarifa por noche", yaxis_title="Cantidad de personas")
    st.plotly_chart(style_fig(fig3), use_container_width=True)

st.caption("UNIVALLE – Proyecto Hotel – Página Habitaciones y Clientes")