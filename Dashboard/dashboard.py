# With search facilty done on 21 June 2024
import os
import sqlite3
import pandas as pd
import streamlit as st
from image_loader import render_image

# Database path
database_path = 'student.db'
image_dir = "images"
st.set_page_config(page_title='Aakash Students Dashboard', page_icon='🎉')

# Streamlit app
def main():
    st.set_page_config(page_title="Student Batch Viewer", layout="wide")

    # Connect to the database
    conn = sqlite3.connect(database_path)
    
    st.title("Student Batch Viewer")

    # Sidebar for batch selection
    batch_list = pd.read_sql_query("SELECT DISTINCT batch FROM students", conn)['batch'].tolist()
    selected_batch = st.sidebar.selectbox("Select Batch", ["All"] + batch_list)

    # Load student data based on selected batch
    if selected_batch != "All":
        query = "SELECT ps_id, roll_no, batch, name, photo FROM students WHERE batch = ?"
        student_data = pd.read_sql_query(query, conn, params=[selected_batch])
    else:
        query = "SELECT ps_id, roll_no, batch, name, photo FROM students"
        student_data = pd.read_sql_query(query, conn)

    # Sidebar for search options
    search_option = st.sidebar.radio("Search by", ("PS ID", "Name", "Roll No"))
    search_term = st.sidebar.text_input(f"Enter {search_option}")

    # Apply search filter
    if search_term:
        search_term = search_term.strip()
        if search_option == "Name":
            student_data = student_data[student_data['name'].str.contains(search_term, case=False, na=False)]
        else:
            student_data = student_data[student_data[search_option.lower().replace(' ', '_')] == search_term]

    # Dropdown search by name
    student_names = student_data['name'].tolist()
    selected_name = st.sidebar.selectbox("Select Student Name", ["All"] + student_names)

    if selected_name != "All":
        student_data = student_data[student_data['name'] == selected_name]

    # Skip images button
    skip_images = st.sidebar.checkbox("Skip Images")

    # Display student data
    st.subheader(f"Displaying {selected_batch} Batch")
    
    css = """
    <style>
    .student-card {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-around;
        gap: 20px;
        margin: 20px 0;
    }
    .student-card div {
        border: 2px solid #ddd;
        padding: 10px;
        border-radius: 8px;
        width: 200px;
        text-align: center;
    }
    .student-card h3 {
        margin: 10px 0 5px 0;
    }
    .student-card p {
        margin: 5px 0;
    }
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)

    st.markdown("<div class='student-card'>", unsafe_allow_html=True)
    for _, row in student_data.iterrows():
        st.markdown(f"""
            <div>
                <h3>{row['name']}</h3>
                <p><strong>PS ID:</strong> {row['ps_id']}</p>
                <p><strong>Roll No:</strong> {row['roll_no']}</p>
        """, unsafe_allow_html=True)
        if not skip_images:
             
            # Display the image using render_image function
            # render_image(os.path.join(image_dir, row['photo']))
             
# This is new add
             render_image(os.path.join(image_dir, row['photo']))
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Close the database connection
    conn.close()

if __name__ == "__main__":
    main()

