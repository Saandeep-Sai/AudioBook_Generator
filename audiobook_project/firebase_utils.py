import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import os

def initialize_firebase():
    if not firebase_admin._apps:
        b64_credentials = os.getenv("FIREBASE_CREDENTIALS_BASE64")
        project_id = os.getenv("FIREBASE_PROJECT_ID")
        
        decoded = base64.b64decode(b64_credentials)
        cred_dict = json.loads(decoded.decode())
        cred = credentials.Certificate(cred_dict)
        
        firebase_admin.initialize_app(cred, {
            "projectId": project_id
        })

def split_base64_string(b64_string, segment_size=250000):
    return {
        f"segment_{i+1}": b64_string[i:i+segment_size]
        for i in range(0, len(b64_string), segment_size)
    }

def save_audiobook_to_firestore(audio_path: str, topic: str, duration: int, emotion: str, segments_data: list):
    initialize_firebase()
    db = firestore.client()
    
    # Convert audio to base64
    with open(audio_path, "rb") as audio_file:
        audio_data = audio_file.read()
        encoded_audio = base64.b64encode(audio_data).decode('utf-8')
    
    # Create master document
    doc_ref = db.collection("audiobooks").document()
    doc_ref.set({
        "topic": topic,
        "duration": duration,
        "emotion": emotion,
        "segment_count": 0,
        "segments": segments_data,
        "created_at": firestore.SERVER_TIMESTAMP
    })
    
    # Split and store audio segments
    audio_segments = split_base64_string(encoded_audio)
    segment_coll = doc_ref.collection("audio_segments")
    
    for i, (segment_id, content) in enumerate(audio_segments.items(), start=1):
        segment_coll.document(segment_id).set({
            "segment_index": i,
            "content": content
        })
    
    # Update segment count
    doc_ref.update({"segment_count": len(audio_segments)})
    
    return doc_ref.id