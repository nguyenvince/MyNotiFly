import json
import os
import urllib.request
from datetime import datetime, timedelta
from FlightRadar24 import FlightRadar24API
# from dotenv import load_dotenv
# load_dotenv()

arrival = {
    'name': 'Arrival',
    'lat': float(os.environ['ARRIVAL_LAT']),
    'long': float(os.environ['ARRIVAL_LONG']),
    'heading': int(os.environ['ARRIVAL_HEADING']),
}

departure = {
    'name': 'Departure',
    'lat': float(os.environ['DEPARTURE_LAT']),
    'long': float(os.environ['DEPARTURE_LONG']),
    'heading': int(os.environ['DEPARTURE_HEADING']),
}

noti_url = os.getenv('NOTI_URL')

radius = 5000  # meters
maxHeight = 3000  # feet
maxSpeed = 300  # knots
minSpeed = 100
heading_tolerance = 10  # degrees tolerance for runway alignment
cooldown_period = timedelta(minutes=10)  # 10 min cooldown period to determine if the last flight has already passed
state_file = 'runway_state.json'

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

# Initialize API
fr_api = FlightRadar24API()

# Check for flights that meet the criteria
flight_overhead = False

# Function to check if a flight is aligned with the runway
def is_flight_heading_to_runway(heading, runway_heading):
    return abs(heading - runway_heading) <= heading_tolerance

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
        # Convert notification content to JSON format and encode it
        params = json.dumps(notification_content['message']).encode('utf8')

        # Create the request object
        req = urllib.request.Request(noti_url, data=params,
                                     headers=notification_content['headers'])

        # Send the request and get the response
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print("Notification sent: ", notification_content['headers']['Title'])
            else:
                raise Exception(f"HTTP Error: {response.status} {response.reason}")
    
    except Exception as e:
        print(f"Failed to send notification: {e}")

if __name__ == '__main__':
    # Load the current state
    state = load_state()
    runway_active = state['runway_active']
    last_active_time = datetime.strptime(state['last_active'], '%Y-%m-%d %H:%M:%S') if state['last_active'] else None
    current_time = datetime.now()

    for runway_direction in [arrival, departure]:
        # Get bounds and fetch flights
        try:    
            bounds = fr_api.get_bounds_by_point(runway_direction["lat"], runway_direction["long"], radius)
            flights = fr_api.get_flights(bounds=bounds)
        except Exception as e:
            print(f"Failed to retrieve flight data: {e}")
            flights = []

        print(f"{runway_direction['name']}, all flights: {flights}")

        for flight in flights:
            if flight.altitude <= maxHeight and flight.ground_speed <= maxSpeed and minSpeed <= flight.ground_speed and is_flight_heading_to_runway(flight.heading, runway_direction["heading"]):
                flight_overhead = True
                print("Overhead: ", flight)
                break # one flight is enough to trigger flight_overhead flag

        # Notification logic
        if flight_overhead:
            state['last_active'] = current_time.strftime('%Y-%m-%d %H:%M:%S')

            if not runway_active:
                send_notification(Notifications['active']) # send notification if this is the first flight after the runway is marked inactive
                state['runway_active'] = True
            else:
                print("Notification not sent, runway has been ACTIVE for a long time")

            save_state(state)
            break    
        else:
            if runway_active and (last_active_time and current_time - last_active_time > cooldown_period):
                # Send notification that runway is no longer active
                send_notification(Notifications['inactive'])  # Pass the dictionary
                # Update state
                state['runway_active'] = False
                state['last_active'] = None
                save_state(state)
            else:
                print("Notification not sent, runway has been INACTIVE for a long time")

