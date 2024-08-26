from datetime import datetime, timedelta
from FlightRadar24 import FlightRadar24API
import json
import os
import requests  # Import the requests library

# Initialize API
fr_api = FlightRadar24API()

# Constants
coordinates = [52.320436486573826, 4.870884388612222]
radius = 4000  # meters
maxHeight = 1000  # feet
maxSpeed = 300  # knots
heading_threshold = 10  # degrees tolerance for runway alignment
runway_heading = [90, 270]  # Runway heading for 09 and 27
cooldown_period = timedelta(minutes=60)  # 1 hour cooldown period
state_file = 'runway_state.json'
notification_url = "https://ntfy.sh/uilenstede102_flight"  # Ensure the URL is valid

# Function to check if a flight is aligned with the runway
def is_flight_heading_to_runway(heading):
    for runway in runway_heading:
        if abs(heading - runway) <= heading_threshold:
            return True
    return False

# Function to load state
def load_state():
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    return {'last_active': None, 'runway_active': False}

# Function to save state
def save_state(state):
    with open(state_file, 'w') as f:
        json.dump(state, f)

# Function to send notification
def send_notification(message):
    try:
        response = requests.post(notification_url, data=message)
        response.raise_for_status()  # Raises an HTTPError if the response was an error
    except requests.RequestException as e:
        print(f"Failed to send notification: {e}")

# Get bounds and fetch flights
bounds = fr_api.get_bounds_by_point(coordinates[0], coordinates[1], radius)
flights = fr_api.get_flights(bounds=bounds)

# Load the current state
state = load_state()
runway_active = state['runway_active']
last_active_time = datetime.strptime(state['last_active'], '%Y-%m-%d %H:%M:%S') if state['last_active'] else None

# Check for flights that meet the criteria
relevant_flights = []
for flight in flights:
    if flight.altitude <= maxHeight and flight.ground_speed <= maxSpeed and is_flight_heading_to_runway(flight.heading):
        relevant_flights.append(flight)

# Notification logic
current_time = datetime.utcnow()

if relevant_flights:
    if not runway_active or (last_active_time and current_time - last_active_time > cooldown_period):
        # Send notification
        send_notification("A flight is heading towards the runway.")
        # Update state
        state['runway_active'] = True
        state['last_active'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
        save_state(state)
else:
    if runway_active and (last_active_time and current_time - last_active_time > timedelta(minutes=5)):
        # Send notification that runway is no longer active
        send_notification("The runway is now inactive.")
        # Update state
        state['runway_active'] = False
        state['last_active'] = None
        save_state(state)
