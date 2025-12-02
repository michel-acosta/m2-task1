# Importamos el conector de MySQL
import mysql.connector
from mysql.connector import pooling

# Creamos el pool de conexiones
connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    host="64.202.117.89",
    port=3306,
    user="bzbmwhup_mudesweb",
    password="gu)%t@1_$qfI)QKY",
    database="bzbmwhup_mudesweb"
)

# Método que devuelve la conexión a base de datos
def get_connection():
    return connection_pool.get_connection()
