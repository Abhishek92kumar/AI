import streamlit as st
from ics import Calendar
from datetime import datetime, timedelta
import pandas as pd
import requests

st.set_page_config(page_title='Aakash Automated BPR', page_icon='🎉')

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
        'KK108-2W05-2025-120713': 'CCFH',
        'KK108-CPSA-2025-121065': 'CPSA',
        'KK108-FSW2-2025-121173': 'FSIV',
        'KK108-MW04-2025-121094': 'CTYE',
        'KK108-RM15-2025-122783': 'CRO',
            }
    return class_substitutions.get(location, location)

def filter_last_5_days(events):
    today = datetime.now().date()
    seen_events = set()
    last_5_days_events = [
        event for event in events
        if today - timedelta(days=300) <= event['start_time'].date() <= today
        and (event['Location'], event['start_time'], event['end_time']) not in seen_events
    ]
    seen_events.update((event['Location'], event['start_time'], event['end_time']) for event in last_5_days_events)
    return sorted(last_5_days_events, key=lambda x: (x['Class'], x['start_time']), reverse=True)

def sort_and_display_last_5_days(ics_url):
    with st.spinner('Fetching and processing data takes 15-20 seconds...'):
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
            classes = {'CCFH': [], 'CRO': [], 'FSIV': [], 'CTYE': [],'CPSA': []}
            for event in last_5_days_events:
                if event['Class'] in classes:
                    classes[event['Class']].append(event)

            for class_name, events in classes.items():
                if events:
                    df = pd.DataFrame(events).drop(columns=['start_time', 'end_time'])
                    st.subheader(f"Class: {class_name}")
                    st.markdown(df.to_html(index=False, classes='styled-table'), unsafe_allow_html=True)

# Custom CSS for table styling
st.markdown("""
    <style>
        .styled-table {
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.9em;
            font-family: 'Trebuchet MS', sans-serif;
            min-width: 400px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
        }
        .styled-table thead tr {
            background-color: #009879;
            color: #ffffff;
            text-align: left;
        }
        .styled-table th,
        .styled-table td {
            padding: 12px 15px;
        }
        .styled-table tbody tr {
            border-bottom: 1px solid #dddddd;
            background-color: #2d2d2d;
            color: #ffffff;
        }
        .styled-table tbody tr:nth-of-type(even) {
            background-color: #3e3e3e;
        }
        .styled-table tbody tr:last-of-type {
            border-bottom: 2px solid #009879;
        }
    </style>
""", unsafe_allow_html=True)

# Streamlit app
st.title("Class Schedule Viewer")

# Fetch the URL from Streamlit secrets
ics_url = "https://outlook.office365.com/owa/calendar/888f3bb6c2904fd39d8c125e42b7ab8d@aakashicampus.com/bcbe1538d6f34d84b4fe1ab75d7d6d0410158316872069178778/calendar.ics"  # Fetch the URL from Streamlit secrets

if st.button("Fetch and Display Schedule"):
    sort_and_display_last_5_days(ics_url)
