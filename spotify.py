from flask import Blueprint, redirect, request, jsonify
from db import get_connection
import base64
import os
import requests
import time
from urllib.parse import urlencode

# Guardamos el blueprint para poder usarlo desde otros ficheros
spotify_bp = Blueprint('spotify', __name__)

# Credenciales de la API de Spotify
CLIENT_ID = "cd3607f9979b420a9fdff834d4cc9027"
CLIENT_SECRET = "6bb27222d53542cba27aed0d9d19a4c3"

# URLs de Spotify que usaremos
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
REDIRECT_URI = "https://michelacosta.com/mudesweb_m2_t1.php"

# Token y caducidad del mismo para Client Credentials
ACCESS_TOKEN = None
EXPIRES_AT = 0

# Access token y refresh token para authentication code flow
ACCESS_TOKEN2 = None 
REFRESH_TOKEN2 = None

# ==================================================================================== #
# MÉTODOS AUXILIARES PARA AUTENTICACIÓN CON CLIENT CREDENTIALS (sin login del usuario) #
# ==================================================================================== #

# Método para obtener el token de la BD
def load_token_from_db():
    global ACCESS_TOKEN, EXPIRES_AT

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # El id siempre será 1 porque hacemos un truncate antes de insertarlo
        cursor.execute("SELECT access_token, expires_at FROM m2t1_spotify WHERE id = 1")
        row = cursor.fetchone()

        if row:
            ACCESS_TOKEN = row["access_token"]
            EXPIRES_AT = row["expires_at"]

    finally:
        cursor.close()
        conn.close()

# Método para guardar el token en la BD
def save_token_to_db(token, expires_in):
    global ACCESS_TOKEN, EXPIRES_AT

    ACCESS_TOKEN = token
    # tiempo actual + tiempo de expiración que nos dice Spotify - 10 segundos de margen por seguridad
    EXPIRES_AT = int(time.time()) + expires_in - 10    

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Truncamos la tabla siempre antes de insertar el token, así nos aseguramos de que siempre haya solo uno
        # Esto es solamente para este test porque no habrá concurrencia ni gestión de usuarios reales
        cursor.execute("TRUNCATE TABLE m2t1_spotify")
        sql = "INSERT INTO m2t1_spotify (access_token, expires_at) VALUES (%s, %s)"
        cursor.execute(sql, (ACCESS_TOKEN, EXPIRES_AT))
        conn.commit()

    finally:
        cursor.close()
        conn.close()

# Método para pedir un nuevo token (solo sirve para obtener datos que no son propios del usuario logueado)
def request_new_token():

    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    data = {"grant_type": "client_credentials"}
    headers = {"Authorization": f"Basic {auth_header}"}

    # Aquí se hace el post a la URL de spotify con las credenciales de acceso
    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers)
    token_info = response.json()

    token = token_info.get("access_token")
    expires_in = token_info.get("expires_in", 3600)

    # Guardamos en nuestra BD el token y su expiración, procedentes de Spotify
    save_token_to_db(token, expires_in)

    return token

# Método para obtener el token
def get_access_token():
    global ACCESS_TOKEN, EXPIRES_AT

    # En el primer acceso, buscamos en nuestra BD a ver si hay token
    if ACCESS_TOKEN is None:
        load_token_from_db()

    # Si sigue siendo None es que todavía no había token. Pedimos uno.
    if ACCESS_TOKEN is None:
        return request_new_token()

    # En caso de tener un token, pero expirado, pedimos otro.
    if time.time() >= EXPIRES_AT:
        return request_new_token()

    return ACCESS_TOKEN

# Método por el que pasarán todas nuestras llamadas a la API de Spotify cuando estemos usando Client Credentials
def spotify_get(endpoint, params=None):
    # Pedimos el token
    token = get_access_token()
    # Lo añadimos como header de autorización
    headers = {"Authorization": f"Bearer {token}"}

    url = f"{SPOTIFY_API_URL}{endpoint}"
    # Lanzamos el GET con los parámetros que hemos recibido
    response = requests.get(url, headers=headers, params=params)

    # Si Spotify nos responde con un HTTP 401...
    if response.status_code == 401:
        # Pedimos un nuevo token
        token = request_new_token()
        headers["Authorization"] = f"Bearer {token}"
        # Volvemos a intentar el GET
        response = requests.get(url, headers=headers, params=params)

    return response.json()

# ============================ #
# ENDPOINTS CLIENT CREDENTIALS #
# ============================ #

# Para ver los datos del token actual en la BD
@spotify_bp.route("/spotify/token", methods=['GET'])
def token():
    token = get_access_token()
    return jsonify({"access_token": token, "expires_at": EXPIRES_AT})

# Obtiene una lista de artistas (recibe un parámetro "q" que es lo que el usuario quiere buscar)
# Si "q" está vacío, usamos "Jamiroquai" por defecto (imposición mía, sorry)
@spotify_bp.route("/spotify/artists", methods=['GET'])
def artistas():
    q = request.args.get("q", "jamiroquai")

    params = {
        "q": q,
        "type": "artist",
        "limit": 10
    }

    data = spotify_get("/search", params=params)
    return jsonify(data)

# ========================================================================================= #
# MÉTODOS AUXILIARES PARA AUTENTICACIÓN CON AUTHORIZATION CODE FLOW (con login del usuario) #
# ========================================================================================= #

# Método que refresca el token si falla el GET
def refresh_access_token():
    global ACCESS_TOKEN2, REFRESH_TOKEN2

    if not REFRESH_TOKEN2:
        return None

    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN2
    }

    headers = {
        "Authorization": f"Basic {auth_header}"
    }

    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers)
    
    token_info = response.json()

    ACCESS_TOKEN2 = token_info.get("access_token")
    return ACCESS_TOKEN2

# Método por el que pasarán todas nuestras llamadas a la API de Spotify cuando estemos usando Authorization Code Flow
def spotify_get2(url, params=None):
    global ACCESS_TOKEN2

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN2}"
    }
    r = requests.get(url, headers=headers, params=params)

    # Si el token está caducado, forzamos que se refresque
    if r.status_code == 401:
        refresh_access_token()
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN2}"
        r = requests.get(url, headers=headers, params=params)

    return r.json()

# ================================== #
# ENDPOINTS AUTHENTICATION CODE FLOW #
# ================================== #

# Lanza el proceso de login de Spotify
@spotify_bp.route("/spotify/login", methods=['GET'])
def login():
    scope = "user-read-private user-top-read"
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": scope
    }
    return redirect(f"{SPOTIFY_AUTH_URL}?{urlencode(params)}")

# Recoge los parámetros de Spotify a la vuelta del login
@spotify_bp.route("/spotify/callback", methods=['GET'])
def callback():
    global ACCESS_TOKEN2, REFRESH_TOKEN2

    code = request.args.get("code")

    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers)
    token_info = response.json()

    ACCESS_TOKEN2 = token_info.get("access_token")
    REFRESH_TOKEN2 = token_info.get("refresh_token")

    return jsonify({
        "message": "Auth OK",
        "access_token": ACCESS_TOKEN2,
        "refresh_token": REFRESH_TOKEN2
    })

# Método para obtener la lista de artistas favoritos del usuario logueado con Authentication Code Flow
@spotify_bp.route("/spotify/myartists", methods=['GET'])
def get_myartists():

    url = f"{SPOTIFY_API_URL}/me/top/artists"

    data = spotify_get2(url)
    return jsonify(data)

# Método para obtener la lista de canciones favoritas del usuario logueado con Authentication Code Flow
@spotify_bp.route("/spotify/mysongs", methods=['GET'])
def get_mysongs():

    url = f"{SPOTIFY_API_URL}/me/top/tracks"

    data = spotify_get2(url)
    return jsonify(data)