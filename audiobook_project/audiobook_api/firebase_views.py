from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from firebase_admin import firestore
from firebase_utils import initialize_firebase

class AudiobookLibraryView(APIView):
    def get(self, request):
        try:
            initialize_firebase()
            db = firestore.client()
            
            # Get all audiobooks
            audiobooks_ref = db.collection("audiobooks")
            docs = audiobooks_ref.stream()
            
            audiobooks = []
            for doc in docs:
                data = doc.to_dict()
                audiobooks.append({
                    'id': doc.id,
                    'topic': data.get('topic'),
                    'duration': data.get('duration'),
                    'emotion': data.get('emotion'),
                    'segments': data.get('segments', []),
                    'created_at': data.get('created_at')
                })
            
            return Response({
                'success': True,
                'audiobooks': audiobooks
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AudiobookRetrieveView(APIView):
    def get(self, request, firebase_id):
        try:
            initialize_firebase()
            db = firestore.client()
            
            # Get audiobook metadata
            doc_ref = db.collection("audiobooks").document(firebase_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return Response({
                    'success': False,
                    'error': 'Audiobook not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get audio segments
            segments_ref = doc_ref.collection("audio_segments")
            segments = segments_ref.order_by("segment_index").stream()
            
            # Reconstruct base64 audio
            audio_content = ""
            for segment in segments:
                audio_content += segment.to_dict()['content']
            
            data = doc.to_dict()
            return Response({
                'success': True,
                'id': firebase_id,
                'topic': data.get('topic'),
                'duration': data.get('duration'),
                'emotion': data.get('emotion'),
                'segments': data.get('segments', []),
                'audio_base64': audio_content
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)