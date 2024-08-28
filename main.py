import json
import os
import requests
from datetime import datetime, timedelta
from FlightRadar24 import FlightRadar24API

# Constants
arrival = {
    "lat": 52.32259984929215,
    "long": 4.948247872062269,
    "heading": 270
}
departure = {
    "lat": 52.318395577749435,
    "long": 4.796553441787003,
    "heading": 90
}

radius = 5000  # meters
maxHeight = 3000  # feet
arrival = {
    "lat": 52.32259984929215,
    "long": 4.948247872062269,
    "heading": 270
}
departure = {
    "lat": 52.318395577749435,
    "long": 4.796553441787003,
    "heading": 90
}

radius = 5000  # meters
maxHeight = 3000  # feet
maxSpeed = 300  # knots
minSpeed = 100
heading_threshold = 10  # degrees tolerance for runway alignment
cooldown_period = timedelta(minutes=10)  # 10 min cooldown period to determine if the last flight has already passed
state_file = 'runway_state.json'
notification_url = "https://ntfy.sh/uilenstede102_flight"  # Ensure the URL is valid

Notifications = {
    "active": {
        "headers": {
            "Title": "ACTIVE RUNWAY",
            "Priority": "urgent",
            "Tags": "flight_departure,skull",
            'Actions': 'view, Flight Tracker, https://flightradar24.com, clear=true'
        },
        "message": "Put on ANC"
    },
    "inactive": {
        "headers": {
            "Title": "Inactive Runway",
            "Priority": "urgent",
            "Tags": "white_check_mark,shushing_face"
        },
        "message": "Enjoy your peace"
    }
}

# Function to check if a flight is aligned with the runway
def is_flight_heading_to_runway(heading, runway_heading):
    return abs(heading - runway_heading) <= heading_threshold

# Function to load state
def load_state():
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    else:
        # Create a default state if the file doesn't exist
        return {'last_active': None, 'runway_active': False}

# Function to save state
def save_state(state):
    with open(state_file, 'w') as f:
        json.dump(state, f)

# Function to send notification
def send_notification(notification_content):
    try:
        response = requests.post(notification_url, data=notification_content['message'], headers=notification_content['headers'])
        print(notification_content['headers']['Title'])
        response.raise_for_status()  # Raises an HTTPError if the response was an error
    except requests.RequestException as e:
        print(f"Failed to send notification: {e}")

# Function to handle flight checks for either arrival or departure
def check_flights_and_send_noti_if_exist(runway_direction):
    # Initialize API
    fr_api = FlightRadar24API()
    
    # Get bounds and fetch flights
    try:    
        bounds = fr_api.get_bounds_by_point(runway_direction["lat"], runway_direction["long"], radius)
        flights = fr_api.get_flights(bounds=bounds)
    except Exception as e:
        print(f"Failed to retrieve flight data: {e}")
        flights = []

    # Load the current state
    state = load_state()
    runway_active = state['runway_active']
    last_active_time = datetime.strptime(state['last_active'], '%Y-%m-%d %H:%M:%S') if state['last_active'] else None
    # Load the current state
    state = load_state()
    runway_active = state['runway_active']
    last_active_time = datetime.strptime(state['last_active'], '%Y-%m-%d %H:%M:%S') if state['last_active'] else None

    # Check for flights that meet the criteria
    flight_overhead = False
    print("All flights: ", flights)
    for flight in flights:
        if flight.altitude <= maxHeight and flight.ground_speed <= maxSpeed and minSpeed <= flight.ground_speed and is_flight_heading_to_runway(flight.heading, runway_direction["heading"]):
            flight_overhead = True
            print("Overhead flight: ", flight)
            break

    # Notification logic
    current_time = datetime.utcnow()

    if flight_overhead:
        # Update last_active time
        state['last_active'] = current_time.strftime('%Y-%m-%d %H:%M:%S')

        if not runway_active:
            send_notification(Notifications['active'])  # Pass the dictionary
            state['runway_active'] = True
            save_state(state)
            return True  # Return True if a notification was sent
        else:
            save_state(state)
            return False  # Return False if a notification was not sent
        
    else:
        if runway_active and (last_active_time and current_time - last_active_time > cooldown_period):
            # Send notification that runway is no longer active
            send_notification(Notifications['inactive'])  # Pass the dictionary
            # Update state
            state['runway_active'] = False
            state['last_active'] = None
            save_state(state)
            return True  # Return True if a notification was sent
        else:
            return False  # Return False if a notification was not sent

if __name__ == '__main__':
    # Check arrival flights first
    if check_flights_and_send_noti_if_exist(arrival):
        print("Notification sent for arrival")
    else:
        # If no arrival notification was sent, check departure flights
        if check_flights_and_send_noti_if_exist(departure):
            print("Notification sent for departure")
        else:
            print("No flight")
