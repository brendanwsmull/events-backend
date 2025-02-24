import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
from dotenv import load_dotenv, dotenv_values

def connect_to_db():
    # the pymysql connector
    load_dotenv()
    return pymysql.connect(
        host=os.getenv("db_host"),
        user=os.getenv("db_user"),
        password=os.getenv("db_password"),
        database=os.getenv("db_name"),
        cursorclass=pymysql.cursors.DictCursor
    )

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    # the login route for testing login details
    @app.route('/login', methods=['GET'])
    def login():
        username = request.args.get('username')
        password = request.args.get('password')

        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            query = "SELECT UUID, accountType FROM users WHERE userName = %s AND password = %s"
            cursor.execute(query, (username, password))
            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user:
                return jsonify({"success": True, "uuid": user["UUID"], "accountType": user["accountType"]}), 200
            else:
                return jsonify({"success": False, "error": "Invalid username or password"}), 400

        except Exception as e:
            return jsonify({"success": False, "error": "something failed"}), 500

    return app
