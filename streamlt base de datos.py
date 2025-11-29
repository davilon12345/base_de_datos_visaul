import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st

st.title('Blog UNIVALLE')
st.set_page_config(page_title='Blog', page_icon='📝', layout='wide')

usuario = 'root'
contraseña = ''
host = 'localhost'
puerto = 3306
base = 'blog_univalles'

conexion_str = f'mysql+pymysql://{usuario}:{contraseña}@{host}:{puerto}/{base}'
engine = create_engine(conexion_str)

query="""
   SELECT 
    p.id_post,
    p.titulo,
    p.fecha_publicacion,
    u.nombre_usuario AS autor,
    GROUP_CONCAT(e.texto_etiqueta SEPARATOR ', ') AS etiquetas
FROM post p
JOIN usuario u ON u.id_usuario = p.id_usuario
LEFT JOIN etiqueta e ON e.id_post = p.id_post
GROUP BY p.id_post, p.titulo, p.fecha_publicacion, u.nombre_usuario
ORDER BY p.fecha_publicacion DESC;
"""
df = pd.read_sql_query(query, engine)
##df.to_csv('avg_len_comentarios_usuarios.csv', index=False)
st.write(df)

## SIDE BAR FILTROS
st.sidebar.title('Filtros')

texto_busqueda= st.sidebar.text_input('Buscar en titulo  etiqueta', 
                      value='',help='Buscar por titulo o etiqueta')

autores = df['autor'].unique().tolist()
autor_sel= st.sidebar.selectbox('Autor', autores)

fecha_min = df['fecha_publicacion'].min()
fecha_max = df['fecha_publicacion'].max()

#st.write(autores)
rango_fechas=st.sidebar.date_input('Fecha publicacion', 
                      value=fecha_min, 
                      min_value=fecha_min, 
                      max_value=fecha_max,
                      help='Filtrar por fecha de publicacion')

modo_vista=st.sidebar.radio("Modo Vista",
                            ['Tabla Completa','Primeros 5 resultados']
                            )

cols_sel= st.sidebar.multiselect("Ver solo estas columnas",
                        df.columns.tolist(),
                        default=df.columns.tolist()
                        )

df_filtrado=df.copy()

#filtro por texto

# Filtro por texto
if texto_busqueda.strip():
    txt = texto_busqueda.strip().lower()
    df_filtrado = df_filtrado[
        df_filtrado["titulo"].str.lower().str.contains(txt, na=False)
        | df_filtrado["etiquetas"].str.lower().str.contains(txt, na=False)
    ]

if cols_sel:
    df_filtrado = df_filtrado[cols_sel]

# Filtro por autor
if autor_sel:
    df_filtrado = df_filtrado[df_filtrado["autor"] == autor_sel]


st.write(df_filtrado)