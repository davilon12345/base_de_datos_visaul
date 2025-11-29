import pandas as pd
from sqlalchemy import create_engine, text

usuario = 'root'
contraseña = ''
host = 'localhost'
puerto = 3306
base = 'blog_univalles'

conexion_str = f'mysql+pymysql://{usuario}:{contraseña}@{host}:{puerto}/{base}'
engine = create_engine(conexion_str)

query="""
   SELECT u.id_usuario, u.nombre_usuario,
       AVG(CHAR_LENGTH(c.cuerpo_comentario)) AS avg_len_coment
    FROM usuario u
    JOIN post p ON p.id_usuario = u.id_usuario
    JOIN comentario c ON c.id_post = p.id_post
    GROUP BY u.id_usuario, u.nombre_usuario
    ORDER BY avg_len_coment DESC;
"""
df = pd.read_sql_query(query, engine)
df.to_csv('avg_len_comentarios_usuarios.csv', index=False)
print(df)