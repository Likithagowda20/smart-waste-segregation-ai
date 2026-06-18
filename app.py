import streamlit as st
from PIL import Image
import numpy as np
from typing import Dict, List, Tuple
import requests
import json
import os

# Page configuration
st.set_page_config(
    page_title="Smart Waste Segregation",
    layout="centered",
    page_icon="♻️"
)

# IBM watsonx.ai Configuration
IBM_API_KEY = os.getenv("IBM_API_KEY", "")  # Set your IBM API key in environment
IBM_PROJECT_ID = os.getenv("IBM_PROJECT_ID", "")  # Set your project ID
IBM_URL = "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"

# Knowledge Base - Waste disposal guidelines
KNOWLEDGE_BASE = {
    "organic": {
        "items": [
            "food scraps", "fruit peels", "vegetable waste", "coffee grounds", "tea bags",
            "eggshells", "bread", "rice", "pasta", "paper towels", "napkins",
            "cardboard", "newspaper", "leaves", "grass clippings", "flowers",
            "wood chips", "sawdust", "cotton fabric", "wool", "hair", "fur",
            "banana", "apple", "orange", "potato", "tomato", "lettuce", "carrot"
        ],
        "keywords": [
            "food", "fruit", "vegetable", "peel", "core", "scraps", "organic",
            "paper", "cardboard", "compost", "biodegradable", "natural", "plant",
            "wood", "cotton", "wool", "leaf", "grass", "flower"
        ],
        "guidelines": "♻️ Organic waste decomposes naturally and can be composted. Keep it clean and dry for best results.",
        "tips": [
            "✓ Compost in green bin",
            "✓ Keep waste dry and clean",
            "✓ Chop large items for faster decomposition",
            "✓ Mix green and brown materials"
        ]
    },
    "recyclable": {
        "items": [
            "plastic bottles", "plastic containers", "PET plastic", "HDPE plastic",
            "glass bottles", "glass jars", "aluminum cans", "tin cans", "steel cans",
            "metal lids", "aluminum foil", "clean paper", "magazines", "catalogs",
            "office paper", "cardboard boxes", "milk cartons", "juice boxes",
            "clean packaging", "bubble wrap", "styrofoam", "plastic bags",
            "bottle", "can", "jar", "container"
        ],
        "keywords": [
            "plastic", "bottle", "container", "glass", "jar", "aluminum", "metal",
            "can", "tin", "steel", "paper", "magazine", "catalog", "packaging",
            "recyclable", "recycle", "PET", "HDPE", "carton", "foil"
        ],
        "guidelines": "🔄 Rinse containers before recycling. Remove caps and lids. Flatten cardboard to save space.",
        "tips": [
            "✓ Rinse containers thoroughly",
            "✓ Remove caps and lids",
            "✓ Flatten cardboard boxes",
            "✓ Keep materials dry and clean"
        ]
    },
    "hazardous": {
        "items": [
            "batteries", "lithium batteries", "car batteries", "electronics", "phones",
            "computers", "TVs", "monitors", "light bulbs", "fluorescent tubes",
            "LED bulbs", "paint", "chemicals", "pesticides", "fertilizers",
            "motor oil", "antifreeze", "cleaning products", "bleach", "ammonia",
            "medicines", "pills", "syringes", "thermometers", "smoke detectors",
            "battery", "phone", "laptop", "tablet", "charger"
        ],
        "keywords": [
            "battery", "batteries", "electronic", "phone", "computer", "laptop",
            "tablet", "TV", "monitor", "bulb", "light", "paint", "chemical",
            "pesticide", "oil", "medicine", "pill", "toxic", "hazardous",
            "dangerous", "bleach", "ammonia", "cleaner"
        ],
        "guidelines": "⚠️ NEVER mix hazardous waste with regular waste. Contact local waste authorities for proper disposal.",
        "tips": [
            "⚠️ Handle with care",
            "⚠️ Store safely until disposal",
            "⚠️ Contact local hazardous waste facility",
            "⚠️ Never mix with regular waste"
        ]
    }
}

def classify_with_ibm_ai(item_text: str) -> Tuple[str, str, float]:
    """Classify waste using IBM watsonx.ai Granite model"""
    
    if not IBM_API_KEY or not IBM_PROJECT_ID:
        # Fallback to local classification if API not configured
        return classify_waste_local(item_text)
    
    try:
        # Prepare the prompt for IBM Granite
        prompt = f"""You are an expert waste management AI. Classify this item into ONE category: ORGANIC, RECYCLABLE, or HAZARDOUS.

Item: {item_text}

Respond in this exact format:
CATEGORY: [ORGANIC/RECYCLABLE/HAZARDOUS]
CONFIDENCE: [0.0-1.0]
REASON: [brief explanation]"""

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {IBM_API_KEY}"
        }
        
        body = {
            "input": prompt,
            "parameters": {
                "decoding_method": "greedy",
                "max_new_tokens": 150,
                "temperature": 0.3,
                "stop_sequences": ["END"]
            },
            "model_id": "ibm/granite-13b-chat-v2",
            "project_id": IBM_PROJECT_ID
        }
        
        response = requests.post(IBM_URL, headers=headers, json=body, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("results", [{}])[0].get("generated_text", "")
            
            # Parse the response
            category = "recyclable"
            confidence = 0.75
            reason = "Classified by IBM Granite AI"
            
            if "CATEGORY:" in generated_text:
                lines = generated_text.split("\n")
                for line in lines:
                    if "CATEGORY:" in line:
                        cat = line.split("CATEGORY:")[1].strip().lower()
                        if cat in ["organic", "recyclable", "hazardous"]:
                            category = cat
                    elif "CONFIDENCE:" in line:
                        try:
                            confidence = float(line.split("CONFIDENCE:")[1].strip())
                        except:
                            pass
                    elif "REASON:" in line:
                        reason = line.split("REASON:")[1].strip()
            
            return category, reason, confidence
        else:
            # Fallback to local classification
            return classify_waste_local(item_text)
            
    except Exception as e:
        # Fallback to local classification on error
        return classify_waste_local(item_text)

def classify_waste_local(item_text: str) -> Tuple[str, str, float]:
    """Local fallback classification using keyword matching"""
    item_lower = item_text.lower()
    category_scores = {}
    
    for category, data in KNOWLEDGE_BASE.items():
        score = 0
        matches = []
        
        for known_item in data["items"]:
            if known_item in item_lower or item_lower in known_item:
                score += 10
                matches.append(known_item)
        
        for keyword in data["keywords"]:
            if keyword in item_lower:
                score += 5
        
        if score > 0:
            category_scores[category] = score
    
    if category_scores:
        best_category = max(category_scores.items(), key=lambda x: x[1])[0]
        confidence = min(0.95, 0.5 + (category_scores[best_category] / 100))
    else:
        best_category = "recyclable"
        confidence = 0.50
    
    reason = f"Matched with {best_category} category based on keywords"
    return best_category, reason, confidence

def analyze_image(image: Image.Image) -> Tuple[str, str, float]:
    """Analyze image colors for waste classification"""
    try:
        img_rgb = image.convert('RGB').resize((200, 200))
        img_array = np.array(img_rgb)
        
        avg_color = img_array.mean(axis=(0, 1))
        r, g, b = avg_color
        
        is_green = g > r + 20 and g > b + 20
        is_brown = r > 100 and g > 70 and b < 100 and abs(r - g) < 50
        is_metallic = abs(r - g) < 20 and abs(g - b) < 20 and r > 120
        is_clear = r > 200 and g > 200 and b > 200
        
        if is_green or is_brown:
            return "organic", "🌿 Organic colors detected (green/brown)", 0.80
        elif is_metallic or is_clear:
            return "recyclable", "♻️ Recyclable material detected (metallic/clear)", 0.85
        else:
            if r > g and r > b:
                return "hazardous", "⚠️ Possible hazardous material (red tones)", 0.65
            else:
                return "recyclable", "♻️ General recyclable item", 0.60
        
    except Exception as e:
        return "recyclable", f"Error analyzing image: {str(e)}", 0.50

# Waste bin information
WASTE_BINS = {
    "organic": {
        "name": "Green Bin",
        "subtitle": "Organic/Compostable",
        "emoji": "🟢",
        "color": "#d4edda",
        "border": "#28a745"
    },
    "recyclable": {
        "name": "Yellow Bin",
        "subtitle": "Recyclable",
        "emoji": "🟡",
        "color": "#fff3cd",
        "border": "#ffc107"
    },
    "hazardous": {
        "name": "Red Bin",
        "subtitle": "Hazardous/Special Disposal",
        "emoji": "🔴",
        "color": "#f8d7da",
        "border": "#dc3545"
    }
}

# Custom CSS - Original Clean Theme
st.markdown("""
<style>
    /* Main container */
    .main .block-container {
        max-width: 800px;
        padding: 2rem 1rem;
    }
    
    /* Header */
    .main-header {
        text-align: center;
        padding: 2rem 1.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        font-weight: 800;
    }
    
    .main-header p {
        font-size: 1.1rem;
        opacity: 0.95;
        margin: 0;
    }
    
    /* Result box */
    .result-box {
        max-width: 450px;
        margin: 1.5rem auto;
        padding: 1.5rem;
        border-radius: 16px;
        border: 3px solid;
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
        text-align: center;
    }
    
    .result-box .emoji {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    
    .result-box h2 {
        font-size: 1.6rem;
        margin: 0.3rem 0;
        font-weight: 700;
        color: #000;
    }
    
    .result-box .subtitle {
        font-size: 0.95rem;
        opacity: 0.75;
        margin-bottom: 0.8rem;
        color: #000;
    }
    
    .result-box .item-name {
        font-size: 1.2rem;
        font-weight: 600;
        margin: 0.8rem 0;
        padding: 0.4rem 0.8rem;
        background: rgba(0,0,0,0.08);
        border-radius: 8px;
        display: inline-block;
        color: #000;
    }
    
    .confidence-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        background: rgba(0,0,0,0.15);
        font-size: 0.9rem;
        font-weight: 700;
        margin: 0.8rem 0;
        color: #000;
    }
    
    .reasoning {
        font-size: 0.9rem;
        opacity: 0.8;
        margin-top: 0.8rem;
        padding: 0.8rem;
        background: rgba(0,0,0,0.06);
        border-radius: 8px;
        color: #000;
    }
    
    /* Buttons */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        font-size: 1.1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Input fields */
    .stTextInput>div>div>input {
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        padding: 0.75rem 1rem;
        font-size: 1rem;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Info boxes */
    .stAlert {
        border-radius: 12px;
        border-left: 4px solid;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>♻️ Smart Waste Segregation</h1>
    <p>Intelligent waste classification system powered by IBM AI</p>
</div>
""", unsafe_allow_html=True)

# Create tabs
tab1, tab2 = st.tabs(["📝 Text Input", "📸 Image Upload"])

with tab1:
    st.markdown("### 🔍 Enter Waste Item")
    item_input = st.text_input(
        "What do you want to throw away?",
        placeholder="e.g., plastic bottle, banana peel, old battery",
        label_visibility="collapsed"
    )
    
    if st.button("Classify Item", key="text_classify"):
        if item_input.strip():
            with st.spinner("Analyzing..."):
                category, reason, confidence = classify_with_ibm_ai(item_input)
                
                bin_info = WASTE_BINS[category]
                st.markdown(f"""
                <div class="result-box" style="background-color: {bin_info['color']}; border-color: {bin_info['border']};">
                    <div class="emoji">{bin_info['emoji']}</div>
                    <h2>{bin_info['name']}</h2>
                    <div class="subtitle">{bin_info['subtitle']}</div>
                    <div class="item-name">"{item_input.title()}"</div>
                    <div class="confidence-badge">Confidence: {confidence:.0%}</div>
                    <div class="reasoning">💡 {reason}</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.success(f"**Disposal Guidelines:** {KNOWLEDGE_BASE[category]['guidelines']}")
                
                with st.expander("📚 Similar Items"):
                    st.write(", ".join(KNOWLEDGE_BASE[category]['items'][:10]))
        else:
            st.warning("⚠️ Please enter an item name")

with tab2:
    st.markdown("### 📸 Upload Waste Photo")
    uploaded_file = st.file_uploader(
        "Take a photo or upload image",
        type=['png', 'jpg', 'jpeg'],
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.image(image, caption="Your Image", use_column_width=True)
        
        with col2:
            if st.button("Analyze Image", key="image_classify"):
                with st.spinner("Analyzing..."):
                    category, description, confidence = analyze_image(image)
                    
                    bin_info = WASTE_BINS[category]
                    st.markdown(f"""
                    <div class="result-box" style="background-color: {bin_info['color']}; border-color: {bin_info['border']};">
                        <div class="emoji">{bin_info['emoji']}</div>
                        <h2>{bin_info['name']}</h2>
                        <div class="subtitle">{bin_info['subtitle']}</div>
                        <div class="confidence-badge">Confidence: {confidence:.0%}</div>
                        <div class="reasoning">{description}</div>
                    </div>
                    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("### 💡 Quick Examples")

col1, col2, col3 = st.columns(3)

examples = [
    ("🟢 Banana Peel", "banana peel"),
    ("🟡 Plastic Bottle", "plastic bottle"),
    ("🔴 Old Battery", "old battery")
]

for col, (label, value) in zip([col1, col2, col3], examples):
    with col:
        if st.button(label, key=f"ex_{value}"):
            st.session_state.example_item = value
            st.rerun()

if 'example_item' in st.session_state:
    st.info(f"💡 Try classifying: **{st.session_state.example_item}**")
    del st.session_state.example_item

# Made with Bob
st.markdown("""
<div style="text-align: center; padding: 1rem; margin-top: 2rem; opacity: 0.7;">
    <p>♻️ Smart Waste Segregation | Powered by IBM watsonx.ai</p>
    <p style="font-size: 0.9rem;">1M1B AI for Sustainability Virtual Internship</p>
</div>
""", unsafe_allow_html=True)

# Made with Bob
