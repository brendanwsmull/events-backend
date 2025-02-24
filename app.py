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

            if user:
                return jsonify({"success": True, "uuid": user["UUID"], "accountType": user["accountType"]}), 200
            else:
                return jsonify({"success": False, "error": "Invalid username or password"}), 400

        except Exception as e:
            return jsonify({"success": False, "error": "something failed"}), 500
        
        finally:
            cursor.close()
            conn.close()


    # The route for creating new accounts
    @app.route('/createAccount', methods=['POST'])
    def createAccount():
        response = request.get_json()
        
        username = response['username']
        password = response['password']
        isPrivate = response['isPrivate']
        accountType = response['accountType']
        
        try:
            conn = connect_to_db
            cursor = conn.cursor()
            
            query = "SELECT UUID, FROM users WHERE userName = %s"
            cursor.execute(query, (username))
            user = cursor.fetchone()
            
            # Create new user if name is available
            if user:
                return jsonify({"success": False, "error": "Username already taken"}), 400
            else:
                query = ("INSERT INTO users (UUID, userName, password, isPrivate, accountType) " +
                         "VALUES (null, %s, %s, %b, %d)")
                cursor.execute(query, (username, password, isPrivate, accountType))

                return jsonify({"success": True, "username": username}), 201
            
        except Exception as e:
            return jsonify({"success": False, "error": "Unable to create account"}), 500
        
        finally:
            cursor.close()
            conn.close()

    return app
