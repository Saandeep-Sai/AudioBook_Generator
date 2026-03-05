import os
import time
import asyncio
from django.http import FileResponse, Http404
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import AudiobookRequestSerializer, AudiobookResponseSerializer
from firebase_utils import save_audiobook_to_firestore
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from audio_book_gen import AudioBookGenerator

class GenerateAudiobookView(APIView):
    def post(self, request):
        serializer = AudiobookRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        start_time = time.time()
        
        try:
            # Run async audiobook generation
            result = asyncio.run(self._generate_audiobook(
                data['topic'],
                data['duration'],
                data['emotion']
            ))
            
            generation_time = time.time() - start_time
            minutes = int(generation_time // 60)
            seconds = int(generation_time % 60)
            
            if result['success']:
                # Format segments for frontend
                segments_data = []
                for segment in result.get('segments_objects', []):
                    segments_data.append({
                        'text': segment.text,
                        'start_time': segment.start_time,
                        'end_time': segment.end_time,
                        'duration': segment.duration
                    })
                
                # Save to Firebase Firestore
                try:
                    firebase_doc_id = save_audiobook_to_firestore(
                        result['audio_path'], 
                        result['topic'], 
                        result['duration'], 
                        result['emotion'], 
                        segments_data
                    )
                    # Clean up local file after Firebase save
                    os.remove(result['audio_path'])
                except Exception as e:
                    firebase_doc_id = None
                    print(f"Firebase save failed: {e}")
                
                response_data = {
                    'success': True,
                    'firebase_id': firebase_doc_id,
                    'topic': result['topic'],
                    'duration': result['duration'],
                    'emotion': result['emotion'],
                    'segments': segments_data,
                    'segment_count': len(segments_data),
                    'word_count': result['word_count'],
                    'generation_time': f"{minutes}m {seconds}s"
                }
            else:
                response_data = {
                    'success': False,
                    'error': result['error'],
                    'generation_time': f"{minutes}m {seconds}s"
                }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            generation_time = time.time() - start_time
            minutes = int(generation_time // 60)
            seconds = int(generation_time % 60)
            
            return Response({
                'success': False,
                'error': str(e),
                'generation_time': f"{minutes}m {seconds}s"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    async def _generate_audiobook(self, topic, duration, emotion):
        generator = AudioBookGenerator()  # Uses .env file
        result = await generator.create_audiobook(topic, duration, emotion)
        # Store segments objects for frontend use
        if result['success']:
            result['segments_objects'] = generator.last_generated_segments
        return result

class DownloadAudiobookView(APIView):
    def get(self, request, filename):
        file_path = os.path.join(settings.MEDIA_ROOT, filename)
        if os.path.exists(file_path):
            return FileResponse(
                open(file_path, 'rb'),
                as_attachment=True,
                filename=filename,
                content_type='audio/mpeg'
            )
        raise Http404("Audio file not found")