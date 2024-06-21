import os
import sqlite3
import pandas as pd
import streamlit as st
from image_loader import render_image  # Ensure correct import

# Database path
database_path = 'student.db'
image_dir = "images"

# Streamlit app
def main():
    st.set_page_config(page_title="Student Batch Viewer", layout="wide")

    # Connect to the database
    conn = sqlite3.connect(database_path)
    
    st.title("Student Batch Viewer")

    # Sidebar for batch selection
    batch_list = pd.read_sql_query("SELECT DISTINCT batch FROM students", conn)['batch'].tolist()
    selected_batch = st.sidebar.selectbox("Select Batch", ["All"] + batch_list)

    if selected_batch != "All":
        query = "SELECT ps_id, roll_no, batch, name, photo FROM students WHERE batch = ?"
        student_data = pd.read_sql_query(query, conn, params=[selected_batch])
    else:
        query = "SELECT ps_id, roll_no, batch, name, photo FROM students"
        student_data = pd.read_sql_query(query, conn)

    # Sidebar for individual student selection
    student_list = student_data['ps_id'].tolist()
    selected_student = st.sidebar.selectbox("Select Student (PS ID)", ["All"] + student_list)

    if selected_student != "All":
        query = "SELECT ps_id, roll_no, batch, name, photo FROM students WHERE batch = ? AND ps_id = ?"
        student_data = pd.read_sql_query(query, conn, params=[selected_batch, selected_student])

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
        # Display the image using render_image function
        render_image(os.path.join(image_dir, row['photo']))
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Close the database connection
    conn.close()

if __name__ == "__main__":
    main()
