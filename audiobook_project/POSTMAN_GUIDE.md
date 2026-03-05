# Postman Testing Guide for Audiobook API

## Setup Instructions

### 1. Import Collection
1. Open Postman
2. Click **Import** button
3. Select `Audiobook_API.postman_collection.json`
4. Collection will appear in your workspace

### 2. Set Environment Variables
- `base_url`: `http://localhost:8000`
- `filename`: Will be set from API response

## API Endpoints

### 1. Generate Audiobook
**Method:** POST  
**URL:** `{{base_url}}/api/generate/`

**Request Body:**
```json
{
    "topic": "The History of Space Exploration",
    "duration": 5,
    "emotion": "serious",
    "gemini_api_key": "your_actual_api_key"
}
```

**Response:**
```json
{
    "success": true,
    "audio_url": "http://localhost:8000/media/The_History_of_Space_Exploration_audiobook.mp3",
    "topic": "The History of Space Exploration",
    "duration": 5,
    "emotion": "serious",
    "segments": 8,
    "word_count": 825,
    "generation_time": "1m 45s"
}
```

### 2. Download Audiobook
**Method:** GET  
**URL:** `{{base_url}}/api/download/{{filename}}/`

## Test Scenarios

### Scenario 1: Basic Generation
1. Use "Generate Audiobook" request
2. Replace `gemini_api_key` with your actual key
3. Send request
4. Copy filename from `audio_url` in response
5. Use "Download Audiobook" to get the file

### Scenario 2: Different Emotions
- **Cheerful:** "Amazing Animal Adventures"
- **Mystery:** "Ancient Egyptian Mysteries"  
- **Serious:** "The History of Space Exploration"
- **Neutral:** Any topic

### Scenario 3: Error Testing
- Use "Invalid Request - Missing API Key"
- Should return 400 Bad Request

## Parameters

| Field | Type | Required | Options |
|-------|------|----------|---------|
| topic | string | Yes | Any descriptive text |
| duration | integer | Yes | 1-60 minutes |
| emotion | string | Yes | cheerful, serious, mystery, neutral |
| gemini_api_key | string | Yes | Your Gemini API key |

## Expected Response Times
- **Short (1-5 min):** 30s - 2m
- **Medium (6-10 min):** 1m - 3m  
- **Long (11+ min):** 2m - 5m

## Troubleshooting

### Common Errors
1. **400 Bad Request:** Missing required fields
2. **500 Internal Server Error:** Invalid API key or generation failure
3. **404 Not Found:** File doesn't exist for download

### Tips
1. Keep duration under 10 minutes for faster testing
2. Use descriptive topics for better content
3. Save successful responses to reuse filenames