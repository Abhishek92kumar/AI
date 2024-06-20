import os
import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
import sqlite3

# Configuration
pdf_paths = [
    "D://To Be uploaded//Documents//Distribution List for CCFI Batch.pdf",
    "D://To Be uploaded//Documents//Distribution List for CTYJ Batch.pdf",
    # Add more PDF file paths if needed
]
image_dir = "images"
os.makedirs(image_dir, exist_ok=True)
database_path = 'students.db'
csv_output_path = 'students.csv'

# Remove this if do not want to delete the existing database
if os.path.exists(database_path):
    os.remove(database_path)
    
    
# Initialize database
conn = sqlite3.connect('student.db')
cursor = conn.cursor()

# Create table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ps_id TEXT,
        roll_no TEXT,
        batch TEXT,
        name TEXT,
        photo TEXT,
        course_id TEXT,
        ho_class TEXT
    )
''')

def recoverpix(doc, item):
    xref = item[0]  # xref of PDF image
    smask = item[1]  # xref of its /SMask

    if smask > 0:
        pix0 = fitz.Pixmap(doc.extract_image(xref)["image"])
        if pix0.alpha:  # catch irregular situation
            pix0 = fitz.Pixmap(pix0, 0)  # remove alpha channel
        mask = fitz.Pixmap(doc.extract_image(smask)["image"])
        try:
            pix = fitz.Pixmap(pix0, mask)
        except:  # fallback to original base image in case of problems
            pix = fitz.Pixmap(doc.extract_image(xref)["image"])
        if pix0.n > 3:
            ext = "pam"
        else:
            ext = "png"
        return {"ext": ext, "colorspace": pix.colorspace.n, "image": pix.tobytes(ext)}
    if "/ColorSpace" in doc.xref_object(xref, compressed=True):
        pix = fitz.Pixmap(doc, xref)
        pix = fitz.Pixmap(fitz.csRGB, pix)
        return {"ext": "png", "colorspace": 3, "image": pix.tobytes("png")}
    return doc.extract_image(xref)

def extract_images(pdf_path):
    doc = fitz.open(pdf_path)
    page_count = doc.page_count
    xreflist = []
    imglist = []
    for pno in range(page_count):
        il = doc.get_page_images(pno)
        imglist.extend([x[0] for x in il])
        for img in il:
            xref = img[0]
            if xref in xreflist:
                continue
            image = recoverpix(doc, img)
            n = image["colorspace"]
            imgdata = image["image"]
            imgfile = os.path.join(image_dir, f"img_{xref}.{image['ext']}")
            with open(imgfile, "wb") as fout:
                fout.write(imgdata)
            xreflist.append(xref)
    return xreflist

def extract_tables(pdf_path):
    all_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                df = pd.DataFrame(table)
                all_tables.append(df)
    combined_df = pd.concat(all_tables, ignore_index=True)
    combined_df = combined_df.drop_duplicates()  # Drop rows that are exact duplicates
    combined_df.rename(columns={0: "Sl", 1: "PS ID", 2: "Roll No.", 3: "Batch", 4: "Name of Student", 5: "Photo", 6: "Course ID", 7: "HO Class"}, inplace=True)
    combined_df = combined_df[combined_df["Sl"].str.contains("Sl") == False]
    combined_df = combined_df[combined_df["PS ID"].str.contains("PS ID") == False]
    combined_df = combined_df[combined_df["Roll No."].str.contains("Roll No.") == False]
    combined_df = combined_df[combined_df["Batch"].str.contains("Batch") == False]
    combined_df = combined_df[combined_df["Name of Student"].str.contains("Name of\nStudent") == False]
    combined_df = combined_df[combined_df["Photo"].str.contains("Photo") == False]
    return combined_df

def clean_filename(name):
    # Replace newline characters and other invalid characters with an underscore
    invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|', '\n']
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name

def process_pdfs(pdf_paths):
    for pdf_path in pdf_paths:
        print(f"Processing {pdf_path}...")
        images = extract_images(pdf_path)
        df = extract_tables(pdf_path)
        
        # Link images to students
        student_data = []
        img_files = sorted([f for f in os.listdir(image_dir) if f.startswith("img_") and f.endswith(".png")], key=lambda x: int(x.split('_')[1].split('.')[0]))
        
        # Skip irrelevant images and ensure correct alignment
        img_idx = 0
        for idx, row in df.iterrows():
            while img_idx < len(img_files) and (img_files[img_idx] in ["img_6.png"] 
#                                                 or img_files[img_idx] == "img_6.png"
                                               ):  # Adjust conditions as necessary
                img_idx += 1
            
            if img_idx >= len(img_files):
                break
            
            img_file = img_files[img_idx]
            img_idx += 1
            
            ps_id = row['PS ID']
            roll_no = row['Roll No.']
            batch = row['Batch']
            name = row['Name of Student']
            course_id = row['Course ID']
            ho_class = row['HO Class']
            
            # Clean the student name for file naming
            clean_name = clean_filename(name)
            image_name = f"{clean_name}_{ps_id}.png"
            image_path = os.path.join(image_dir, image_name)
            
            # Rename the image file to the new name
            os.rename(os.path.join(image_dir, img_file), image_path)
            
            student_data.append((ps_id, roll_no, batch, name, image_path, course_id, ho_class))
            # Update the dataframe with the image path
            df.at[idx, 'Photo'] = image_path
        
        # Print the updated dataframe
        print(df)
#         df.to_csv(csv_output_path, index=False)
        
        # Insert data into database
        cursor.executemany('''
            INSERT INTO students (ps_id, roll_no, batch, name, photo, course_id, ho_class)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', student_data)
    
    conn.commit()
    df = pd.read_sql_query("SELECT * FROM students", conn)

    df.to_csv(csv_output_path, index=False)
    conn.close()

process_pdfs(pdf_paths)
