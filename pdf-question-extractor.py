# Comprehensive PDF Question Extraction Pipeline
# Handles various PDF formats and layouts for building educational databases

import os
import re
import json
import logging
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import base64
from io import BytesIO

# Core PDF processing libraries
import fitz  # PyMuPDF - install: pip install PyMuPDF
import pdfplumber  # install: pip install pdfplumber
from pypdf import PdfReader  # install: pip install pypdf

# OCR libraries
import pytesseract  # install: pip install pytesseract
from pdf2image import convert_from_path  # install: pip install pdf2image

# NLP libraries
import spacy  # install: pip install spacy
from transformers import pipeline  # install: pip install transformers

# Document AI libraries (optional, for advanced layout detection)
# from azure.ai.documentintelligence import DocumentIntelligenceClient
# from google.cloud import documentai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Question:
    """Data structure for a question"""
    id: str
    question_text: str
    options: Dict[str, str]
    correct_answer: str
    exam: str
    year: Optional[int]
    subject: str
    sub_topic: str
    image_path: Optional[str] = None
    source_info: Optional[str] = None

class PDFQuestionExtractor:
    """
    Comprehensive PDF Question Extraction System
    Handles multiple PDF types: text-based, scanned images, mixed layouts
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.setup_nlp()
        
    def _default_config(self) -> Dict:
        return {
            'ocr_engine': 'tesseract',  # tesseract, azure, google
            'text_extraction': 'auto',  # pymupdf, pdfplumber, pypdf, auto
            'question_patterns': [
                r'^(\d+\.?\s*)',  # "1. ", "1) "
                r'^([A-Z]\.?\s*)',  # "A. ", "B) "
                r'^\s*Question\s*:?\s*(\d+)',  # "Question: 1"
            ],
            'option_patterns': [
                r'^\s*\([a-d]\)\s*(.+)',  # "(a) option"
                r'^\s*[a-d][\.\)]\s*(.+)',  # "a. option" or "a) option"
                r'^\s*\[[a-d]\]\s*(.+)',  # "[a] option"
            ],
            'answer_patterns': [
                r'Answer[:\s]*([a-d])',
                r'Ans[:\s]*([a-d])',
                r'^\s*([a-d])\s*$',
            ],
            'subject_mapping': {
                'physics': ['motion', 'dynamics', 'kinematics', 'mechanics'],
                'chemistry': ['organic', 'inorganic', 'physical chemistry'],
                'biology': ['botany', 'zoology', 'genetics'],
                'mathematics': ['algebra', 'geometry', 'calculus']
            }
        }
    
    def setup_nlp(self):
        """Initialize NLP models"""
        try:
            # Load spaCy model for text processing
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
            
        # Initialize question-answering pipeline for content classification
        try:
            self.qa_pipeline = pipeline("question-answering", 
                                       model="distilbert-base-cased-distilled-squad")
        except Exception as e:
            logger.warning(f"Could not load QA pipeline: {e}")
            self.qa_pipeline = None

    def extract_text_pymupdf(self, pdf_path: str) -> Tuple[List[str], List[Dict]]:
        """Extract text using PyMuPDF (best for most PDFs)"""
        doc = fitz.open(pdf_path)
        pages_text = []
        pages_blocks = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract plain text
            text = page.get_text()
            pages_text.append(text)
            
            # Extract structured blocks with layout information
            blocks = page.get_text("dict")
            pages_blocks.append(blocks)
            
        doc.close()
        return pages_text, pages_blocks
    
    def extract_text_pdfplumber(self, pdf_path: str) -> Tuple[List[str], List[Dict]]:
        """Extract text using pdfplumber (good for tables and structured data)"""
        pages_text = []
        pages_data = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
                
                # Extract tables if present
                tables = page.extract_tables()
                
                # Get page layout info
                page_data = {
                    'text': text,
                    'tables': tables,
                    'width': page.width,
                    'height': page.height
                }
                pages_data.append(page_data)
                
        return pages_text, pages_data
    
    def extract_text_with_ocr(self, pdf_path: str) -> List[str]:
        """Extract text using OCR (for scanned PDFs)"""
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=300)
        pages_text = []
        
        for i, image in enumerate(images):
            # Preprocess image for better OCR
            image_np = np.array(image)
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
            
            # Apply image preprocessing
            denoised = cv2.fastNlMeansDenoising(gray)
            thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # OCR with Tesseract
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(thresh, config=custom_config)
            pages_text.append(text)
            
            logger.info(f"OCR processed page {i+1}")
            
        return pages_text
    
    def extract_images_from_pdf(self, pdf_path: str, output_dir: str) -> List[str]:
        """Extract images from PDF and save them"""
        doc = fitz.open(pdf_path)
        image_paths = []
        
        os.makedirs(output_dir, exist_ok=True)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    img_filename = f"page_{page_num+1}_img_{img_index+1}.png"
                    img_path = os.path.join(output_dir, img_filename)
                    pix.save(img_path)
                    image_paths.append(img_path)
                    
                pix = None
                
        doc.close()
        return image_paths
    
    def detect_pdf_type(self, pdf_path: str) -> str:
        """Detect if PDF is text-based or image-based"""
        doc = fitz.open(pdf_path)
        
        text_chars = 0
        total_chars = 0
        
        # Sample first few pages
        sample_pages = min(3, len(doc))
        
        for page_num in range(sample_pages):
            page = doc[page_num]
            text = page.get_text()
            text_chars += len(text.strip())
            
            # Check if page has images
            images = page.get_images()
            if images:
                total_chars += 1000  # Assume image-heavy content
                
        doc.close()
        
        if text_chars < 100 and total_chars > 500:
            return "scanned"
        elif text_chars > 500:
            return "text_based"
        else:
            return "mixed"
    
    def extract_text_adaptive(self, pdf_path: str) -> Tuple[List[str], str]:
        """Adaptively choose extraction method based on PDF type"""
        pdf_type = self.detect_pdf_type(pdf_path)
        logger.info(f"Detected PDF type: {pdf_type}")
        
        if pdf_type == "scanned":
            pages_text = self.extract_text_with_ocr(pdf_path)
        elif pdf_type == "text_based":
            pages_text, _ = self.extract_text_pymupdf(pdf_path)
        else:  # mixed
            # Try text extraction first, fallback to OCR if needed
            pages_text, _ = self.extract_text_pymupdf(pdf_path)
            
            # If text extraction yields poor results, use OCR
            if sum(len(page.strip()) for page in pages_text) < 100:
                pages_text = self.extract_text_with_ocr(pdf_path)
                
        return pages_text, pdf_type
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common OCR errors
        text = text.replace('|', 'I')
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Split joined words
        
        # Normalize quotes and dashes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace('—', '-').replace('–', '-')
        
        return text.strip()
    
    def segment_questions(self, text: str) -> List[str]:
        """Segment text into individual questions"""
        # Split by question patterns
        patterns = self.config['question_patterns']
        
        segments = []
        current_segment = ""
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line starts a new question
            is_new_question = False
            for pattern in patterns:
                if re.match(pattern, line):
                    is_new_question = True
                    break
                    
            if is_new_question and current_segment:
                segments.append(current_segment.strip())
                current_segment = line
            else:
                current_segment += " " + line
                
        # Add the last segment
        if current_segment:
            segments.append(current_segment.strip())
            
        return segments
    
    def parse_question_block(self, block: str) -> Optional[Question]:
        """Parse a question block into structured data"""
        lines = block.split('\n')
        question_text = ""
        options = {}
        correct_answer = ""
        
        current_section = "question"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for options
            option_match = None
            for pattern in self.config['option_patterns']:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    option_match = match
                    break
                    
            if option_match:
                # Extract option letter and text
                option_letter = line[0].lower() if line[0].isalpha() else line[1].lower()
                option_text = option_match.group(1) if option_match.lastindex else line[3:].strip()
                options[option_letter] = option_text
                current_section = "options"
            
            # Check for answer
            answer_match = None
            for pattern in self.config['answer_patterns']:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    correct_answer = match.group(1).lower()
                    break
                    
            # Build question text
            if current_section == "question" and not option_match and not answer_match:
                question_text += " " + line
                
        # Clean and validate
        question_text = self.clean_text(question_text)
        
        if not question_text or len(options) < 2:
            return None
            
        # Generate question ID
        question_id = f"q_{hash(question_text[:50]) % 10000:04d}"
        
        # Extract metadata (exam, subject, etc.)
        exam_info = self.extract_metadata(block)
        
        return Question(
            id=question_id,
            question_text=question_text,
            options=options,
            correct_answer=correct_answer,
            exam=exam_info.get('exam', 'Unknown'),
            year=exam_info.get('year'),
            subject=exam_info.get('subject', 'General'),
            sub_topic=exam_info.get('sub_topic', ''),
            source_info=block[:100] + "..." if len(block) > 100 else block
        )
    
    def extract_metadata(self, text: str) -> Dict:
        """Extract exam metadata from text"""
        metadata = {}
        
        # Extract year
        year_match = re.search(r'(19|20)\d{2}', text)
        if year_match:
            metadata['year'] = int(year_match.group())
            
        # Extract exam board/type
        exam_patterns = [
            r'(JEE|NEET|AIIMS|CBSE|NCERT|IIT)',
            r'(PMT|PET|CET|EAMCET)',
        ]
        
        for pattern in exam_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['exam'] = match.group(1).upper()
                break
                
        # Extract subject using keyword matching
        text_lower = text.lower()
        for subject, keywords in self.config['subject_mapping'].items():
            for keyword in keywords:
                if keyword in text_lower:
                    metadata['subject'] = subject.title()
                    metadata['sub_topic'] = keyword.title()
                    break
            if 'subject' in metadata:
                break
                
        return metadata
    
    def process_pdf(self, pdf_path: str, output_dir: str = None) -> List[Question]:
        """Main method to process a PDF and extract questions"""
        logger.info(f"Processing PDF: {pdf_path}")
        
        if output_dir is None:
            output_dir = os.path.splitext(pdf_path)[0] + "_extracted"
            
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract text
        pages_text, pdf_type = self.extract_text_adaptive(pdf_path)
        
        # Extract images if present
        image_paths = self.extract_images_from_pdf(pdf_path, os.path.join(output_dir, "images"))
        
        # Combine all text
        full_text = "\n".join(pages_text)
        full_text = self.clean_text(full_text)
        
        # Segment into question blocks
        question_blocks = self.segment_questions(full_text)
        
        # Parse each block
        questions = []
        for i, block in enumerate(question_blocks):
            question = self.parse_question_block(block)
            if question:
                # Try to associate with relevant images
                if image_paths and i < len(image_paths):
                    question.image_path = image_paths[i]
                    
                questions.append(question)
                
        logger.info(f"Extracted {len(questions)} questions from {pdf_path}")
        
        # Save results
        self.save_questions(questions, os.path.join(output_dir, "questions.json"))
        
        return questions
    
    def save_questions(self, questions: List[Question], output_path: str):
        """Save questions to JSON file"""
        questions_data = []
        for q in questions:
            questions_data.append({
                'id': q.id,
                'question': q.question_text,
                'options': q.options,
                'correct_answer': q.correct_answer,
                'exam': q.exam,
                'year': q.year,
                'subject': q.subject,
                'sub_topic': q.sub_topic,
                'image_path': q.image_path,
                'source_info': q.source_info
            })
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(questions_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved {len(questions)} questions to {output_path}")
    
    def process_directory(self, pdf_directory: str, output_directory: str = None) -> Dict[str, List[Question]]:
        """Process all PDFs in a directory"""
        if output_directory is None:
            output_directory = os.path.join(pdf_directory, "extracted_questions")
            
        os.makedirs(output_directory, exist_ok=True)
        
        all_questions = {}
        
        for filename in os.listdir(pdf_directory):
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(pdf_directory, filename)
                output_subdir = os.path.join(output_directory, os.path.splitext(filename)[0])
                
                try:
                    questions = self.process_pdf(pdf_path, output_subdir)
                    all_questions[filename] = questions
                except Exception as e:
                    logger.error(f"Error processing {filename}: {e}")
                    all_questions[filename] = []
                    
        # Save consolidated database
        self.create_question_database(all_questions, output_directory)
        
        return all_questions
    
    def create_question_database(self, all_questions: Dict[str, List[Question]], output_dir: str):
        """Create consolidated question database"""
        consolidated = []
        
        for pdf_name, questions in all_questions.items():
            for question in questions:
                q_data = {
                    'id': question.id,
                    'question': question.question_text,
                    'options': question.options,
                    'correct_answer': question.correct_answer,
                    'exam': question.exam,
                    'year': question.year,
                    'subject': question.subject,
                    'sub_topic': question.sub_topic,
                    'image_path': question.image_path,
                    'source_pdf': pdf_name
                }
                consolidated.append(q_data)
                
        # Save to multiple formats
        database_path = os.path.join(output_dir, "question_database.json")
        with open(database_path, 'w', encoding='utf-8') as f:
            json.dump(consolidated, f, indent=2, ensure_ascii=False)
            
        # Create CSV for easy import into databases
        import csv
        csv_path = os.path.join(output_dir, "question_database.csv")
        
        if consolidated:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=consolidated[0].keys())
                writer.writeheader()
                
                for question in consolidated:
                    # Flatten options for CSV
                    row = question.copy()
                    for key, value in question['options'].items():
                        row[f'option_{key}'] = value
                    del row['options']
                    writer.writerow(row)
                    
        logger.info(f"Created consolidated database with {len(consolidated)} questions")


# Example usage and testing
def main():
    """Example usage of the PDF Question Extractor"""
    
    # Initialize extractor
    config = {
        'ocr_engine': 'tesseract',
        'text_extraction': 'auto',
    }
    
    extractor = PDFQuestionExtractor(config)
    
    # Process single PDF
    pdf_path = "Part-02-Question-141-161-Copy.pdf"  # Your uploaded file
    
    if os.path.exists(pdf_path):
        try:
            questions = extractor.process_pdf(pdf_path)
            print(f"Successfully extracted {len(questions)} questions")
            
            # Print first few questions as examples
            for i, q in enumerate(questions[:3]):
                print(f"\n=== Question {i+1} ===")
                print(f"ID: {q.id}")
                print(f"Question: {q.question_text[:100]}...")
                print(f"Options: {q.options}")
                print(f"Answer: {q.correct_answer}")
                print(f"Subject: {q.subject}")
                
        except Exception as e:
            print(f"Error processing PDF: {e}")
    
    # Process directory of PDFs
    # pdf_directory = "path/to/your/pdfs"
    # all_questions = extractor.process_directory(pdf_directory)
    # print(f"Total questions extracted from directory: {sum(len(qs) for qs in all_questions.values())}")


if __name__ == "__main__":
    main()