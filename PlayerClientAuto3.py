from collections import deque
import os
import json
import random
from dotenv import load_dotenv
import paho.mqtt.client as paho
from paho import mqtt
import time
from threading import Thread
from queue import Queue
import heapq

# Define constants for moves
MOVES = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1)
}

fake_coin_positions = [(0, 0), (0, 9), (9, 0), (9, 9)]

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


# Calculate Manhattan distance between two points
def manhattan_distance(pos1, pos2):
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

def bfs(grid, start, goal):
    visited = set()
    queue = deque([(start, [])])

    while queue:
        current, path = queue.popleft()
        if current == goal:
            return path
        visited.add(current)
        for move, (dx, dy) in MOVES.items():
            next_pos = (current[0] + dx, current[1] + dy)
            if next_pos in grid and grid[next_pos] != 'W' and next_pos not in visited:
                queue.append((next_pos, path + [move]))
                visited.add(next_pos)
    return []

def on_message(client, userdata, msg):
    global fake_coin_positions  # Declare the global variable inside the function

    if msg.topic.endswith("/game_state"):  # Check if the topic ends with "/game_state"
        game_state = json.loads(msg.payload)  # Parse the JSON payload

        print(game_state)

        # Extract relevant data from the game state
        current_position = tuple(game_state["currentPosition"])
        coin_positions = [tuple(coin) for coin in game_state["coin1"] + game_state["coin2"] + game_state["coin3"]]
        wall_positions = [tuple(wall) for wall in game_state["walls"]]

        # Create a grid to represent the game board
        grid = {(x, y): '.' for x in range(10) for y in range(10)}
        for wall in wall_positions:
            grid[wall] = 'W'

        if coin_positions:  # If there are real coins available
            nearest_coin = min(coin_positions, key=lambda coin: manhattan_distance(current_position, coin))
            path_to_nearest_coin = bfs(grid, current_position, nearest_coin)

            # Determine next move based on the path
            if path_to_nearest_coin:
                next_move = path_to_nearest_coin[0]
            else:
                # If no path to the nearest real coin, move randomly
                next_move = random.choice(list(MOVES.keys()))
        else:
            if fake_coin_positions:  # If there are fake coins available
                print(fake_coin_positions)
                nearest_fake_coin = min(fake_coin_positions, key=lambda coin: manhattan_distance(current_position, coin))
                path_to_nearest_fake_coin = bfs(grid, current_position, nearest_fake_coin)

                if manhattan_distance(current_position, nearest_fake_coin) <= 2:
                        fake_coin_positions.remove(nearest_fake_coin)

                # Determine next move based on the path
                if path_to_nearest_fake_coin:
                    next_move = path_to_nearest_fake_coin[0]
                    # If the next move hits a fake coin, remove it from the list
                    if current_position == nearest_fake_coin:
                        fake_coin_positions.remove(nearest_fake_coin)
                else:
                    # If no path to the nearest fake coin, move randomly
                    next_move = random.choice(list(MOVES.keys()))
            else:
                # If no fake coins available, move randomly
                next_move = random.choice(list(MOVES.keys()))

        # Publish the next move
        client.publish(f"games/{lobby_name}/{player_name}/move", next_move)



if __name__ == '__main__':
    load_dotenv(dotenv_path='./credentials.env')
    
    broker_address = os.environ.get('BROKER_ADDRESS')
    broker_port = int(os.environ.get('BROKER_PORT'))
    username = os.environ.get('USER_NAME')
    password = os.environ.get('PASSWORD')

    client = paho.Client(callback_api_version=paho.CallbackAPIVersion.VERSION1, client_id="Player3", userdata=None, protocol=paho.MQTTv5)
    
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
    player_name = "Player3"

    client.subscribe(f"games/{lobby_name}/lobby")
    client.subscribe(f'games/{lobby_name}/{player_name}/game_state')
    client.subscribe(f'games/{lobby_name}/scores')

    client.publish("new_game", json.dumps({'lobby_name':lobby_name, 'team_name':'BTeam', 'player_name' : player_name}))

    time.sleep(1) # Wait a second to resolve game start

    #client.publish(f"games/{lobby_name}/start", "START")

    client.loop_forever()
