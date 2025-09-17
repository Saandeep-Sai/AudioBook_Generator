# 🎧 Cinematic AI Audiobook Generator

Generate professional-quality audiobooks with intelligent background ambience using Gemini AI and Edge TTS. Features ChatGPT-like natural narration with cinematic sound design.

## ✨ Features

- **🧠 Intelligent Content Generation**: Gemini AI creates structured segments with audio cues
- **🎙️ Natural Voice Synthesis**: Edge TTS with emotion-based voice selection
- **🎵 Cinematic Audio Design**: Real ambience files with intelligent placement
- **⚡ Parallel Processing**: Simultaneous segment generation for speed
- **🎚️ Professional Audio**: Dynamic ducking, compression, and EQ
- **🔄 Chunked Generation**: Handles long durations without timeouts
- **🌐 Dual Interface**: CLI and REST API support

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Environment
```bash
# Create .env file
echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
```

### 3. Add Audio Files
Place ambience files in `sounds/` folder:
```
sounds/
├── ambient-piano-logo-165357.mp3
├── forest-nature-322637.mp3
├── nature-ambience-323729.mp3
├── spring-forest-nature-332842.mp3
└── [other ambience files...]
```

### 4. Generate Audiobook
```bash
python audio_book_gen.py
```

## 🎯 Usage

### CLI Interface
```bash
python audio_book_gen.py
# Prompts:
# - Gemini API key (or use .env)
# - Topic: "The History of Space Exploration"
# - Duration: 15 minutes
# - Emotion: serious/cheerful/mystery/neutral
```

### API Interface
```bash
# Start server
uvicorn audio_book_gen:app --host 0.0.0.0 --port 8000

# Generate audiobook
curl -X POST "http://localhost:8000/generate-audiobook" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Ancient Egyptian Mysteries",
    "duration": 10,
    "emotion": "mystery",
    "api_key": "your_gemini_api_key"
  }'
```

## 🎭 Emotion Voices

| Emotion | Voice | Characteristics |
|---------|-------|----------------|
| **Cheerful** | JennyNeural | Bright, energetic, 1.1x speed |
| **Serious** | DavisNeural | Authoritative, warm, 0.85x speed |
| **Mystery** | AriaNeural | Atmospheric, deeper, 0.8x speed |
| **Neutral** | JennyNeural | Conversational, balanced, 0.9x speed |

## 🎵 Audio Features

### Intelligent Background Audio
- **Gemini-directed placement**: AI selects appropriate ambience per scene
- **Dynamic discovery**: Automatically finds audio files in `sounds/` folder
- **Smart mixing**: -20dB background with dynamic ducking during speech
- **Professional processing**: EQ, compression, and normalization

### Cinematic Effects
- **Piano transitions**: Signature cues at start/end
- **Fade in/out**: Smooth audio transitions
- **Speech detection**: Background lowers during narration
- **Layered ambience**: Multiple audio tracks for richness

## 📁 Project Structure

```
audio_book_generator/
├── audio_book_gen.py          # Main application
├── requirements.txt           # Dependencies
├── .env.example              # Environment template
├── sounds/                   # Ambience audio files
│   ├── README.md            # Audio file guide
│   └── [audio files...]
└── README.md                # This file
```

## 🔧 Technical Details

### Content Generation
- **Structured segments**: JSON-based narrative with audio assignments
- **Chunked processing**: 5-minute chunks for long audiobooks
- **Retry logic**: Exponential backoff for API reliability
- **Word targeting**: 165 words/minute precision

### Audio Processing
- **Parallel TTS**: All segments generated simultaneously
- **Professional pipeline**: Compression → EQ → Normalization
- **Export quality**: 192kbps MP3, 44.1kHz
- **Memory efficient**: Cleanup of temporary files

### Voice Enhancement
- **Conversational text**: Natural speech patterns without SSML
- **Emotion markers**: "Well, ", "Indeed, ", "But then..." 
- **Strategic pauses**: Ellipsis for natural breathing
- **Speed adjustment**: Emotion-based playback rates

## 🎨 Audio Sources

### Recommended Sources
- **Freesound.org** (CC-0 licensed)
- **Pixabay Audio** (royalty-free)
- **Mixkit** (free commercial use)

### File Requirements
- **Format**: MP3 or WAV
- **Length**: 30 seconds to 5 minutes
- **Quality**: 44.1kHz recommended
- **Naming**: Descriptive filenames (forest-nature-322637.mp3)

## 🚨 Troubleshooting

### Common Issues
- **504 Timeout**: Use shorter durations (<10 min) or chunked generation handles this
- **Missing audio files**: Check `sounds/` folder and file names
- **API key errors**: Verify GEMINI_API_KEY in .env or input
- **TTS failures**: Automatic fallback to plain voice

### Performance Tips
- **Shorter segments**: Better for parallel processing
- **Smaller audio files**: Faster loading and processing
- **SSD storage**: Improves audio file I/O performance

## 📊 Output

### Generated Files
- **`{topic}_audiobook.mp3`**: Final cinematic audiobook
- **Progress logs**: Detailed generation tracking
- **Temporary cleanup**: Automatic intermediate file removal

### Quality Metrics
- **Professional audio**: Broadcast-quality output
- **Natural speech**: ChatGPT-like voice quality
- **Cinematic mixing**: Film-quality background integration
- **Scalable duration**: 5 minutes to 60+ minutes

## 🛠️ Tech Stack

- **AI Content**: Google Gemini 2.5 Flash
- **Voice Synthesis**: Microsoft Edge TTS
- **Audio Processing**: pydub + FFmpeg
- **Web Framework**: FastAPI
- **Async Processing**: asyncio + tqdm
- **Environment**: python-dotenv

## 📄 License

This project is for educational and personal use. Ensure compliance with:
- Google Gemini API terms
- Microsoft Edge TTS usage policies  
- Audio file licensing (CC-0, royalty-free, etc.)

---

**🎉 Create professional audiobooks in minutes with AI-powered content generation and cinematic audio design!**