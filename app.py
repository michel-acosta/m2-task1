# Importamos flask
from flask import Flask
# Importamos usuarios
from users import users_bp
# Importamos spotify
from spotify import spotify_bp

app = Flask(__name__)

# Registramos el blueprint de usuarios
app.register_blueprint(users_bp)

# Registramos el blueprint de spotify
app.register_blueprint(spotify_bp)

@app.route('/')
def home():
    return "Hello world!"

if __name__ == '__main__':
    app.run(debug=True)