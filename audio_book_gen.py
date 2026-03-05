import os
import re
import asyncio
import json
import logging
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
from dotenv import load_dotenv
import google.generativeai as genai
import edge_tts
from pydub import AudioSegment
from pydub.effects import compress_dynamic_range, high_pass_filter
from tqdm.asyncio import tqdm

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class NarrationSegment:
    start_time: float
    end_time: float
    duration: float
    text: str
    visual_description: str
    audio_path: Optional[str] = None

class EdgeTTSWrapper:
    def __init__(self, emotion: str = 'neutral'):
        self.emotion = emotion
        # SSML-free voice configurations with natural voices
        self.voice_configs = {
            'cheerful': {'voice': 'en-US-JennyNeural', 'speed_factor': 1.1},
            'serious': {'voice': 'en-US-DavisNeural', 'speed_factor': 0.85},
            'mystery': {'voice': 'en-US-AriaNeural', 'speed_factor': 0.8},
            'neutral': {'voice': 'en-US-JennyNeural', 'speed_factor': 0.9}
        }
        
        config = self.voice_configs.get(emotion, self.voice_configs['neutral'])
        self.voice = config['voice']
        self.speed_factor = config['speed_factor']

    async def synthesize_with_retry(self, text: str, output_path: str, max_retries: int = 3):
        for attempt in range(max_retries):
            try:
                await self.synthesize(text, output_path)
                return
            except Exception as e:
                wait_time = 2 ** attempt
                logger.warning(f"TTS attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    raise e

    async def synthesize(self, text: str, output_path: str):
        # SSML-free approach using only voice names and post-processing
        try:
            # Use plain voice name (no styles)
            communicate = edge_tts.Communicate(text, self.voice)
            
            # Save to temporary path for post-processing
            temp_path = f"temp_{output_path}"
            await communicate.save(temp_path)
            
            # Apply emotion-based audio processing
            self._apply_emotion_processing(temp_path, output_path)
            
            # Cleanup temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        except Exception as e:
            logger.warning(f"TTS failed: {e}. Retrying...")
            # Fallback - save directly without processing
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(output_path)
    
    def _apply_emotion_processing(self, input_path: str, output_path: str):
        """Apply emotion-based audio processing without SSML"""
        audio = AudioSegment.from_mp3(input_path)
        
        # Apply speed adjustment based on emotion
        if self.speed_factor != 1.0:
            # Speed up or slow down
            if self.speed_factor > 1.0:
                audio = audio.speedup(playback_speed=self.speed_factor)
            else:
                # Slow down by changing frame rate
                audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * self.speed_factor)})
                audio = audio.set_frame_rate(audio.frame_rate)
        
        # Apply emotion-specific audio effects
        if self.emotion == 'cheerful':
            # Brighter, more energetic
            audio = audio + 1  # Slight volume boost
            audio = audio.high_pass_filter(100)  # Enhance clarity
        elif self.emotion == 'serious':
            # Deeper, more authoritative
            audio = audio - 2  # Slight volume reduction
            audio = audio.low_pass_filter(8000)  # Warmer tone
        elif self.emotion == 'mystery':
            # Darker, more atmospheric
            audio = audio - 3  # Lower volume
            audio = audio.low_pass_filter(6000)  # Muffled effect
        
        # Export processed audio
        audio.export(output_path, format="mp3")

class CinematicAudioProcessor:
    def __init__(self):
        self.sounds_dir = Path("sounds")
        self.ambience_files = self._discover_ambience_files()

    def _discover_ambience_files(self):
        """Dynamically discover ambience files from sounds folder"""
        files = {}
        if self.sounds_dir.exists():
            for file in self.sounds_dir.glob("*.mp3"):
                files[file.stem] = str(file)
            for file in self.sounds_dir.glob("*.wav"):
                files[file.stem] = str(file)
        logger.info(f"Discovered {len(files)} ambience files: {list(files.keys())}")
        return files

    def load_ambience_track(self, filename: str) -> AudioSegment:
        """Load and prepare ambience track"""
        if filename in self.ambience_files:
            logger.info(f"Loading ambience file: {filename}")
            return AudioSegment.from_file(self.ambience_files[filename])
        else:
            logger.warning(f"Ambience file '{filename}' not found")
            return AudioSegment.silent(duration=5000)

    def create_segment_based_mix(self, segments: List[NarrationSegment], narration_path: str, output_path: str):
        """Create cinematic mix based on Gemini-generated segments"""
        logger.info("Creating segment-based cinematic mix")
        
        logger.info("🎵 Loading and processing narration...")
        # Load narration
        narration = AudioSegment.from_mp3(narration_path)
        narration = self.apply_professional_processing(narration, is_narration=True)
        
        # Create background track
        background = AudioSegment.silent(duration=len(narration))
        
        # Process each segment
        logger.info("🎬 Processing background audio segments...")
        for i, segment in enumerate(tqdm(segments, desc="Background Audio")):
            if segment.audio_path:
                logger.info(f"Segment {i+1}: '{segment.audio_path}' for '{segment.visual_description}' ({segment.start_time:.1f}s - {segment.end_time:.1f}s)")
                
                # Load segment audio
                segment_audio = self.load_ambience_track(segment.audio_path)
                
                if len(segment_audio) > 1000:  # Valid audio file
                    # Calculate positions in milliseconds
                    start_ms = int(segment.start_time * 1000)
                    end_ms = int(segment.end_time * 1000)
                    duration_ms = end_ms - start_ms
                    
                    # Ensure we don't exceed narration length
                    if start_ms < len(narration):
                        end_ms = min(end_ms, len(narration))
                        duration_ms = end_ms - start_ms
                        
                        # Prepare segment audio
                        if len(segment_audio) < duration_ms:
                            # Loop if too short
                            loops = (duration_ms // len(segment_audio)) + 1
                            segment_audio = segment_audio * loops
                        
                        # Trim to exact duration
                        segment_audio = segment_audio[:duration_ms]
                        
                        # Apply processing and volume
                        segment_audio = self.apply_professional_processing(segment_audio)
                        segment_audio = segment_audio - 20  # -20dB for background
                        
                        # Fade in/out for smooth transitions
                        fade_duration = min(1000, duration_ms // 4)
                        segment_audio = segment_audio.fade_in(fade_duration).fade_out(fade_duration)
                        
                        # Overlay on background
                        background = background.overlay(segment_audio, position=start_ms)
        
        logger.info("🎚️ Applying dynamic ducking...")
        # Apply dynamic ducking
        background = self.apply_dynamic_ducking(narration, background)
        
        logger.info("🎧 Creating final mix...")
        # Final mix
        final_audio = narration.overlay(background)
        
        # Export
        logger.info("💾 Exporting final audiobook...")
        final_audio.export(output_path, format="mp3", bitrate="192k", parameters=["-ar", "44100"])
        logger.info(f"Segment-based audiobook exported to {output_path}")

    def apply_dynamic_ducking(self, narration: AudioSegment, background: AudioSegment) -> AudioSegment:
        """Apply dynamic ducking based on speech detection"""
        from pydub.silence import detect_nonsilent
        
        nonsilent_ranges = detect_nonsilent(narration, min_silence_len=500, silence_thresh=-40)
        ducked_background = background - 8  # Pause level
        
        for start_ms, end_ms in nonsilent_ranges:
            speech_segment = background[start_ms:end_ms] - 18  # Speech level
            ducked_background = (
                ducked_background[:start_ms] + 
                speech_segment + 
                ducked_background[end_ms:]
            )
        
        return ducked_background

    def apply_professional_processing(self, audio: AudioSegment, is_narration: bool = False) -> AudioSegment:
        """Apply professional audio processing"""
        if is_narration:
            audio = compress_dynamic_range(audio, threshold=-20.0, ratio=3.0)
            audio = high_pass_filter(audio, 120)
            audio = audio.normalize(headroom=1.0)
        else:
            audio = audio.low_pass_filter(10000)
            audio = audio.high_pass_filter(100)
        return audio

class AudioBookGenerator:
    def __init__(self, gemini_api_key: str = None):
        api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("Gemini API key required. Set GEMINI_API_KEY environment variable or pass as parameter.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.audio_processor = CinematicAudioProcessor()
        self.last_generated_segments = []

    def calculate_target_words(self, duration: int) -> int:
        return int(duration * 165)

    async def generate_structured_content(self, topic: str, duration: int = 10, emotion: str = 'neutral') -> List[NarrationSegment]:
        """Generate structured content with audio cues using Gemini"""
        available_sounds = list(self.audio_processor.ambience_files.keys())
        
        # Support chunked generation for long durations
        if duration > 15:
            logger.info(f"Long duration ({duration} min) detected, using chunked generation")
            return await self._generate_chunked_content(topic, duration, emotion, available_sounds)
        else:
            return await self._generate_single_chunk(topic, duration, emotion, available_sounds, 0.0, False, None)
    
    async def _generate_single_chunk(self, topic: str, duration: int, emotion: str, available_sounds: List[str], start_offset: float, is_continuation: bool = False, previous_context: str = None) -> List[NarrationSegment]:
        """Generate a single chunk of content"""
        word_count = self.calculate_target_words(duration)
        
        logger.info(f"Generating chunk - Target: {word_count} words, Duration: {duration} min")
        
        if is_continuation and previous_context:
            continuation_instruction = f"\n\nIMPORTANT: This is a CONTINUATION of an existing audiobook. The previous section ended with: '{previous_context}'. Continue the narrative naturally from where it left off. DO NOT repeat the introduction or restart the story."
        else:
            continuation_instruction = ""
        
        prompt = f"""You are an expert audiobook producer. Create a structured audiobook script about "{topic}" with specific audio cues.{continuation_instruction}

AVAILABLE AUDIO FILES: {available_sounds}

Requirements:
1. Target: ~{word_count} words (±5%) for {duration} minutes
2. Emotion: {emotion}
3. Create 8-12 narrative segments
4. Each segment should specify which audio file to use as background

Return ONLY a JSON array with this exact structure:
[
  {{
    "start_time": {start_offset},
    "end_time": {start_offset + 45.2},
    "duration": 45.2,
    "text": "The story begins in a mystical forest where ancient trees whispered secrets...",
    "visual_description": "mystical forest scene with ancient trees",
    "audio_path": "forest-nature-322637"
  }}
]

Rules:
- Use ONLY audio files from the available list
- Match audio to the scene content
- Ensure segments flow naturally
- Total duration should be approximately {duration * 60} seconds
- Each segment text should be concise (25-75 words)
- Start_time of next segment = end_time of previous segment"""

        # Retry logic with exponential backoff
        for attempt in range(3):
            try:
                response = await self.model.generate_content_async(prompt)
                break
            except Exception as e:
                logger.warning(f"Gemini attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise RuntimeError("Gemini failed after 3 attempts")
        
        try:
            # Extract JSON from response
            json_text = response.text.strip()
            if json_text.startswith('```json'):
                json_text = json_text[7:-3]
            elif json_text.startswith('```'):
                json_text = json_text[3:-3]
            
            segments_data = json.loads(json_text)
            
            # Convert to NarrationSegment objects
            segments = []
            for seg_data in segments_data:
                segment = NarrationSegment(
                    start_time=seg_data['start_time'],
                    end_time=seg_data['end_time'],
                    duration=seg_data['duration'],
                    text=seg_data['text'],
                    visual_description=seg_data['visual_description'],
                    audio_path=seg_data.get('audio_path')
                )
                segments.append(segment)
            
            logger.info(f"Generated {len(segments)} structured segments")
            return segments
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response was: {response.text}")
            raise ValueError("Failed to generate structured content")
    
    async def _generate_chunked_content(self, topic: str, total_duration: int, emotion: str, available_sounds: List[str]) -> List[NarrationSegment]:
        """Generate content in chunks for long durations"""
        chunk_size = 8  # 8 minutes per chunk
        chunks_needed = (total_duration + chunk_size - 1) // chunk_size  # Ceiling division
        
        logger.info(f"Generating {chunks_needed} chunks of {chunk_size} minutes each")
        
        all_segments = []
        current_start_time = 0.0
        previous_context = None
        
        for chunk_idx in range(chunks_needed):
            # Calculate duration for this chunk
            remaining_duration = total_duration - (chunk_idx * chunk_size)
            chunk_duration = min(chunk_size, remaining_duration)
            
            logger.info(f"Generating chunk {chunk_idx + 1}/{chunks_needed} (duration: {chunk_duration} min)")
            
            # Determine if this is a continuation
            is_continuation = chunk_idx > 0
            
            # Generate chunk
            chunk_segments = await self._generate_single_chunk(
                topic, chunk_duration, emotion, available_sounds, current_start_time, is_continuation, previous_context
            )
            print(chunk_segments)
            # Adjust timing for subsequent chunks
            if chunk_segments:
                # Extract context from last segment for next chunk
                last_segment_text = chunk_segments[-1].text
                words = last_segment_text.split()
                previous_context = ' '.join(words[-15:])  # Last 15 words as context
                
                # Update start time for next chunk
                current_start_time = chunk_segments[-1].end_time
                all_segments.extend(chunk_segments)
        
        logger.info(f"Generated total of {len(all_segments)} segments across {chunks_needed} chunks")
        return all_segments

    def preprocess_text(self, text: str, emotion: str = 'neutral') -> str:
        """Enhance text for natural conversational speech"""
        # Clean formatting
        clean_text = re.sub(r'\*\*\*|###|\*\*|\*|\[.*?\]|\(.*?\)', '', text)
        clean_text = re.sub(r'\n+', ' ', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Add natural conversational elements based on emotion
        clean_text = self.make_conversational(clean_text, emotion)
        
        return clean_text
    
    def make_conversational(self, text: str, emotion: str = 'neutral') -> str:
        """Transform text for natural speech without SSML"""
        # Add natural pauses with punctuation
        text = re.sub(r'([.!?])\s+', r'\1... ', text)  # Longer pauses
        text = re.sub(r'([,;:])\s+', r'\1 ', text)      # Natural comma pauses
        
        # Add conversational elements based on emotion
        if emotion == 'cheerful':
            # Add enthusiasm markers
            text = re.sub(r'\b(amazing|incredible|wonderful)\b', r'\1!', text, flags=re.IGNORECASE)
            text = re.sub(r'([.])\s+', r'\1 Well, ', text, count=2)  # Add conversational connectors
        elif emotion == 'serious':
            # Add authoritative markers
            text = re.sub(r'\b(important|crucial|significant)\b', r'\1,', text, flags=re.IGNORECASE)
            text = re.sub(r'([.])\s+', r'\1 Indeed, ', text, count=1)
        elif emotion == 'mystery':
            # Add suspenseful markers
            text = re.sub(r'\b(suddenly|quietly|secretly)\b', r'\1...', text, flags=re.IGNORECASE)
            text = re.sub(r'([.])\s+', r'\1 But then... ', text, count=1)
        
        # Break very long sentences naturally
        sentences = text.split('.')
        processed_sentences = []
        
        for sentence in sentences:
            words = sentence.split()
            if len(words) > 20:  # Long sentence
                # Find natural break point
                break_words = ['and', 'but', 'so', 'because', 'while', 'when', 'where', 'which']
                for i, word in enumerate(words):
                    if word.lower() in break_words and i > 8:
                        words.insert(i, '...')
                        break
            processed_sentences.append(' '.join(words))
        
        return '.'.join(processed_sentences)

    async def generate_speech(self, text: str, output_path: str, emotion: str = 'neutral'):
        """Generate speech with emotion-based voice and style"""
        tts = EdgeTTSWrapper(emotion)
        await tts.synthesize_with_retry(text, output_path)
    
    async def generate_segment_speeches(self, segments: List[NarrationSegment], emotion: str = 'neutral') -> List[str]:
        """Generate speech for all segments simultaneously"""
        logger.info(f"Generating speech for {len(segments)} segments simultaneously")
        
        # Create tasks for parallel generation
        tasks = []
        segment_paths = []
        
        for i, segment in enumerate(segments):
            segment_path = f"segment_{i+1}.mp3"
            segment_paths.append(segment_path)
            
            clean_text = self.preprocess_text(segment.text, emotion)
            task = self.generate_speech(clean_text, segment_path, emotion)
            tasks.append(task)
        
        # Execute all TTS tasks simultaneously with progress bar
        logger.info("🎙️ Generating speech for all segments...")
        await tqdm.gather(*tasks, desc="TTS Generation")
        logger.info(f"All {len(segments)} segment speeches generated")
        
        return segment_paths
    
    def combine_segment_audios(self, segment_paths: List[str], output_path: str):
        """Combine all segment audio files into one continuous narration"""
        logger.info("Combining segment audio files")
        
        combined_audio = AudioSegment.empty()
        
        logger.info("🔗 Combining audio segments...")
        for i, path in enumerate(tqdm(segment_paths, desc="Combining Audio")):
            if os.path.exists(path):
                segment_audio = AudioSegment.from_mp3(path)
                combined_audio += segment_audio
                logger.info(f"Added segment {i+1}: {len(segment_audio)/1000:.1f}s")
                
                # Cleanup individual segment file
                os.remove(path)
            else:
                logger.warning(f"Segment file {path} not found")
        
        # Export combined narration
        logger.info("💾 Exporting combined narration...")
        combined_audio.export(output_path, format="mp3")
        logger.info(f"Combined narration exported: {len(combined_audio)/1000:.1f}s total")

    async def create_audiobook(self, topic: str, duration: int = 10, emotion: str = 'neutral') -> dict:
        """Create cinematic audiobook with structured segments"""
        logger.info(f"Creating structured audiobook - Topic: {topic}, Duration: {duration}min, Emotion: {emotion}")
        
        try:
            logger.info(f"🎬 Creating audiobook: '{topic}' ({duration} min, {emotion})")
            
            # Generate structured content
            logger.info("📝 Generating structured content with Gemini...")
            segments = await self.generate_structured_content(topic, duration, emotion)
            print(segments)
            logger.info(f"✅ Generated {len(segments)} segments")
            
            # File paths
            safe_topic = re.sub(r'[^\w\s-]', '', topic).strip().replace(' ', '_')
            narration_path = f"{safe_topic}_narration.mp3"
            final_audio_path = f"{safe_topic}_audiobook.mp3"
            
            # Generate speech for all segments simultaneously
            segment_paths = await self.generate_segment_speeches(segments, emotion)
            logger.info("✅ All segment speeches generated")
            
            # Combine all segment audio files into one continuous narration
            self.combine_segment_audios(segment_paths, narration_path)
            logger.info("✅ Audio segments combined")
            
            # Create segment-based mix with background audio
            self.audio_processor.create_segment_based_mix(segments, narration_path, final_audio_path)
            logger.info("✅ Final cinematic mix completed")
            
            # Get combined text for response
            full_text = " ".join([self.preprocess_text(seg.text, emotion) for seg in segments])
            
            # Cleanup
            if os.path.exists(narration_path):
                os.remove(narration_path)
            
            # Store segments for API access
            self.last_generated_segments = segments
            
            logger.info(f"🎉 Audiobook '{topic}' completed successfully!")
            return {
                'success': True,
                'plain_text': full_text,
                'audio_path': final_audio_path,
                'topic': topic,
                'duration': duration,
                'emotion': emotion,
                'segments': len(segments),
                'word_count': len(full_text.split())
            }
            
        except Exception as e:
            logger.error(f"Audiobook creation failed: {e}")
            return {'success': False, 'error': str(e)}

# CLI Usage
async def main():
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            api_key = input("Enter your Gemini API key: ")
        
        topic = input("Enter audiobook topic: ")
        duration = int(input("Enter duration in minutes (default 10): ") or 10)
        emotion = input("Enter emotion (cheerful/serious/mystery/neutral, default neutral): ") or 'neutral'
        
        # Start timer
        start_time = time.time()
        print(f"\n⏱️ Starting generation at {time.strftime('%H:%M:%S')}...")
        
        generator = AudioBookGenerator(api_key)
        result = await generator.create_audiobook(topic, duration, emotion)
        
        # Calculate generation time
        end_time = time.time()
        generation_time = end_time - start_time
        minutes = int(generation_time // 60)
        seconds = int(generation_time % 60)
        
        if result['success']:
            print(f"\n✅ Structured audiobook generated!")
            print(f"⏱️ Generation time: {minutes}m {seconds}s")
            print(f"Topic: {result['topic']}")
            print(f"Emotion: {result['emotion']}")
            print(f"Segments: {result['segments']}")
            print(f"Word count: {result['word_count']}")
            print(f"Audio saved to: {result['audio_path']}")
            
            play_audio = input("\nPlay audio now? (y/n): ").lower() == 'y'
            if play_audio:
                os.startfile(result['audio_path'])
        else:
            print(f"❌ Error: {result['error']}")
            print(f"⏱️ Failed after: {minutes}m {seconds}s")
            
    except Exception as e:
        logger.error(f"CLI error: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())