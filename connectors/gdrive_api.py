import os
import json
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

class GDriveConnector:
    def __init__(self, secrets_path="secrets.json", token_path="/tmp/gdrive_token.pickle"):
        with open(secrets_path, "r") as f:
            self.secrets = json.load(f)
        
        self.token_path = token_path
        self.creds = None
        self.scopes = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata.readonly']
        self._authenticate()
        self.service = build('drive', 'v3', credentials=self.creds)

    def _authenticate(self):
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                client_config = {
                    "installed": {
                        "client_id": self.secrets["GOOGLE_CLIENT_ID"],
                        "client_secret": self.secrets["GOOGLE_CLIENT_SECRET"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                }
                flow = InstalledAppFlow.from_client_config(client_config, self.scopes)
                # Use a FIXED PORT to avoid redirect_uri_mismatch
                self.creds = flow.run_local_server(port=8080)
            
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)

    def upload_file(self, local_path, folder_id, filename=None):
        """Uploads a file to a specific Google Drive folder."""
        file_metadata = {
            'name': filename or os.path.basename(local_path),
            'parents': [folder_id]
        }
        
        # Determine MIME type (basic)
        mime_type = 'application/octet-stream'
        if local_path.endswith('.pdf'): mime_type = 'application/pdf'
        elif local_path.endswith('.docx'): mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
        file = self.service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        return file.get('id'), file.get('webViewLink')

if __name__ == "__main__":
    # Test connection
    connector = GDriveConnector()
    print("Google Drive Authentication Successful.")
