# Importamos los módulos necesarios de flask
from flask import Blueprint, request, jsonify
# Importamos el módulo de conexión a base de datos
from db import get_connection

# Guardamos el blueprint para poder usarlo desde otros ficheros
users_bp = Blueprint('users', __name__)

# Método GET para listar todos los usuarios (si no recibe un id en la URL) o un usuario concreto si recibe su id
@users_bp.route('/users', defaults={'user_id': None}, methods=['GET'])
@users_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Aquí ejecutamos un select u otro dependiendo de si recibimos el id o no
        if user_id is None:
            sql = "SELECT id, name FROM m2t1_users"
            cursor.execute(sql)
        else:
            sql = "SELECT id, name FROM m2t1_users WHERE id = %s"
            cursor.execute(sql, (user_id,))

        # En cualquiera de los dos casos acabamos llamando al fetch all para llenar la lista de resultados
        results = cursor.fetchall()

        # Si no hay resultados se muestra un 404 (en el caso de estar buscando un id concreto) 
        # o un 200 si estamos listando la lista completa y está vacía
        if not results:
            return jsonify({"message": "User not found", "users": []}), 404 if user_id else 200

        # Si hay resultados, los mostramos junto con un http 200
        return jsonify({
            "message": "Users retrieved successfully",
            "users": results
        }), 200

    except Exception as e:
        print(e)
        # En caso de excepción, devolvemos un http 500
        return jsonify({"message": "Error retrieving users"}), 500

    finally:
        # Finalmente cerramos los objetos de base de datos
        cursor.close()
        conn.close()

# Método POST para insertar usuarios en la tabla de usuarios
# Recibe N usuarios con este formato: { "users": [{ "name": "Míchel" }, {"name": "Fernando"}]}
# El id del usuario creado está definido como autonumérico en la tabla de la BD
@users_bp.route('/users', methods=['POST'])
def post_user():
    body = request.get_json()
    new_users = body.get('users', [])

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Validación del json de usuarios
        for user in new_users:
            if 'name' not in user:
                return jsonify({
                    "message": "Each user must have 'name' field"
                }), 400
            # Comprobamos si el usuario con ese nombre ya existe
            cursor.execute("SELECT id FROM m2t1_users WHERE name = %s", (user["name"],))
            existing = cursor.fetchone()

            if existing:
                return jsonify({"message": f"User {user["name"]} already exists"}), 409 # 409 = estado HTTP para conflicto de datos

        # Para cada usuario recibido, ejecutamos el insert
        sql = "INSERT INTO m2t1_users (name) VALUES (%s)"
        for user in new_users:
            cursor.execute(sql, (user['name'],))

        # Commiteamos al finalizar
        conn.commit()

        # Devolvemos un http 201 junto con la lista de usuarios insertados
        return jsonify({
            "message": "User(s) added successfully",
            "users_names": [u['name'] for u in new_users]
        }), 201

    except Exception as e:
        print(e)
        # En caso de excepción, devolvemos un http 500
        return jsonify({"message": "Error inserting user"}), 500

    finally:
        # Finalmente cerramos los objetos de base de datos
        cursor.close()
        conn.close()

# Método PUT para modificar un usuario
# Recibe por ejemplo { "name":"Pepito" }
# El id del usuario va en la URL
@users_bp.route('/users/<int:user_id>', methods=['PUT'])
def put_user(user_id):
    body = request.get_json()
    new_users = body.get('users', [])

    # Validación: debe venir el campo "name"
    if not body or "name" not in body:
        return jsonify({
            "message": "The request body must contain a 'name' field"
        }), 400

    new_name = body["name"]

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Comprobamos si el usuario existe
        cursor.execute("SELECT id FROM m2t1_users WHERE id = %s", (user_id,))
        existing = cursor.fetchone()

        if not existing:
            return jsonify({"message": "User not found"}), 404

        # Comprobamos si el usuario con ese nombre ya existe
        cursor.execute("SELECT id FROM m2t1_users WHERE name = %s", (new_name,))
        existing = cursor.fetchone()

        if existing:
            return jsonify({"message": f"User {new_name} already exists"}), 409 # 409 = estado HTTP para conflicto de datos        

        # Ejecutamos el update
        sql = "UPDATE m2t1_users SET name = %s WHERE id = %s"
        cursor.execute(sql, (new_name, user_id))

        # Commiteamos al finalizar
        conn.commit()

        cursor = conn.cursor(dictionary=True)
        sql = "SELECT id, name FROM m2t1_users WHERE id = %s"
        cursor.execute(sql, (user_id,))
        updated_user = cursor.fetchone()

        # Devolvemos un http 200 junto con el usuario modificado
        return jsonify({
            "message": "User updated successfully",
            "user": updated_user
        }), 200

    except Exception as e:
        print(e)
        # En caso de excepción, devolvemos un http 500
        return jsonify({"message": "Error updating user"}), 500

    finally:
        # Finalmente cerramos los objetos de base de datos
        cursor.close()
        conn.close()    

# Método DELETE para eliminar un usuario por su id
@users_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Comprobamos si el usuario existe
        cursor.execute("SELECT id FROM m2t1_users WHERE id = %s", (user_id,))
        existing = cursor.fetchone()

        if not existing:
            return jsonify({"message": "User not found"}), 404

        # Ejecutamos el delete
        sql = "DELETE FROM m2t1_users WHERE id = %s"
        cursor.execute(sql, (user_id,))

        # Commiteamos al finalizar
        conn.commit()

        # Devolvemos un http 200 si todo ha ido bien
        return jsonify({
            "message": "User deleted successfully",
        }), 200

    except Exception as e:
        print(e)
        # En caso de excepción, devolvemos un http 500
        return jsonify({"message": "Error deleting user"}), 500

    finally:
        # Finalmente cerramos los objetos de base de datos
        cursor.close()
        conn.close()

# Método GET para listar los artistas de un usuario
@users_bp.route('/users/<int:user_id>/artists', methods=['GET'])
def get_artists(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Comprobamos si el usuario existe
        cursor.execute("SELECT id FROM m2t1_users WHERE id = %s", (user_id,))
        existing = cursor.fetchone()

        if not existing:
            return jsonify({"message": "User not found"}), 404

        cursor = conn.cursor(dictionary=True)
        sql = "SELECT id, name FROM m2t1_users_artists WHERE id_user = %s"
        cursor.execute(sql, (user_id,))
        updated_artists = cursor.fetchall()

        # Devolvemos un http 200 junto con la lista de artistas del usuario
        return jsonify({
            "artists": updated_artists
        }), 200

    except Exception as e:
        print(e)
        # En caso de excepción, devolvemos un http 500
        return jsonify({"message": "Error reading artists"}), 500

    finally:
        # Finalmente cerramos los objetos de base de datos
        cursor.close()
        conn.close()  

# Método POST para insertar un artista para un usuario
# Recibe un artista con este formato: { "name": "Jamiroquai" }
# El id del artista creado está definido como autonumérico en la tabla de la BD
# El id del usuario va en la URL
@users_bp.route('/users/<int:user_id>/artists', methods=['POST'])
def post_artist(user_id):
    body = request.get_json()
    new_artist = body.get('name', [])

    # Validación: debe venir el campo "name"
    if not body or "name" not in body:
        return jsonify({
            "message": "The request body must contain a 'name' field"
        }), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Comprobamos si el usuario existe
        cursor.execute("SELECT id FROM m2t1_users WHERE id = %s", (user_id,))
        existing = cursor.fetchone()

        if not existing:
            return jsonify({"message": "User not found"}), 404

        # Comprobamos si el artista existe
        cursor.execute("SELECT id FROM m2t1_users_artists WHERE id_user = %s and name = %s", (user_id, new_artist))
        existing = cursor.fetchone()

        if existing:
            return jsonify({"message": "Artist already exists"}), 409 # 409 = estado HTTP para conflicto de datos

        # Ejecutamos el insert
        sql = "INSERT INTO m2t1_users_artists (id_user, name) VALUES (%s, %s)"
        cursor.execute(sql, (user_id, new_artist))

        # Commiteamos al finalizar
        conn.commit()

        cursor = conn.cursor(dictionary=True)
        sql = "SELECT id, name FROM m2t1_users_artists WHERE id_user = %s"
        cursor.execute(sql, (user_id,))
        updated_artists = cursor.fetchall()

        # Devolvemos un http 200 junto con la lista de artistas del usuario
        return jsonify({
            "message": "Artist added successfully",
            "artists": updated_artists
        }), 200

    except Exception as e:
        print(e)
        # En caso de excepción, devolvemos un http 500
        return jsonify({"message": "Error inserting artist"}), 500

    finally:
        # Finalmente cerramos los objetos de base de datos
        cursor.close()
        conn.close()   

# Método DELETE para eliminar un artista de un usuario por su id
# En la URL van el id de usuario y el id de artista
@users_bp.route('/users/<int:user_id>/artists/<int:artist_id>', methods=['DELETE'])
def delete_artist(user_id, artist_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Comprobamos si el usuario existe
        cursor.execute("SELECT id FROM m2t1_users WHERE id = %s", (user_id,))
        existing = cursor.fetchone()

        if not existing:
            return jsonify({"message": "User not found"}), 404

        # Comprobamos si el artista existe
        cursor.execute("SELECT id FROM m2t1_users_artists WHERE id_user = %s and id = %s", (user_id, artist_id))
        existing = cursor.fetchone()

        if not existing:
            return jsonify({"message": "Artist not found"}), 404

        # Ejecutamos el delete
        sql = "DELETE FROM m2t1_users_artists WHERE id = %s"
        cursor.execute(sql, (artist_id,))

        # Commiteamos al finalizar
        conn.commit()

        # Devolvemos un http 200 si todo ha ido bien, junto con la lista de artistas modificada
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT id, name FROM m2t1_users_artists WHERE id_user = %s"
        cursor.execute(sql, (user_id,))
        updated_artists = cursor.fetchall()

        # Devolvemos un http 200 junto con la lista de artistas del usuario
        return jsonify({
            "message": "Artist deleted successfully",
            "artists": updated_artists
        }), 200

    except Exception as e:
        print(e)
        # En caso de excepción, devolvemos un http 500
        return jsonify({"message": "Error deleting artist"}), 500

    finally:
        # Finalmente cerramos los objetos de base de datos
        cursor.close()
        conn.close()