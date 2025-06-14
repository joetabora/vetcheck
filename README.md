# AI Pet Symptom Analyzer

This is a web-based AI-powered veterinary symptom analysis tool designed to provide pet owners with preliminary diagnostic insights based on their pet's symptoms. It uses the OpenRouter AI model for both diagnosis and detailed condition information. The project is built with Flask (Python) for the backend and JavaScript for the frontend, running in a Docker container.

**Note**: This tool is not a substitute for professional veterinary advice. Always consult a licensed veterinarian for accurate diagnosis and treatment.

## Features
- **Pet-Specific Symptom Analysis**: Users input pet species (dogs/cats), breed, age, sex, medical history, symptoms, and additional info to receive ranked possible diagnoses with likelihoods, urgency indicators, veterinary consultation advice, and home care suggestions.
- **AI-Powered Veterinary Details**: Retrieves detailed veterinary information for the top diagnosis using the OpenRouter AI model, returned as JSON for seamless UI rendering.
- **Breed-Specific Analysis**: Supports 25+ dog breeds and 24+ cat breeds with breed-specific diagnostic considerations.
- **Responsive UI**: Chat-style interface with auto-scrolling and result categorization (green/yellow/red).
- **Caching**: Uses `lru_cache` to cache AI responses for repeated queries, improving performance and reducing API usage.

## Tech Stack
- **Backend**: Flask, CLI, Python 3.11
- **Frontend**: HTML, CSS, JavaScript (Bootstrap 4)
- **AI**: OpenRouter AI (`meta-llama/llama-3.3-8b-instruct:free`)
- **Containerization**: None
- **Dependencies**: Managed via `requirements.txt`

## Project Structure
```
ai-pet-symptom-analyzer/
├── README.md            # Project documentation
├── compose.yml          # Docker Compose
└── Main
    ├── app.py               # Flask application with API endpoints
    ├── requirements.txt     # Python dependencies
    ├── scripts.js           # Frontend JavaScript logic with pet-specific forms
    ├── index.html           # Main page with veterinary-focused UI
    ├── styles.css           # Custom CSS for the UI
    └── Dockerfile           # Dockerfile
```

