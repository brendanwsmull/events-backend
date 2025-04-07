import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import requests
import math
from dotenv import load_dotenv, dotenv_values

def get_distance(lat1, long1, lat2, long2):
    # this was pulled from here: https://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points 
    # converting degrees to radians
    r = 3956 # earth radius
    lat1 = math.radians(lat1)
    long1 = math.radians(long1)
    lat2 = math.radians(lat2)
    long2 = math.radians(long2)
    # get differences
    dlat = lat2 - lat1
    dlong = long2 - long1
    # Havernsine Formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlong / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    return r * c

def hashC(coord):
    return int(coord * 10)

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
        accountType = response.get('accountType')
        isPrivate = True
        
        if (accountType == "1"):
            isPrivate = False
        
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
            query = """
                INSERT INTO events VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                (SELECT isPrivate FROM users WHERE UUID = %s))
                """
            cursor.execute(query, (
                UUID, 
                eventName, 
                date, 
                address, 
                round(location['lat'], 3), 
                round(location['lng'], 3), 
                desc, 
                tags, 
                cap,
                hashC(location['lat']),
                hashC(location['lng']),
                UUID
                ))
            conn.commit()
            return jsonify({"success": True}), 200
        except Exception as e:
            print(e)
            return jsonify({"error": str(e)}), 500

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
            print("Error: ", e)
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
        uuid = request.args.get('UUID')
        
        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            query = "SELECT prefs FROM prefs WHERE UUID = %s"
            cursor.execute(query, (uuid))
            data = cursor.fetchall()

            return jsonify({"success": True, "prefs":data[0]["prefs"]}), 200

        except Exception as e:
            print(e)
            return jsonify({"success": False, "error": "Failed to get preferences"}), 500
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
    
    @app.route('/updateDistance', methods=['POST'])
    def updateDistance():
        data = request.get_json()
        uuid = data.get("UUID")
        dist = data.get("dist")

        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            query = "CALL updateDistance(%s, %s)"
            cursor.execute(query, (uuid, dist))
            return jsonify({"success": True, "dist": dist}), 200
            
        except Exception as e:
            print(e)
            return jsonify({"success": False, "error": "Failed to update preferred distance"}), 500
        finally:
            cursor.close()
            conn.close()


    @app.route('/getDistance', methods=['GET'])
    def getDistance():
        uuid = request.args.get("UUID")
        
        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            query = "SELECT dist FROM prefs WHERE UUID = %s"
            cursor.execute(query, (uuid))
            dist = cursor.fetchall()
            return jsonify({"success": True, "distance": dist[0]["dist"]}), 200
            
        except Exception as e:
            print(e)
            return jsonify({"success": False, "error": "Failed to update preferences"}), 500
        finally:
            cursor.close()
            conn.close()
    

    @app.route('/getEventFeed', methods=["GET"])
    def getEventFeed():
        UUID = request.args.get("UUID")
        long = float(request.args.get("long"))
        lat = float(request.args.get("lat"))
        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            # Get list of events from groups they are apart of
            groupQ = """
                SELECT e.*, u.userName AS hostName
                FROM events e
                JOIN users u ON e.eventHost = u.UUID
                WHERE e.eventHost IN (
                    SELECT groupID
                    FROM userGroups
                    WHERE userID = %s AND pending = FALSE
                )
                AND e.date >= NOW()
            """
            cursor.execute(groupQ, (UUID))
            groupEvents = cursor.fetchall()

            # Get list of public events within distance
            publicQ = "CALL findEvents(%s, %s, %s)"
            cursor.execute(publicQ, (UUID, hashC(lat), hashC(long)))
            publicEvents = cursor.fetchall()
            publicEvents = publicEvents
            while cursor.nextset():
                pass
            
            # Filter feed for events that share tags
            query = "SELECT prefs FROM prefs WHERE UUID = %s"
            cursor.execute(query, (UUID))
            prefs = cursor.fetchall()
            prefs = prefs[0]["prefs"].lower().split()
            print("Prefs: ", prefs)

            # Count the number of shared tags
            matching = []
            if (len(prefs) == 0):
                matching = publicEvents
            else:
                for event in publicEvents:
                    print(event["tags"])
                    event["tags"] = event["tags"].lower()
                    for p in prefs:
                        if p in event["tags"]:
                            matching.append(event)
                            break

            return jsonify({
                "groupEvents": groupEvents,
                "eventFeed": matching
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    @app.route('/deleteEvent', methods=["GET"])
    def deleteEvent():
        UEID = request.args.get("UEID")
        try:
            conn = connect_to_db()
            cursor = conn.cursor()
            deleteQSignedUp = "DELETE FROM signedUp WHERE UEID = %s"
            cursor.execute(deleteQSignedUp, (UEID,))
            deleteQEvents = "DELETE FROM events WHERE UEID = %s"
            cursor.execute (deleteQEvents, (UEID,))
            conn.commit()
            return jsonify({"status": "all good :3"}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()
    
    @app.route('/unSignUpEvent', methods=["GET"])
    def unSignUpEvent():
        UEID = request.args.get("UEID")
        UUID = request.args.get("UUID")
        try:
            conn = connect_to_db()
            cursor = conn.cursor()
            deleteQSignedUp = "DELETE FROM signedUp WHERE UUID = %s and UEID = %s"
            cursor.execute(deleteQSignedUp, (UUID, UEID))
            conn.commit()
            return jsonify({"status": "all good :3"}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    @app.route('/signUp', methods=["GET"])
    def signUp():
        UEID = request.args.get("UEID")
        UUID = request.args.get("UUID")
        cap = int(request.args.get("cap"))

        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            checkUserQ = "SELECT * FROM signedUp WHERE UUID = %s AND UEID = %s"
            cursor.execute(checkUserQ, (UUID, UEID))
            if cursor.fetchone():
                return jsonify({"error": "User already signed up for this event"}), 400

            countQ = "SELECT COUNT(*) FROM signedUp WHERE UEID = %s"
            cursor.execute(countQ, (UEID,))
            count = cursor.fetchone()[0]
            if cap > 0 and count >= cap:
                return jsonify({"error": "Event is at full capacity"}), 400

            insertQ = "INSERT INTO signedUp (UUID, UEID) VALUES (%s, %s)"
            cursor.execute(insertQ, (UUID, UEID))
            conn.commit()

            return jsonify({"status": "success"}), 200

        except Exception as e:
            print("Error when signing up:", e)
            return jsonify({'error': str(e)}), 500

        finally:
            cursor.close()
            conn.close()

    return app
