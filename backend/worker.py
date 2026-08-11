import os
import time
import requests
from PyPDF2 import PdfReader
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# The directory simulating our S3 Bucket
WATCH_DIR = "./s3_inbox"
API_URL = "http://localhost:8000/api/threads/start"

class PDFIngestionHandler(FileSystemEventHandler):
    def on_created(self, event):
        # Ignore directory creations or non-PDF files
        if event.is_directory or not event.src_path.lower().endswith(".pdf"):
            return
            
        print(f"\n[EVENT] New contract detected: {event.src_path}")
        self.process_contract(event.src_path)

    def process_contract(self, filepath):
        try:
            # 1. Parse the physical PDF
            print("[WORKER] Extracting byte stream...")
            reader = PdfReader(filepath)
            raw_text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])
            
            # 2. Use synchronized thread ID for frontend radar
            thread_id = "portfolio_live_demo"
            
            # 3. Fire the payload to the LangGraph Swarm
            print(f"[WORKER] Triggering AI Swarm for Thread: {thread_id}")
            payload = {
                "thread_id": thread_id,
                "file_uri": filepath,
                "extracted_text": raw_text[:2000] # Passing real text to the AI
            }
            
            response = requests.post(API_URL, json=payload)
            
            if response.status_code == 200:
                print(f"[SUCCESS] Swarm execution started successfully.")
            else:
                print(f"[ERROR] API failed: {response.text}")
                
        except Exception as e:
            print(f"[FATAL] Pipeline crashed: {str(e)}")

if __name__ == "__main__":
    # Create the inbox directory if it doesn't exist
    os.makedirs(WATCH_DIR, exist_ok=True)
    
    event_handler = PDFIngestionHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    
    print(f"[*] Autonomous Ingestion Worker Online.")
    print(f"[*] Listening for PDF drops in {WATCH_DIR}...")
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
