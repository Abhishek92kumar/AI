import streamlit as st
from ics import Calendar
from datetime import datetime, timedelta
import pandas as pd
import requests

def fetch_ics_from_url(ics_url):
    response = requests.get(ics_url)
    if response.status_code == 200:
        return response.text
    else:
        st.error(f"Failed to fetch the ICS data. HTTP Status Code: {response.status_code}")
        return None

def calculate_duration(start_time, end_time):
    duration = end_time - start_time
    hours, remainder = divmod(duration.total_seconds(), 3600)
    minutes = remainder // 60
    return f"{int(hours)} hr {int(minutes)} min"

def get_date(start_time):
    return start_time.strftime("%Y-%m-%d")

def get_time(start_time):
    return start_time.strftime("%I:%M %p")

def get_day(start_time):
    return start_time.strftime("%A")

def substitute_class(location):
    class_substitutions = {
       'KK108-RM14-2024-104250': 'CRN',
        'KK108-TW06-2024-100420': 'CCFF',
        'KK108-TW04-2024-103467': 'CCFD',
        'KK108-2W04-2024-103479': 'CTYE',
        'KK108-TW06-2024-103469': 'CCFF',

      
        # 'KK108-CPSA-2024-104667': 'CPSA',
        # 'KK108-TW09-2024-100425': 'CCFI',
        # 'KK108-2W09-2024-101706': 'CTYJ',
        # 'KK108-RM08-2024-103459': 'CRH',
        # 'KK108-TW09-2024-103472': 'CCFI',
        # 'KK108-2W09-2024-103485': 'CTYJ',
    }
    return class_substitutions.get(location, location)

def filter_last_5_days(events):
    today = datetime.now().date()
    seen_events = set()
    last_5_days_events = [
        event for event in events
        if today - timedelta(days=15) <= event['start_time'].date() <= today
        and (event['Location'], event['start_time'], event['end_time']) not in seen_events
    ]
    seen_events.update((event['Location'], event['start_time'], event['end_time']) for event in last_5_days_events)
    return sorted(last_5_days_events, key=lambda x: (x['Class'], x['start_time']), reverse=True)

def sort_and_display_last_5_days(ics_url):
    ics_data = fetch_ics_from_url(ics_url)

    if ics_data:
        calendar = Calendar(ics_data)
        events = []

        for event in calendar.events:
            start_time = getattr(event, 'begin', '').datetime
            end_time = getattr(event, 'end', '').datetime

            event_info = {
                'Class': substitute_class(getattr(event, 'location', 'Unknown Location')),
                'Duration': calculate_duration(start_time, end_time),
                'Date': get_date(start_time),
                'Time': get_time(start_time),
                'Day': get_day(start_time),
                'start_time': start_time,
                'end_time': end_time,
                'Location': getattr(event, 'location', 'Unknown Location')
            }
            events.append(event_info)

        last_5_days_events = filter_last_5_days(events)
        classes = {'CRN': [], 'CCFF': [], 'CCFD': [], 'CTYE': []}
        for event in last_5_days_events:
            if event['Class'] in classes:
                classes[event['Class']].append(event)

        for class_name, events in classes.items():
            if events:
                df = pd.DataFrame(events).drop(columns=['start_time', 'end_time'])
                st.subheader(f"Class: {class_name}")
                st.dataframe(df)

# Streamlit app
st.title("Class Schedule Viewer")

ics_url = st.text_input("Enter the URL of the ICS file", "https://outlook.office365.com/owa/calendar/d7cf7de4fd9b4c1faca405f7195573a3@aakashicampus.com/17de5d40f83c4e33b157885d9c9328282645559226640515436/calendar.ics)

if st.button("Fetch and Display Schedule"):
    sort_and_display_last_5_days(ics_url)
