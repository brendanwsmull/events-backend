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
                query = "CALL createAccount(%s, %s, %s, %s)"

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
        response = request.get_json()

        userBeingInvited = response.get('invitedUser')
        groupDoingInviting = response.get('UUID')

        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            # Get Username
            query = "SELECT UUID FROM users WHERE userName = %s"
            cursor.execute(query, (userBeingInvited))
            user = cursor.fetchone()['UUID']
        
            if not user:
                return jsonify({"success": False, "error": "User does not exist"}), 400

            # Create new entry in groups table with pending set to TRUE
            query = "INSERT INTO userGroups (groupID, userID, pending) VALUES (%s, %s, TRUE)"
            cursor.execute(query, (groupDoingInviting, user))
            
            conn.commit()
            return jsonify({"success": True, "message": "Invited user"}), 200


        except Exception as e:
            print(e)
            return jsonify({"success": False, "error": "Unable to send invite"}), 500
        
        finally:
            cursor.close()
            conn.close()


    # Route for accepting or rejecting invites from a group
    @app.route('/inviteResponse', methods=['POST'])
    def inviteResponse():
        response = request.get_json()

        user = response.get('UUID')
        groupName = response.get('group')
        accept = response.get('accept') 

        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            # Get UUID from userName
            query = "SELECT UUID FROM users WHERE userName = %s"
            cursor.execute(query, groupName)
            group = cursor.fetchone()["UUID"]
            
            if accept:
                query = "UPDATE userGroups SET pending = FALSE WHERE userID = %s AND groupID = %s"
                cursor.execute(query, (user, group))
                conn.commit()
                
                return jsonify({"success": True, "message": "Successfully accepted invite"}), 200
            
            else:
                query = "DELETE FROM userGroups WHERE userID = %s AND groupID = %s"
                cursor.execute(query, (user, group))
                conn.commit()
                
                return jsonify({"success": True, "message": "Successfully rejected invite"}), 200

        except Exception as e:
            print(e)
            return jsonify({"success": False, "error": "Something went wrong trying to accept/deny invite"}), 500

        finally:
            cursor.close()
            conn.close()


    # Route for joining a group
    @app.route('/sendJoinRequest', methods=['POST'])
    def sendJoinRequest():
        response = request.get_json()

        userID = response.get("UUID")
        groupToJoin = response.get("joining")

        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            # Get group info and check if it exists
            query = "SELECT isPrivate, UUID FROM users WHERE userName = %s AND accountType != 1"
            cursor.execute(query, groupToJoin)
            groupInfo = cursor.fetchone()
            if groupInfo is None:
                return jsonify({"success": False, "error": "Entered account name does not exits"}), 400
            
            # Check if account is private
            isPrivate = groupInfo["isPrivate"]
            if isPrivate:
                return jsonify({"success": False, "error": str(groupToJoin) + " is not a public group" }), 403
            
            query = "CALL addUserToGroup(%s, %s)"
            cursor.execute(query, (userID, groupInfo["UUID"]))
            print("UserID: %s\nGroupID: ",(userID, groupInfo["UUID"]))
            conn.commit()
            return jsonify({"success": True}), 200
        
        except Exception as e:
            print(e)
            return jsonify({"success": False, "error": "Something went wrong trying to join a group"}), 500

        finally:
            cursor.close()
            conn.close()

    # Route for updating invites
    @app.route('/getInvitedList', methods=['GET'])
    def getInvitedList():
        user = request.args.get('UUID')

        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            query = "SELECT userName FROM users WHERE UUID IN (SELECT groupID FROM userGroups WHERE userID = %s AND pending = TRUE)"
            groupNames = cursor.execute(query, (user))
            groupNames = cursor.fetchall()
            groupNames = [x["userName"] for x in groupNames]
            
            return jsonify({"success": True, "groups": groupNames}), 200

        except Exception as e:
            print(e)
            return jsonify({"success": False, "error": "Something went wrong trying to get the invite list"}), 500

        finally:
            cursor.close()
            conn.close()
        

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

    @app.route('/getCurrentGroups', methods=['GET'])
    def getCurrentGroups():
        uuid = request.args.get('UUID')

        if not uuid:
            return jsonify({"success": False, "error": "Missing UUID"}), 400

        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            query = """
                SELECT userName
                FROM users
                WHERE UUID IN (
                    SELECT groupID
                    FROM userGroups
                    WHERE userID = %s AND pending = FALSE
                )
            """
            cursor.execute(query, (uuid,))
            rows = cursor.fetchall()

            group_string = ""
            for row in rows:
                group_string += row["userName"] + ", "
            if group_string.endswith(", "):
                group_string = group_string[:-2]

            return jsonify({"success": True, "groups": group_string}), 200

        except Exception as e:
            print("Error:", e)
            return jsonify({"success": False, "error": "Failed to get groups"}), 500

        finally:
            cursor.close()
            conn.close()
    
    @app.route('/updatePreferences', methods=['POST'])
    def updatePreferences():
        data = request.get_json()
        uuid = data.get("UUID")
        prefs = data.get("pref")
        
        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            query = "CALL updatePreferences(%s, %s)"
            cursor.execute(query, (uuid, prefs))

            return jsonify({"success": True, "prefs": prefs}), 200

        except Exception as e:
            print(e)
            return jsonify({"success": False, "error": "Failed to update preferences"}), 500
        finally:
            cursor.close()
            conn.close()


    @app.route('/getPrefs', methods=['GET'])
    def getPrefs():
        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            
        except Exception as e:
            print(e)
            return jsonify({"success": False, "error": "Failed to get preferences"}), 500
        finally:
            cursor.close()
            conn.close()
    
    
    @app.route('/updateDistance', methods=['POST'])
    def updateDistance():
        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            
        except Exception as e:
            print(e)
            return jsonify({"success": False, "error": "Failed to update preferred distance"}), 500
        finally:
            cursor.close()
            conn.close()


    @app.route('/getDistance', methods=['GET'])
    def getDistance():
        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            
        except Exception as e:
            print(e)
            return jsonify({"success": False, "error": "Failed to update preferences"}), 500
        finally:
            cursor.close()
            conn.close()

    return app
