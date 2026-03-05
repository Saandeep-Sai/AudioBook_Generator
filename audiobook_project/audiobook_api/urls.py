from django.urls import path
from .views import GenerateAudiobookView, DownloadAudiobookView
from .firebase_views import AudiobookLibraryView, AudiobookRetrieveView

urlpatterns = [
    path('generate_audio_book/', GenerateAudiobookView.as_view(), name='generate_audiobook'),
    path('download/<str:filename>/', DownloadAudiobookView.as_view(), name='download_audiobook'),
    path('library/', AudiobookLibraryView.as_view(), name='audiobook_library'),
    path('retrieve/<str:firebase_id>/', AudiobookRetrieveView.as_view(), name='retrieve_audiobook'),
]
