from functools import lru_cache
import requests
import json
import os
import logging
import hashlib
import re
from flask import Flask, request, jsonify, send_from_directory
from tenacity import retry, wait_exponential, stop_after_attempt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = "meta-llama/llama-3.3-8b-instruct:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

app = Flask(__name__, static_folder='.', static_url_path='')

# Simple in-memory cache for AI responses
ai_response_cache = {}

@app.after_request
def add_noindex_header(response):
    response.headers['X-Robots-Tag'] = 'noindex'
    return response 

def create_cache_key(prompt, model):
    """Create a hash-based cache key for AI responses"""
    content = f"{prompt}|{model}"
    return hashlib.md5(content.encode()).hexdigest()

def create_prompt(user_data):
    species = user_data.get('species', '').lower()
    breed = user_data.get('breed', '')
    
    prompt = f"""You are an expert veterinary diagnostic AI specializing in {species} health. 

Based on the following {species} patient data, provide a JSON response with ranked possible diagnoses:

"""
    
    for key, value in user_data.items():
        if value:  # Only include non-empty values
            prompt += f"{key.replace('_', ' ').capitalize()}: {value}\n"
    
    prompt += f"\nConsider breed-specific health predispositions for {breed if breed else 'mixed breed'} {species}."
    
    prompt += """

Please respond with ONLY a valid JSON object in this exact format:
{
  "conditions": [
    {
      "name": "Condition Name",
      "likelihood": 85,
      "explanation": "Brief explanation of why this condition fits the symptoms"
    }
  ],
  "urgent": true,
  "consult": "Recommendation for veterinary consultation",
  "homecare": "Home care suggestions"
}

Provide 1-3 conditions ranked by likelihood percentage. Make sure the JSON is valid and complete."""
    
    return prompt

def extract_json_from_response(text):
    """Extract JSON from response text, handling cases where there might be extra text"""
    text = text.strip()
    
    # Try to find JSON within the text
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        json_str = json_match.group()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # If that fails, try parsing the entire response as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from response: {text}")
        return None

@retry(wait=wait_exponential(multiplier=1, min=2, max=8), stop=stop_after_attempt(3))
def query_openrouter(prompt, use_cache=True):
    # Check cache first
    cache_key = create_cache_key(prompt, OPENROUTER_MODEL)
    if use_cache and cache_key in ai_response_cache:
        logger.info("Using cached response")
        return ai_response_cache[cache_key]
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "Veterinary AI Assistant"
    }
    
    # Remove response_format for this model - it's causing the validation error
    data = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.15,
        "max_tokens": 2000
    }
    
    logger.info(f"Sending request to OpenRouter with model: {OPENROUTER_MODEL}")
    
    response = requests.post(f"{OPENROUTER_BASE_URL}/chat/completions", headers=headers, json=data)
    
    if response.status_code != 200:
        logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
        response.raise_for_status()
    
    result = response.json()
    
    # Cache the response
    if use_cache:
        ai_response_cache[cache_key] = result
        # Simple cache size management - keep only last 100 entries
        if len(ai_response_cache) > 100:
            oldest_key = next(iter(ai_response_cache))
            del ai_response_cache[oldest_key]
    
    return result

def process_response(response):
    if not response or "choices" not in response or not response["choices"]:
        logger.error("Invalid response structure")
        return None
        
    content = response["choices"][0]["message"]["content"]
    logger.info(f"Raw AI response: {content}")
    
    return extract_json_from_response(content)

def get_diagnoses(response):
    if response and "conditions" in response:
        return [{"name": c["name"], "likelihood": c["likelihood"], "explanation": c.get("explanation", "")} for c in response["conditions"]]
    return []

def get_highest_ranked_diagnosis(results):
    if not results:
        return "No diagnosis available"
    top_diagnosis = max(results, key=lambda x: x["likelihood"])
    if len(results) >= 3:
        top_three = sorted(results, key=lambda x: x["likelihood"], reverse=True)[:3]
        diagnoses_str = ', '.join(f"{d['name']} ({d['likelihood']}%)" for d in top_three)
        return f"Top 3 possible diagnoses: {diagnoses_str}"
    return f"{top_diagnosis['name']} ({top_diagnosis['likelihood']}%)"

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/scripts.js')
def serve_scripts():
    return send_from_directory('.', 'scripts.js')

@app.route('/styles.css')
def serve_css():
    return send_from_directory('.', 'styles.css')

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory('images', filename)

@app.route('/diagnose', methods=['POST'])
def diagnose():
    try:
        user_data = request.json
        
        # Validate required fields
        required_fields = ['species', 'age', 'sex', 'symptoms']
        missing_fields = [field for field in required_fields if not user_data.get(field)]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        # Validate species
        species = user_data.get('species', '').lower()
        if species not in ['cat', 'dog']:
            return jsonify({"error": "Species must be either 'cat' or 'dog'"}), 400
        
        prompt = create_prompt(user_data)
        logger.info(f"Generated prompt: {prompt}")
        
        results = []
        queried_models = []
        skipped_models = []
        openrouter_response = None
        
        if OPENROUTER_API_KEY:
            try:
                raw_response = query_openrouter(prompt)
                openrouter_response = process_response(raw_response)
                if openrouter_response:
                    openrouter_diagnoses = get_diagnoses(openrouter_response)
                    results.extend(openrouter_diagnoses)
                    queried_models.append("OpenRouter/Llama-3.3")
                    logger.info(f"Successfully processed OpenRouter response: {openrouter_response}")
                else:
                    skipped_models.append("OpenRouter (response parsing error)")
                    logger.error("Failed to parse OpenRouter response")
            except Exception as e:
                logger.error(f"OpenRouter API error: {str(e)}")
                skipped_models.append(f"OpenRouter (API error: {str(e)})")
        else:
            skipped_models.append("OpenRouter (no API key)")
        
        if not queried_models:
            return jsonify({"error": "No AI models were available to process your request. Please check API configurations.", "skipped_models": skipped_models}), 503
        
        # Create fallback response if parsing failed
        if not openrouter_response:
            openrouter_response = {
                "conditions": [{"name": "Unable to determine", "likelihood": 0, "explanation": "Response parsing failed"}],
                "urgent": False,
                "consult": "Please consult with a veterinarian for proper diagnosis.",
                "homecare": "Monitor your pet and seek professional veterinary advice."
            }
        
        final_diagnosis = get_highest_ranked_diagnosis(results)
        response = {
            "diagnosis": final_diagnosis,
            "conditions": openrouter_response.get("conditions", []),
            "urgent": openrouter_response.get("urgent", False),
            "consult": openrouter_response.get("consult", "Consult with a veterinarian"),
            "homecare": openrouter_response.get("homecare", "Monitor your pet closely"),
            "disclaimer": "This is not professional veterinary advice. Please consult a licensed veterinarian for accurate diagnosis and treatment.",
            "queried_models": queried_models,
            "skipped_models": skipped_models
        }
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in diagnose endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

def query_veterinary_details(diagnosis, species, breed):
    prompt = f"""Provide detailed veterinary information about "{diagnosis}" in {species} (breed: {breed}).

Please respond with ONLY a valid JSON object in this exact format:
{{
  "Overview": "Brief overview of the condition",
  "Symptoms": ["symptom1", "symptom2", "symptom3"],
  "When to see a veterinarian": "When to seek professional help",
  "Causes": "What causes this condition",
  "Risk factors": ["factor1", "factor2"],
  "Complications": "Possible complications",
  "Prevention": "Prevention methods",
  "Treatment options": "Available treatments"
}}

Focus on species-specific and breed-specific considerations where relevant. Make sure the JSON is valid and complete."""
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "Veterinary AI Assistant"
    }
    data = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 2000
    }
    response = requests.post(f"{OPENROUTER_BASE_URL}/chat/completions", headers=headers, json=data)
    response.raise_for_status()
    
    content = response.json()["choices"][0]["message"]["content"]
    return extract_json_from_response(content)

@app.route('/veterinary-details', methods=['POST'])
def veterinary_details():
    try:
        data = request.json
        diagnosis = data.get("diagnosis")
        species = data.get("species", "")
        breed = data.get("breed", "mixed breed")
        
        if not diagnosis:
            return jsonify({"error": "Diagnosis is required"}), 400
        if not species:
            return jsonify({"error": "Species is required"}), 400
        
        queried_models = []
        skipped_models = []
        
        if OPENROUTER_API_KEY:
            try:
                details = query_veterinary_details(diagnosis, species, breed)
                if details:
                    queried_models.append("OpenRouter/Llama-3.3")
                else:
                    details = None
                    skipped_models.append("OpenRouter (parsing error)")
            except Exception as e:
                logger.error(f"Error getting veterinary details: {str(e)}")
                details = None
                skipped_models.append(f"OpenRouter (error: {str(e)})")
        else:
            details = None
            skipped_models.append("OpenRouter (no API key)")
        
        if not queried_models:
            return jsonify({"error": "No AI models available", "skipped_models": skipped_models}), 503
        
        response = {
            "diagnosis": diagnosis,
            "species": species,
            "breed": breed,
            "veterinary_details": details if details else "No details available",
            "queried_models": queried_models,
            "skipped_models": skipped_models
        }
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in veterinary-details endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    missing_keys = []
    available_models = []
    
    if not OPENROUTER_API_KEY:
        missing_keys.append("OPENROUTER_API_KEY")
    else:
        available_models.append("OPENROUTER_API_KEY")
    
    cache_stats = {
        "cached_responses": len(ai_response_cache),
        "cache_enabled": True
    }
    
    if missing_keys:
        return jsonify({
            "status": "error",
            "message": "Service cannot function - no API key configured",
            "missing_keys": missing_keys,
            "cache_stats": cache_stats
        }), 503
    
    return jsonify({
        "status": "healthy",
        "message": "Veterinary AI service is up and running with OpenRouter API key configured",
        "available_models": available_models,
        "cache_stats": cache_stats
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)