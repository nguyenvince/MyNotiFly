import json
import os
import urllib.request
from datetime import datetime, timedelta
from FlightRadar24 import FlightRadar24API

env_file = os.getenv('GITHUB_ENV')
print(env_file)

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

noti_url = os.environ['NOTI_URL']

radius = 5000  # meters
maxHeight = 3000  # feet
maxSpeed = 300  # knots
minSpeed = 100
heading_tolerance = 10  # degrees tolerance for runway alignment
cooldown_period = timedelta(minutes=10)  # 10 min cooldown period to determine if the last flight has already passed

THRESHOLD_CONSECUTIVE_FLIGHTS = 3

Notifications = {
    "active": {
        "headers": {
            "Title": "ACTIVE RUNWAY",
            "Priority": "high",
            "Tags": "flight_departure,skull",
            'Actions': 'view, Flight Tracker, https://flightradar24.com, clear=true'
        },
        "message": "Put on ANC"
    },
    "inactive": {
        "headers": {
            "Title": "Inactive Runway",
            "Priority": "high",
            "Tags": "white_check_mark,shushing_face"
        },
        "message": "Enjoy your peace"
    }
}


# Function to check if a flight is aligned with the runway
def is_flight_heading_to_runway(heading, runway_heading):
    return abs(heading - runway_heading) <= heading_tolerance

# Function to load state from environment variables
def load_state():
    last_active = os.getenv('LAST_ACTIVE')
    consecutive_flights = int(os.getenv('CONSECUTIVE_FLIGHTS', 0))

    state = {
        'last_active': last_active,
        'consecutive_flights': consecutive_flights
    }
    print(state)

    return state

# Function to save state to environment variables
def save_state(state):
    with open(env_file, "a") as env_file:
        env_file.write(f"LAST_ACTIVE={state['last_active'] if state['last_active'] else ""}")
        env_file.write(f"\n")
        env_file.write(f"CONSECUTIVE_FLIGHTS={state['consecutive_flights']}")

# Function to send notification
def send_notification(notification_content):
    try:
        # Convert notification content to JSON format and encode it
        params = json.dumps(notification_content['message']).encode('utf8')

        # Create the request object
        req = urllib.request.Request(
            noti_url, 
            data=params,
            headers=notification_content['headers']
        )

        # Send the request and get the response
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print("Notification sent: ", notification_content['headers']['Title'])
            else:
                raise Exception(f"HTTP Error: {response.status} {response.reason}")
    
    except Exception as e:
        print(f"Failed to send notification: {e}")

# Initialize API
fr_api = FlightRadar24API()

# Check for flights that meet the criteria
flight_overhead = False

if __name__ == '__main__':
    # Load the current state
    state = load_state()
    last_active_time = datetime.strptime(state['last_active'], '%Y-%m-%d %H:%M:%S') if state['last_active'] else None
    current_time = datetime.now()
    consecutive_flights = state.get('consecutive_flights', 0)
    
    # Flag to stop further processing once a notification is sent
    notification_sent = False

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
            if (flight.altitude <= maxHeight and 
                flight.ground_speed <= maxSpeed and 
                minSpeed <= flight.ground_speed and 
                is_flight_heading_to_runway(flight.heading, runway_direction["heading"])):
                
                flight_overhead = True
                print("Overhead: ", flight)
                break  # one flight is enough to trigger flight_overhead flag

        # Notification logic
        if flight_overhead:
            state['last_active'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
            consecutive_flights += 1
            state['consecutive_flights'] = consecutive_flights

            if not last_active_time:
                # Send active notification for the first flight after inactivity
                send_notification(Notifications['active'])  
                notification_sent = True  # Set flag to indicate a notification was sent
            else:
                print(f"Notification not sent, runway has been ACTIVE for a long time. Consecutive count: {consecutive_flights}")

            save_state(state)
            break  # Stop checking after sending a notification
        else:
            if last_active_time and current_time - last_active_time > cooldown_period:
                if consecutive_flights >= THRESHOLD_CONSECUTIVE_FLIGHTS:
                    # Send inactive notification if enough flights have passed with no new ones detected
                    send_notification(Notifications['inactive'])  
                    notification_sent = True  # Set flag to indicate a notification was sent
                    
                else:
                    print(f"Fewer than {THRESHOLD_CONSECUTIVE_FLIGHTS} consecutive flights. No inactive notification sent.")
                
                # Reset state after inactivity
                state['last_active'] = None
                state['consecutive_flights'] = 0
                save_state(state)

                break  # Stop checking 
            else:
                print("No recent flights, runway remains inactive.")

        # Stop the loop if a notification was sent
        if notification_sent:
            break