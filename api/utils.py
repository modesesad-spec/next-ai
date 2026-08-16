# utils.py — helper functions (optional)
import re

def clean_text(text):
    return re.sub(r'<[^>]*>', '', text)

def extract_emails(text):
    return re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
