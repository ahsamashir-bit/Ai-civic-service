import json
import requests
import re
from textblob import TextBlob
import database

def analyze_complaint(title, description):
    """
    Main entry point for analyzing a complaint.
    Attempts to use configured LLM APIs (OpenAI or Gemini) first.
    Falls back to a high-quality Local NLP / Heuristic Engine if no API keys are present or if they fail.
    """
    # 1. Retrieve API Keys from database settings
    openai_key = database.get_setting("openai_api_key", "").strip()
    gemini_key = database.get_setting("gemini_api_key", "").strip()
    
    # Check if they are placeholder values
    if openai_key == "your_key_here" or openai_key == "openai_api_key_here":
        openai_key = ""
    if gemini_key == "your_key_here" or gemini_key == "gemini_api_key_here":
        gemini_key = ""

    prompt = f"""
    You are an AI civic assistant. Classify and analyze the following local service complaint.
    Title: {title}
    Description: {description}

    You MUST respond with a JSON object matching exactly this schema:
    {{
        "category": "Roads & Traffic" | "Water & Sanitation" | "Waste Management" | "Electrical & Lighting" | "Parks & Public Spaces" | "Public Safety",
        "priority": "Low" | "Medium" | "High" | "Critical",
        "urgency_score": 1-100 (integer representing priority scale, 1 is negligible, 100 is life-threatening emergency),
        "reasoning": "A concise paragraph explaining the classification and priority decision based on hazards, utility outages, public safety, or accessibility",
        "suggested_steps": "Numbered steps for the city resolution team (1. Step one, 2. Step two...)",
        "estimated_hours": 4 | 12 | 48 | 120 (SLA target resolution hours: Critical=4, High=12, Medium=48, Low=120),
        "key_entities": ["list", "of", "3-5", "extracted", "keywords", "like", "pothole", "hydrant", "etc"]
    }}
    """

    # 2. Try Gemini API if key is present
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            response = requests.post(url, headers=headers, json=payload, timeout=8)
            if response.status_code == 200:
                resp_json = response.json()
                text_content = resp_json['candidates'][0]['content']['parts'][0]['text']
                # Extract JSON from block if needed
                json_match = re.search(r'\{.*\}', text_content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
                return json.loads(text_content)
        except Exception as e:
            print(f"Gemini API execution failed: {e}. Falling back...")

    # 3. Try OpenAI API if key is present
    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a precise JSON classifier for municipal complaints."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            response = requests.post(url, headers=headers, json=payload, timeout=8)
            if response.status_code == 200:
                resp_json = response.json()
                text_content = resp_json['choices'][0]['message']['content']
                return json.loads(text_content)
        except Exception as e:
            print(f"OpenAI API execution failed: {e}. Falling back...")

    # 4. Fallback to Local Heuristic & NLP Engine
    return analyze_heuristically(title, description)


def analyze_heuristically(title, description):
    """
    A smart rule-based and NLP analyzer that processes text locally.
    Uses keyword matching, sentiment analysis (via TextBlob), and heuristics.
    """
    combined_text = f"{title} {description}".lower()
    
    # 1. Category Detection
    category_scores = {
        "Roads & Traffic": 0,
        "Water & Sanitation": 0,
        "Waste Management": 0,
        "Electrical & Lighting": 0,
        "Parks & Public Spaces": 0,
        "Public Safety": 0
    }
    
    keywords = {
        "Roads & Traffic": ["pothole", "street", "road", "asphalt", "pavement", "sidewalk", "lane", "crosswalk", "swerve", "traffic", "sign", "marking", "paving", "curb", "accident"],
        "Water & Sanitation": ["water", "leak", "gush", "hydrant", "pipe", "sewer", "drain", "flood", "pool", "clog", "utility", "burst", "waterway", "drainage", "overflow"],
        "Waste Management": ["garbage", "trash", "waste", "dump", "tire", "mattress", "litter", "recycling", "bin", "rodent", "raccoon", "debris", "fly-tipping", "dumping", "rubbish"],
        "Electrical & Lighting": ["light", "dark", "bulb", "lantern", "electrical", "grid", "power", "wire", "pole", "spark", "transformer", "electricity", "outage", "blackout", "circuit"],
        "Parks & Public Spaces": ["park", "playground", "swing", "tree", "branch", "garden", "lawn", "grass", "bench", "recreation", "trail", "pathway", "foliage", "shrubbery"],
        "Public Safety": ["safety", "crime", "theft", "break-in", "security", "threat", "weapon", "fire", "danger", "hazard", "hiss", "animals", "aggressive", "harassment", "vandalism", "graffiti"]
    }
    
    for category, words in keywords.items():
        for word in words:
            # Add score based on occurrences
            occurrences = combined_text.count(word)
            category_scores[category] += occurrences * 2
            
    # Select category with max score, default to Roads & Traffic
    category = max(category_scores, key=category_scores.get)
    if category_scores[category] == 0:
        # Default fallback by common topics
        category = "Roads & Traffic"

    # 2. Sentiment Analysis (NLP Component)
    sentiment_score = 0.0
    try:
        blob = TextBlob(description)
        sentiment_score = blob.sentiment.polarity  # -1.0 to 1.0
    except Exception:
        pass

    # 3. Priority and Urgency Heuristic
    # Keywords indicating emergency
    critical_words = ["spark", "fire", "emergency", "immediate", "child", "school", "hazard", "gush", "flood", "swerving", "accident", "fatal", "injury", "broken bone", "bleeding"]
    high_words = ["unsafe", "block", "wheelchair", "darkness", "consecutive", "broken swing", "rodent", "aggressive", "fallen", "leak", "clogged"]
    
    critical_hits = sum(1 for w in critical_words if w in combined_text)
    high_hits = sum(1 for w in high_words if w in combined_text)
    
    # Calculate base score from sentiment and keywords
    # Negative sentiment increases urgency
    base_urgency = 50 - int(sentiment_score * 25)
    
    # Boost urgency based on keyword hits
    base_urgency += (critical_hits * 15) + (high_hits * 8)
    
    # Cap score
    base_urgency = max(10, min(99, base_urgency))
    
    # Map to priority levels
    if base_urgency >= 85 or critical_hits >= 1:
        priority = "Critical"
        estimated_hours = 4
    elif base_urgency >= 65 or high_hits >= 1:
        priority = "High"
        estimated_hours = 12
    elif base_urgency >= 45:
        priority = "Medium"
        estimated_hours = 48
    else:
        priority = "Low"
        estimated_hours = 120

    # 4. Extract Key Entities (Simple tokenization filtering)
    cleaned_text = re.sub(r'[^\w\s]', '', combined_text)
    tokens = cleaned_text.split()
    stop_words = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "of", "to", "in", "on", "at", "for", "with", "there", "it", "this", "that", "causes", "causing"}
    candidates = [token for token in tokens if token not in stop_words and len(token) > 3]
    
    # Take top unique candidates from the keywords matching category
    matched_candidates = [c for c in candidates if c in keywords[category]]
    unique_candidates = list(dict.fromkeys(matched_candidates + candidates))[:4]

    # 5. Dynamic Reasoning Generation
    hazards = {
        "Roads & Traffic": "vehicular wear, transportation lane obstruction, or potential driver hazards",
        "Water & Sanitation": "utility supply leakage, drainage blockages, or clean water wastage issues",
        "Waste Management": "sanitary concerns, sidewalk clutter, or public pest attraction risks",
        "Electrical & Lighting": "darkened public pathways, local electrical failure, or active safety risks",
        "Parks & Public Spaces": "recreational safety issues, pathway accessibility blocks, or park wear",
        "Public Safety": "active safety threats, dangerous animal interactions, or neighborhood security concerns"
    }
    
    reasoning = f"AI classified this report under '{category}' with a '{priority}' priority level. "
    reasoning += f"This decision was guided by text patterns suggesting {hazards[category]}. "
    if priority in ["Critical", "High"]:
        reasoning += f"The description indicates heightened urgency due to keywords indicating active risk or critical infrastructure impairment."
    else:
        reasoning += "The issue is determined to be non-life-threatening, suitable for scheduling within standard maintenance timelines."

    # 6. Suggested Action Steps
    steps_templates = {
        "Roads & Traffic": [
            "1. Dispatch an infrastructure crew to assess structural pavement depth.",
            "2. Place warning barriers or temporary visual indicators for motorists.",
            "3. Prepare asphalt/marking mixture and execute structural restoration."
        ],
        "Water & Sanitation": [
            "1. Notify the municipal plumbing and hydraulics dispatch unit.",
            "2. Map local supply valves and inspect pressure lines for leakage.",
            "3. Clear structural blocks or repair pipe integrity immediately."
        ],
        "Waste Management": [
            "1. Dispatch municipal heavy garbage collector vehicle to coordinates.",
            "2. Retrieve and load illegal debris/waste for environmental disposal.",
            "3. Sanitize the local area and audit CCTV logs for illegal dumping."
        ],
        "Electrical & Lighting": [
            "1. Signal utility technicians to inspect nearby electrical terminals.",
            "2. Run diagnostics on local switches, photo-electric sensors, and lamps.",
            "3. Replace bulb components or restore grid breaker connections safely."
        ],
        "Parks & Public Spaces": [
            "1. Send the public parks maintenance team to the scene.",
            "2. Cordon off damaged play area or broken pathways.",
            "3. Perform woodcutting, structural repair, or equipment replacement."
        ],
        "Public Safety": [
            "1. Inform city wardens, animal control, or transit patrols.",
            "2. Dispatch an officer/technician to evaluate active hazards or security issues.",
            "3. Clear hazards and advise local residents on resolution status."
        ]
    }
    
    suggested_steps = "\n".join(steps_templates[category])

    return {
        "category": category,
        "priority": priority,
        "urgency_score": base_urgency,
        "reasoning": reasoning,
        "suggested_steps": suggested_steps,
        "estimated_hours": estimated_hours,
        "key_entities": unique_candidates
    }
