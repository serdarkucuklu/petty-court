def build_body(script):
    return {
        "snippet": {"title": script.title[:100], "description": script.description,
                    "tags": script.tags, "categoryId": "24"},   # 24 = Entertainment
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }

def upload(mp4, script, service):
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(mp4, chunksize=-1, resumable=True) if mp4 else None
    req = service.videos().insert(part="snippet,status", body=build_body(script), media_body=media)
    return req.execute()["id"]

def build_service(client_id, client_secret, refresh_token):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(
        None, refresh_token=refresh_token, client_id=client_id, client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    return build("youtube", "v3", credentials=creds)
