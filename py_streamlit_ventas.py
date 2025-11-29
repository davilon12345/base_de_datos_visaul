import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sqlalchemy import create_engine, text

# ============================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Dashboard de Ventas",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cadena por defecto (puedes modificarla aquí)
# DEFAULT_DB_URI = "mysql+pymysql://root@localhost:3306/VENTAS"
DEFAULT_DB_URI = "mysql+pymysql://sql5809370:ljmKmE64CM@sql5.freesqldatabase.com:3306/sql5809370"
# Host: sql5.freesqldatabase.com
#Database name: sql5809370
#Database user: sql5809370
#Database password: ljmKmE64CM
#Port number: 3306
# ============================================================
# FUNCIÓN DE CONEXIÓN (SIN CACHE → evita error de pickling)
# ============================================================
def get_engine(db_uri):
    """Crea un engine SQLAlchemy sin cachearlo (para evitar errores de pickling)."""
    try:
        engine = create_engine(db_uri)
        # Probar la conexión
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"❌ Error conectando a la base de datos:\n{e}")
        return None

# ============================================================
# CARGA DE DATOS (SÍ cacheado → resultado en DataFrame)
# ============================================================
@st.cache_data(ttl=600)
def load_data(db_uri):
    """Carga datos desde la base de datos y los procesa."""
    engine = create_engine(db_uri)

    query = """
        SELECT 
            c.id_compra,
            c.fecha_compra,
            c.monto,
            c.descuento,
            (c.monto - c.descuento) AS monto_neto,

            -- Producto
            p.id_producto,
            p.codigo_producto,
            p.descripcion,
            p.color,

            -- Fábrica
            f.pais AS pais_fabrica,
            f.nombre AS nombre_fabrica,

            -- Sucursal (a través de sucursal_producto)
            s.id_sucursal,
            s.numero_sucursal,
            s.ciudad AS ciudad_sucursal,

            -- Cliente
            cl.id_cliente,
            CONCAT(cl.nombre_cliente, ' ', cl.apellido_paterno, ' ', cl.apellido_materno) AS nombre_cliente,
            cl.codigo_cliente,
            cl.ci,

            -- Ciudad del cliente
            dc.ciudad AS ciudad_cliente,

            -- Tipo de pago (derivado de las tablas de pago)
            CASE 
                WHEN tpq.id_pago_qr IS NOT NULL THEN 'QR'
                WHEN tpt.id_pago_tarjeta IS NOT NULL THEN 'TARJETA'
                WHEN tpe.id_pago_efectivo IS NOT NULL THEN 'EFECTIVO'
                WHEN tptf.id_tipo_pago_transferencia IS NOT NULL THEN 'TRANSFERENCIA'
                ELSE 'SIN_REGISTRO'
            END AS tipo_pago

        FROM compra c
        LEFT JOIN producto p 
            ON p.id_producto = c.id_producto
        LEFT JOIN fabrica f
            ON f.id_fabrica = p.id_fabrica
        LEFT JOIN sucursal_producto sp
            ON sp.id_producto = p.id_producto
        LEFT JOIN sucursal s
            ON s.id_sucursal = sp.id_sucursal
        LEFT JOIN cliente cl 
            ON cl.id_cliente = c.id_cliente
        LEFT JOIN direccion_clientes dc 
            ON dc.id_cliente = cl.id_cliente
        LEFT JOIN tipo_pago_qr tpq
            ON tpq.id_compra = c.id_compra
        LEFT JOIN tipo_pago_tarjeta tpt
            ON tpt.id_compra = c.id_compra
        LEFT JOIN tipo_pago_efectivo tpe
            ON tpe.id_compra = c.id_compra
        LEFT JOIN tipo_pago_transferencia tptf
            ON tptf.id_compra = c.id_compra;
    """

    df = pd.read_sql(query, engine)

    # Conversión de tipos
    df['fecha_compra'] = pd.to_datetime(df['fecha_compra'])

    df['descuento'] = df['descuento'].fillna(0).astype(float)
    df['monto'] = df['monto'].astype(float)
    df['monto_neto'] = df['monto'] - df['descuento']

    # Columnas derivadas de fecha
    df['anio'] = df['fecha_compra'].dt.year
    df['mes'] = df['fecha_compra'].dt.month
    df['dia'] = df['fecha_compra'].dt.day
    df['mes_anio'] = df['fecha_compra'].dt.to_period('M').astype(str)  # ej: 2025-03

    # Limpieza básica de texto / nulos
    df['pais_fabrica'] = df['pais_fabrica'].fillna('Sin país')
    df['ciudad_cliente'] = df['ciudad_cliente'].fillna('Sin ciudad')
    df['ciudad_sucursal'] = df['ciudad_sucursal'].fillna('Sin sucursal')
    df['tipo_pago'] = df['tipo_pago'].fillna('SIN_REGISTRO')

    return df


### FUNCIONES DE FILTRADO ###
def filtrar(df, fechas, productos, ciudades, colores):
    """Filtra el DataFrame según los criterios seleccionados."""
    if isinstance(fechas, (list,tuple)):
        if len(fechas)==2:
            fi,ff= fechas
        elif len(fechas)==1:
            fi,ff= fechas[0]
        else:
            fi=ff=df['fecha_compra'].min().date()
    else:
        fi=ff=fechas
    
    df = df[df['fecha_compra'].dt.date.between(fi, ff)]

    if productos:
        df = df[df['descripcion'].isin(productos)]
    if ciudades:
        df = df[df['ciudad_cliente'].isin(ciudades)]
    if colores:
        df = df[df['color'].isin(colores)]
    return df
# ============================================================
# ======================= INTERFAZ ============================
# ============================================================

st.title("📊 Dashboard de Ventas")

# ============================================================
# Sidebar – cadena de conexión
# ============================================================

db_uri =  DEFAULT_DB_URI

engine= get_engine(db_uri)  # Probar conexión al cargar la app


if engine is None:
    st.stop()

# ============================================================
# Cargar datos
# ============================================================
df = load_data(db_uri)

if df.empty:
    st.warning("No se pudo cargar la información.")
    st.stop()

st.sidebar.header("📊 DASHBOARD VENTAS")

fecha_min = df['fecha_compra'].min().date()
fecha_max = df['fecha_compra'].max().date()

fechas = st.sidebar.date_input("Rango de fechas", 
                               [fecha_min, fecha_max], 
                               min_value=fecha_min, max_value=fecha_max)

productos= st.sidebar.multiselect("Productos",df['descripcion'].unique().tolist())
# combo de ciudades
ciudades = st.sidebar.multiselect("Ciudades", df['ciudad_cliente'].unique().tolist())

colores = st.sidebar.multiselect("Colores", df['color'].unique().tolist())

df_filtrado = filtrar(df, fechas, productos, ciudades, colores)

if df_filtrado.empty:
    st.warning("No se encontraron resultados.")
    st.stop()

# ============================================================
# Visualización
# ============================================================
st.subheader(" INDICADORES")

k1,k2,k3,k4= st.columns(4)
k1.metric("Total Ventas", f"${df_filtrado['monto_neto'].sum():,.2f}")
k2.metric("Número de Compras", len(df_filtrado))
k3.metric("Ventas promedio", f"${df_filtrado['monto_neto'].mean():,.2f}")
if not df_filtrado.empty:
    prod_top=(
        df_filtrado
        .groupby('descripcion')['monto_neto']
        .sum()
        .sort_values(ascending=False)
        .index[0]
    )
else:
    prod_top="N/A"
    
k4.metric("Top Productos mas vendidos", prod_top)

st.divider()

with st.expander("📊 DATOS FILTRADOS"):
    st.dataframe(df_filtrado, use_container_width=True)

    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar CSV", csv, "ventas.csv") 

    st.divider()

st.subheader("Visualizaciones")

tab_tiempo, tab_productos, tab_geograf, tab_tipo_pago = st.tabs(
    [
        "Tiempo",
        "Productos/Clientes",
        "Geografía",
        "Metodos de Pago"
    ]
)
with tab_tiempo:
    
    st.subheader("Tiempo")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("### Ventas netas en el tiempo")
        df_ts=(
            df_filtrado
            .groupby('fecha_compra', as_index=False)['monto_neto']
            .sum()
            .sort_values('fecha_compra')
        )
        with st.expander("📊 DATOS"):
            st.dataframe(df_ts, use_container_width=True)
        with st.expander("📊 Ver gráfico"):
            fig = px.line(df_ts, x='fecha_compra', y='monto_neto', title='Ventas promedio por mes')
            st.plotly_chart(fig, use_container_width=True)
    with col_t2:
        st.markdown("### Distribucion de montos Netos por compra")
        with st.expander("📊 Ver gráfico"):
            fig=px.histogram(df_filtrado, 
                            x='monto_neto', 
                            nbins=20,
                            title='Distribución de montos netos por compra')
            fig.update_layout(xaxis_title="Montos Neto por Compra", yaxis_title="Fecuencias")
            st.plotly_chart(fig, use_container_width=True)

with tab_productos:

    col1_prod, col2_prod = st.columns(2)
    with col1_prod:
        st.subheader("Productos/Clientes")
        df_prod=(
            df_filtrado
            .groupby('descripcion', as_index=False)['monto_neto']
            .sum()
            .sort_values('monto_neto', ascending=False)
            .head(10)
        )
        fig = px.bar(df_prod, 
                    x='descripcion', 
                    y='monto_neto', 
                    title='Ventas netas por producto')
        fig.update_layout(xaxis_title="Producto", yaxis_title="Ventas Netas")
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    with col2_prod:
        st.markdown("### Diagrama de Cajas montos netos por producto")
        top_productos=(
            df_filtrado
            .groupby('descripcion')['monto_neto']
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .index
        )
        df_box= df_filtrado[df_filtrado['descripcion'].isin(top_productos)]
        fig = px.box(df_box, 
                    x='descripcion', 
                    y='monto_neto', 
                    title='Ventas netas por producto')
        fig.update_layout(xaxis_title="Producto", yaxis_title="Ventas Netas")
        st.plotly_chart(fig, use_container_width=True)
        
with tab_geograf:
    
    st.subheader("Geografía")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("### Ventas por ciudad")
        df_city=(
            df_filtrado
            .groupby('ciudad_cliente', as_index=False)['monto_neto']
            .sum()
            .sort_values('monto_neto', ascending=False)
            .head(10)
        )
        fig = px.bar(df_city, 
                    x='ciudad_cliente', 
                    y='monto_neto', 
                    title='Ventas netas por ciudad')
        fig.update_layout(xaxis_title="Ciudad", yaxis_title="Ventas Netas")
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    with col_g2:
        st.markdown("### Ventas por país de fábrica")
        df_tree_agg= df_filtrado.copy()
        df_tree_agg=(
            df_tree_agg
            .groupby(['ciudad_cliente', 'descripcion'], as_index=False)['monto_neto']
            .sum()
        )
        fig = px.treemap(df_tree_agg, 
                        path=['ciudad_cliente', 'descripcion'], 
                        values='monto_neto', 
                        title='Ventas netas por país de fabrica')
        fig.update_layout(xaxis_title="Ciudad", yaxis_title="Ventas Netas")        
        st.plotly_chart(fig, use_container_width=True)
        
with tab_tipo_pago: 
    st.subheader("Métodos de Pago")
    col_tp, col_tp2 = st.columns(2)
    with col_tp:
        st.markdown("### Ventas netas por tipo de pago")
        df_mb=(
            df_filtrado
            .groupby(['mes_anio','tipo_pago'], as_index=False)['monto_neto']
            .sum()
            .sort_values('mes_anio', ascending=False)

        )

        fig = px.bar(df_mb, 
                    x='mes_anio', 
                    y='monto_neto', 
                    color='tipo_pago', 
                    barmode='group',
                    title='Ventas netas por tipo de pago')
        fig.update_layout(xaxis_title="Mes", yaxis_title="Ventas Netas")
        st.plotly_chart(fig, use_container_width=True)
       
    with col_tp2:
        st.markdown("### Ventas por tipo de pago")
        df_pie=(
            df_filtrado
            .groupby('tipo_pago', as_index=False)['monto_neto']
            .sum()
            .sort_values('monto_neto', ascending=False)
        )
        fig = px.pie(df_pie, 
                    values='monto_neto', 
                    names='tipo_pago', 
                    title='Ventas netas por tipo de pago')
        fig.update_layout(xaxis_title="Tipo de Pago", yaxis_title="Ventas Netas")
        st.plotly_chart(fig, use_container_width=True)     
st.caption("UNIVALLE - ASIGNATURA BASES DE DATOS I 2025/II")