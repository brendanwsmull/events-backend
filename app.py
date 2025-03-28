import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import requests
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

            query = "SELECT UUID, userName, accountType, isPrivate FROM users WHERE userName = %s AND password = %s"
            cursor.execute(query, (username, password))
            user = cursor.fetchone()

            if user:
                return jsonify({
                    "success": True, 
                    "uuid": user["UUID"], 
                    "accountType": user["accountType"], 
                    "username": user["userName"],
                    "isPrivate": user["isPrivate"]
                }), 200
            else:
                return jsonify({"success": False, "error": "Invalid username or password"}), 400

        except Exception as e:
            return jsonify({"success": False, "error": "something failed while logging in"}), 500
        
        finally:
            cursor.close()
            conn.close()


    # The route for creating new accounts
    @app.route('/createAccount', methods=['POST'])
    def createAccount():
        response = request.get_json()
        
        username = response.get('username')
        password = response.get('password')
        isPrivate = response.get('isPrivate', True)
        accountType = response.get('accountType')

        try:
            conn = connect_to_db()
            cursor = conn.cursor()
            
            query = "SELECT UUID FROM users WHERE userName = %s"
            cursor.execute(query, (username))
            user = cursor.fetchone()
            
            # Create new user if name is available
            if user:
                return jsonify({"success": False, "error": "Username already taken"}), 400
            else:
                query = "INSERT INTO users (UUID, userName, password, isPrivate, accountType) VALUES (NULL, %s, %s, %s, %s)"

                cursor.execute(query, (username, password, isPrivate, accountType))
                conn.commit()

                return jsonify({"success": True, "username": username}), 201
            
        except Exception as e:
            return jsonify({"success": False, "error": "Unable to create account"}), 500
        
        finally:
            cursor.close()
            conn.close()
    
    # Route for creating sub-accounts
    @app.route('/createSubAccount', methods=['POST'])
    def createSubAccount():
        response = request.get_json()
        
        username = response.get('username')
        password = response.get('password')
        isPrivate = response.get('isPrivate', True)
        accountType = '2'
        parentAccount = response.get('hostuser')
        
        try:
            conn = connect_to_db()
            cursor = conn.cursor()
            
            query = "SELECT UUID FROM users WHERE userName = %s"
            cursor.execute(query, (username))
            user = cursor.fetchone()
            
            # Create new user if name is available
            if user:
                return jsonify({"success": False, "error": "Username already taken"}), 400
            else:
                query = "INSERT INTO users (UUID, userName, password, isPrivate, accountType, parentAccount) VALUES (NULL, %s, %s, %s, %s, %s)"
                print(parentAccount)
                cursor.execute(query, (username, password, isPrivate, accountType, parentAccount))
                conn.commit()

                return jsonify({"success": True, "username": username}), 201
            
        except Exception as e:
            print(e)
            return jsonify({"success": False, "error": "Unable to create subAccount"}), 500
        
        finally:
            cursor.close()
            conn.close()

    # Route for inviting accounts to a group
    @app.route('/inviteAccount', methods=['POST'])
    def inviteAccount():
        return

    # Route for accepting invites from a group
    @app.route('/acceptInvite', methods=['POST'])
    def acceptInvite():
        return

    # Route for joining a group
    @app.route('/joinGroup', methods=['POST'])
    def joinGroup():
        return

    # Route for updating invites
    @app.route('/updateInvites', methods=['POST'])
    def updateInvites():
        return

    @app.route('/setPrivate', methods=['PUT'])
    def setPrivate():
        data = request.json
        uuid = data.get('UUID')
        bit = data.get('isPrivate')

        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            cursor.execute('UPDATE users SET isPrivate = %s WHERE UUID = %s', (bit, uuid))

            conn.commit()
            return '', 200
        except Exception as e:
            return '', 500
        finally:
            cursor.close()
            conn.close()

    @app.route('/createEvent', methods=['POST'])
    def createEvent():
        load_dotenv()
        response = request.get_json()
        UUID = response.get('UUID')
        eventName = response.get('eventName')
        address = response.get('address')
        desc = response.get('desc')
        cap = response.get('cap')
        tags = response.get('tags')
        date = response.get('date')

        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {
            'address': address,
            'key': os.getenv("geo_coding_key")
        }
        response = requests.get(url, params=params)
        data = response.json()

        if data['status'] != 'OK':
            return jsonify({'error': 'Geocoding failed', 'details': data.get('status')}), 500

        location = data['results'][0]['geometry']['location']

        try:
            conn = connect_to_db()
            cursor = conn.cursor()
            query = "insert into events values (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(query, (UUID, eventName, date, address, location['lat'], location['lng'], desc, tags, cap))
            conn.commit()
            return jsonify({"success": True}), 200
        except Exception as e:
            print(e)
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()
    
    @app.route("/getUserEvents", methods=['GET'])
    def getUserEvents():
        UUID = request.args.get('UUID')
        try:
            conn = connect_to_db()
            cursor = conn.cursor()
            # TODO get list of events user is hosting
            hostedQ = "SELECT * FROM events WHERE eventHost = %s AND date >= NOW()"
            cursor.execute(hostedQ, (UUID,))
            hostingEvents = cursor.fetchall()
            # TODO get list of events user is signed up for
            attendingQ = """
                    SELECT e.*, u.userName AS hostName FROM events e
                    JOIN users u on e.eventHost = u.UUID WHERE UEID IN (
                    SELECT UEID FROM signedUp WHERE UUID = %s
                    )
                    AND e.eventHost != %s
                    AND e.date >= NOW()
                """
            cursor.execute(attendingQ, (UUID, UUID))
            attendingEvents = cursor.fetchall()
            return jsonify({
                "hostingEvents": hostingEvents,
                "attendingEvents": attendingEvents
            }), 200
        except Exception as e:
            print(e)
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    return app
