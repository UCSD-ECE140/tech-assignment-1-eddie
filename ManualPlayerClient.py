import os
import json
from dotenv import load_dotenv
import paho.mqtt.client as paho
from paho import mqtt
import time
import sys
from threading import Thread

# setting callbacks for different events to see if it works, print the message etc.
def on_connect(client, userdata, flags, rc, properties=None):
    """
        Prints the result of the connection with a reasoncode to stdout ( used as callback for connect )
        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param flags: these are response flags sent by the broker
        :param rc: stands for reasonCode, which is a code for the connection result
        :param properties: can be used in MQTTv5, but is optional
    """
    print("CONNACK received with code %s." % rc)

# with this callback you can see if your publish was successful
def on_publish(client, userdata, mid, properties=None):
    """
        Prints mid to stdout to reassure a successful publish ( used as callback for publish )
        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param mid: variable returned from the corresponding publish() call, to allow outgoing messages to be tracked
        :param properties: can be used in MQTTv5, but is optional
    """
    print("mid: " + str(mid))

# print which topic was subscribed to
def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    """
        Prints a reassurance for successfully subscribing
        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param mid: variable returned from the corresponding publish() call, to allow outgoing messages to be tracked
        :param granted_qos: this is the qos that you declare when subscribing, use the same one for publishing
        :param properties: can be used in MQTTv5, but is optional
    """
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_message(client, userdata, msg):
    if msg.topic.endswith("/game_state"):  # Check if the topic ends with "/game_state"
        game_state = json.loads(msg.payload)  # Parse the JSON payload

        print(game_state)

        # Extract relevant data from the game state
        current_position = game_state["currentPosition"]
        teammate_positions = game_state["teammatePositions"]
        enemy_positions = game_state["enemyPositions"]
        coin_positions = game_state["coin1"] + game_state["coin2"] + game_state["coin3"]
        wall_positions = game_state["walls"]

        # Create a 2D grid to represent the game board
        grid = [['.' for _ in range(10)] for _ in range(10)]

        # Add player, teammates, enemies, coins, and walls to the grid
        grid[current_position[0]][current_position[1]] = 'P'  # Player
        for teammate_position in teammate_positions:
            grid[teammate_position[0]][teammate_position[1]] = 'T'  # Teammate
        for enemy_position in enemy_positions:
            grid[enemy_position[0]][enemy_position[1]] = 'E'  # Enemy
        for coin_position in coin_positions:
            grid[coin_position[0]][coin_position[1]] = 'C'  # Coin
        for wall_position in wall_positions:
            grid[wall_position[0]][wall_position[1]] = 'W'  # Wall

        # Print the game board
        print("Game state:")
        for row in grid:
            print(' '.join(row))

# Function for reading user input and publishing moves
def input_thread(client, lobby_name, player_name):
    while True:
        move = input("Enter move (UP/DOWN/LEFT/RIGHT): ").upper()
        if move in ["UP", "DOWN", "LEFT", "RIGHT"]:
            client.publish(f"games/{lobby_name}/{player_name}/move", move)
        else:
            print("Invalid move! Please enter UP/DOWN/LEFT/RIGHT.")

if __name__ == '__main__':
    load_dotenv(dotenv_path='./credentials.env')
    
    broker_address = os.environ.get('BROKER_ADDRESS')
    broker_port = int(os.environ.get('BROKER_PORT'))
    username = os.environ.get('USER_NAME')
    password = os.environ.get('PASSWORD')

    client = paho.Client(callback_api_version=paho.CallbackAPIVersion.VERSION1, client_id="Player1", userdata=None, protocol=paho.MQTTv5)
    
    # enable TLS for secure connection
    client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    # set username and password
    client.username_pw_set(username, password)
    # connect to HiveMQ Cloud on port 8883 (default for MQTT)
    client.connect(broker_address, broker_port)

    # setting callbacks, use separate functions like above for better visibility
    client.on_subscribe = on_subscribe # Can comment out to not print when subscribing to new topics
    client.on_message = on_message
    client.on_publish = on_publish # Can comment out to not print when publishing to topics

    lobby_name = "TestLobby"
    player_name = "Player1"

    client.subscribe(f"games/{lobby_name}/lobby")
    client.subscribe(f'games/{lobby_name}/{player_name}/game_state')
    client.subscribe(f'games/{lobby_name}/scores')

    client.publish("new_game", json.dumps({'lobby_name':lobby_name, 'team_name':'ATeam', 'player_name' : player_name}))

    time.sleep(1) # Wait a second to resolve game start
    client.publish(f"games/{lobby_name}/start", "START")

    # Start a thread to read user input for moves
    input_thread = Thread(target=input_thread, args=(client, lobby_name, player_name))
    input_thread.start()

    client.loop_forever()
