
import os
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

RESUME_DIR = r"C:\Users\cazam\Downloads\02_resume 전처리"
TARGET_FOLDER_ID = "1a7Gz8vvr0-YQRkeeoBGM5EXf8Gxk4Rru"

def get_drive_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            
            # Print URL explicitly for user
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f"\n[ACTION REQUIRED] Please visit this URL to authorize:\n{auth_url}\n")
            
            # Use fixed port 8080 to match potential console settings
            creds = flow.run_local_server(port=8080, open_browser=False)
            
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    return service

def upload_files():
    service = get_drive_service()
    
    # 1. List existing files in folder to avoid duplicates
    results = service.files().list(
        q=f"'{TARGET_FOLDER_ID}' in parents and trashed=false",
        fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    existing_files = {item['name'] for item in items}
    
    print(f"Found {len(existing_files)} existing files in Drive folder.")

    # 2. Upload
    for filename in os.listdir(RESUME_DIR):
        if filename in existing_files:
            continue
            
        file_path = os.path.join(RESUME_DIR, filename)
        if not os.path.isfile(file_path):
            continue
            
        file_metadata = {
            'name': filename,
            'parents': [TARGET_FOLDER_ID]
        }
        
        media = MediaFileUpload(file_path, resumable=True)
        
        print(f"Uploading {filename}...")
        try:
            file = service.files().create(body=file_metadata,
                                        media_body=media,
                                        fields='id').execute()
            print(f"File ID: {file.get('id')}")
        except Exception as e:
            print(f"Failed to upload {filename}: {e}")

if __name__ == "__main__":
    try:
        upload_files()
    except Exception as e:
        print(f"Error: {e}")
