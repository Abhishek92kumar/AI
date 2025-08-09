import streamlit as st
from ics import Calendar
from datetime import datetime
import requests

st.set_page_config(page_title="Current Status", page_icon="📅")

# def fetch_ics_from_url(ics_url):
#     response = requests.get(ics_url)
#     if response.status_code == 200:
#         return response.text
#     else:
#         st.error(f"Failed to fetch the ICS data. HTTP Status Code: {response.status_code}")
#         return None

# def substitute_class(location):
#     class_substitutions = {
#         'KK108-CPSA-2024-104667': 'CPSA',
#         'KK108-TW09-2024-100425': 'CCFI',
#         'KK108-2W09-2024-101706': 'CTYJ',
#         'KK108-RM08-2024-103459': 'CRH',
#         'KK108-TW09-2024-103472': 'CCFI',
#         'KK108-2W09-2024-103485': 'CTYJ',
#     }
#     return class_substitutions.get(location, location)

# def check_current_status(ics_url):
#     ics_data = fetch_ics_from_url(ics_url)
#     if not ics_data:
#         return

#     calendar = Calendar(ics_data)
#     now = datetime.now()

#     for event in calendar.events:
#         start_time = event.begin.datetime
#         end_time = event.end.datetime

#         if start_time <= now <= end_time:
#             st.error(f"🚨 You are currently BUSY: {substitute_class(event.location)}\n"
#                      f"🕒 {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}")
#             return

#     st.success("✅ You are currently FREE")

# Streamlit app
st.title("Live Class/Meeting Status")

# ics_url = "https://outlook.office365.com/owa/calendar/888f3bb6c2904fd39d8c125e42b7ab8d@aakashicampus.com/bcbe1538d6f34d84b4fe1ab75d7d6d0410158316872069178778/calendar.ics"

# if st.button("Check My Status"):
#     check_current_status(ics_url)
