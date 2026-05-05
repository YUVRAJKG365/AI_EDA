# chatbot.py (Smart and Context-Aware AI Data Scientist with Memory & Learning)
import numpy as np
import datetime
import time
import json
import streamlit as st
import requests
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from collections import deque
import hashlib
import ssl
import certifi
from typing import List, Dict, Any, Optional, Union, Iterable
import os

# ==== FIX SSL CERTIFICATE ISSUE ====
# Clear any problematic SSL environment variables
os.environ.pop('CURL_CA_BUNDLE', None)
os.environ.pop('REQUESTS_CA_BUNDLE', None)
os.environ.pop('SSL_CERT_FILE', None)

# Use certifi's certificate bundle
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# ==== CONFIGURATION ====
# NVIDIA API Configuration (replacing OpenRouter)
NVIDIA_API_KEY = "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"
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
PROMPT_LIMIT = 50
COOLDOWN_HOURS = 24

# Available models configuration - NVIDIA models only
AVAILABLE_MODELS = {
    "Mistral Large (Default)": {
        "url": NVIDIA_API_URL,
        "model_id": "mistralai/mistral-large-3-675b-instruct-2512",
        "provider": "NVIDIA",
        "max_tokens": 2048,
        "temperature": 0.15,
        "top_p": 1.00
    },
    "Mistral Medium": {
        "url": NVIDIA_API_URL,
        "model_id": "mistralai/mistral-medium-3-instruct",
        "provider": "NVIDIA",
        "max_tokens": 1024,
        "temperature": 0.15,
        "top_p": 1.00
    },
    "Meta Llama 4": {
        "url": NVIDIA_API_URL,
        "model_id": "meta/llama-4-maverick-17b-128e-instruct",
        "provider": "NVIDIA",
        "max_tokens": 1024,
        "temperature": 0.15,
        "top_p": 1.00
    },
    "Google Gemma 3": {
        "url": NVIDIA_API_URL,
        "model_id": "google/gemma-3-27b-it",
        "provider": "NVIDIA",
        "max_tokens": 1024,
        "temperature": 0.15,
        "top_p": 0.70
    },
    "Microsoft Phi-4 Multimodal": {
        "url": NVIDIA_API_URL,
        "model_id": "microsoft/phi-4-multimodal-instruct",
        "provider": "NVIDIA",
        "max_tokens": 1024,
        "temperature": 0.20,
        "top_p": 0.70
    },
    "Meta Llama 4 Scout": {
        "url": NVIDIA_API_URL,
        "model_id": "meta/llama-4-scout-17b-16e-instruct",
        "provider": "NVIDIA",
        "max_tokens": 1024,
        "temperature": 1.00,
        "top_p": 1.00
    }
}

# Default model
DEFAULT_MODEL = "Mistral Large (Default)"


# ==== MEMORY & LEARNING SYSTEM ====

class MemorySystem:
    """Short-term and long-term memory for the AI"""
    
    def __init__(self, max_short_term=10):
        self.max_short_term = max_short_term
        
    def initialize_memory(self):
        """Initialize memory in session state"""
        if "short_term_memory" not in st.session_state:
            st.session_state.short_term_memory = deque(maxlen=self.max_short_term)
        
        if "long_term_memory" not in st.session_state:
            st.session_state.long_term_memory = {}
        
        if "user_preferences" not in st.session_state:
            st.session_state.user_preferences = {
                "preferred_mode": None,
                "common_topics": {},
                "expert_count": 0,
                "professional_count": 0,
                "casual_count": 0
            }
        
        if "interaction_history" not in st.session_state:
            st.session_state.interaction_history = []
    
    def add_to_short_term(self, user_input, response, mode):
        """Add interaction to short-term memory"""
        interaction = {
            "timestamp": datetime.datetime.now().isoformat(),
            "user_input": user_input,
            "response": response[:200] + "..." if len(response) > 200 else response,
            "mode": mode
        }
        st.session_state.short_term_memory.append(interaction)
    
    def learn_from_interaction(self, user_input, mode, feedback=None):
        """Learn from user interactions"""
        # Update mode counts
        if mode == "expert":
            st.session_state.user_preferences["expert_count"] += 1
        elif mode == "professional":
            st.session_state.user_preferences["professional_count"] += 1
        else:
            st.session_state.user_preferences["casual_count"] += 1
        
        # Extract topics (simple keyword-based)
        topics = self._extract_topics(user_input)
        for topic in topics:
            st.session_state.user_preferences["common_topics"][topic] = \
                st.session_state.user_preferences["common_topics"].get(topic, 0) + 1
        
        # Determine preferred mode based on usage
        counts = {
            "expert": st.session_state.user_preferences["expert_count"],
            "professional": st.session_state.user_preferences["professional_count"],
            "casual": st.session_state.user_preferences["casual_count"]
        }
        if sum(counts.values()) > 5:  # After enough interactions
            # Fix: Properly get the key with maximum value
            preferred_mode = max(counts.items(), key=lambda x: x[1])[0]
            st.session_state.user_preferences["preferred_mode"] = preferred_mode
        
        # Store in long-term memory if important
        if self._is_important_interaction(user_input):
            self._add_to_long_term(user_input, mode)
    
    def get_memory_context(self):
        """Get memory context for prompts"""
        context_parts = []
        
        # Short-term memory (recent conversations)
        if st.session_state.short_term_memory:
            recent = list(st.session_state.short_term_memory)[-3:]  # Last 3
            context_parts.append("RECENT CONVERSATION:")
            for i, mem in enumerate(recent, 1):
                context_parts.append(f"{i}. User: {mem['user_input'][:100]}")
        
        # User preferences
        prefs = st.session_state.user_preferences
        if prefs["preferred_mode"]:
            context_parts.append(f"USER PREFERENCE: Seems to prefer {prefs['preferred_mode']} responses")
        
        # Common topics
        if prefs["common_topics"]:
            top_topics = sorted(prefs["common_topics"].items(), key=lambda x: x[1], reverse=True)[:3]
            topics_str = ", ".join([t[0] for t in top_topics])
            context_parts.append(f"FREQUENT TOPICS: {topics_str}")
        
        return "\n".join(context_parts)
    
    def _extract_topics(self, text):
        """Extract topics from text"""
        topics = []
        topic_keywords = {
            "machine learning": ["ml", "machine learning", "model", "training"],
            "data analysis": ["analysis", "analyze", "statistics", "correlation"],
            "visualization": ["plot", "chart", "graph", "visualization"],
            "cleaning": ["clean", "missing", "outlier", "preprocessing"],
            "deep learning": ["deep", "neural", "cnn", "rnn", "lstm"],
            "business": ["business", "insights", "dashboard", "report"]
        }
        
        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics[:3]  # Max 3 topics
    
    def _is_important_interaction(self, user_input):
        """Determine if interaction is important enough for long-term memory"""
        important_keywords = ["remember", "important", "key", "critical", "always", "never", "prefer"]
        return any(keyword in user_input.lower() for keyword in important_keywords)
    
    def _add_to_long_term(self, user_input, mode):
        """Add to long-term memory"""
        # Create a hash of the input for lookup
        input_hash = hashlib.md5(user_input.encode()).hexdigest()[:8]
        
        st.session_state.long_term_memory[input_hash] = {
            "input": user_input[:200],
            "mode": mode,
            "timestamp": datetime.datetime.now().isoformat(),
            "importance": "high"
        }


class FeedbackLearning:
    """Learn from user feedback"""
    
    def __init__(self):
        pass
    
    def initialize_feedback(self):
        """Initialize feedback system"""
        if "feedback_history" not in st.session_state:
            st.session_state.feedback_history = []
        
        if "response_quality" not in st.session_state:
            st.session_state.response_quality = {
                "excellent": 0,
                "good": 0,
                "poor": 0
            }
    
    def add_feedback(self, response_id, rating, comment=""):
        """Add user feedback"""
        feedback = {
            "timestamp": datetime.datetime.now().isoformat(),
            "response_id": response_id,
            "rating": rating,
            "comment": comment
        }
        st.session_state.feedback_history.append(feedback)
        st.session_state.response_quality[rating] += 1
    
    def get_quality_score(self):
        """Get overall quality score"""
        total = sum(st.session_state.response_quality.values())
        if total == 0:
            return 0.5
        return (st.session_state.response_quality["excellent"] * 1.0 +
                st.session_state.response_quality["good"] * 0.7) / total


# ==== PROMPT ENGINE (AUTO + MANUAL MODE) ====

class PromptEngine:
    def __init__(self, model_name="YUPS-AI"):
        self.model_name = model_name

    def detect_mode(self, user_input: str):
        user_input_lower = user_input.lower()

        expert_keywords = [
            "optimize", "architecture", "scalability", "tradeoff",
            "xgboost", "lstm", "transformer", "fine-tuning",
            "hyperparameter", "pipeline", "production", "distributed",
            "ensemble", "gradient", "backpropagation", "attention"
        ]

        data_keywords = [
            "data", "analysis", "dataset", "csv", "pandas",
            "numpy", "visualization", "plot", "graph",
            "machine learning", "model", "training", "prediction",
            "correlation", "regression", "classification", "cluster"
        ]

        if any(word in user_input_lower for word in expert_keywords):
            return "expert"

        elif any(word in user_input_lower for word in data_keywords):
            return "professional"

        return "casual"

    def build_prompt(self, user_input, context, memory_context, manual_expert_mode=False):
        auto_mode = self.detect_mode(user_input)

        # PRIORITY: Manual override
        if manual_expert_mode:
            mode = "expert"
        else:
            mode = auto_mode

        # Add learning context
        full_context = context + "\n\n" + memory_context if memory_context else context

        if mode == "casual":
            return self._casual(user_input), mode
        elif mode == "expert":
            return self._expert(user_input, full_context), mode
        else:
            return self._professional(user_input, full_context), mode

    # ---- MODES ----
    def _casual(self, user_input):
        return (
            "You are a fun, friendly, and intelligent AI buddy created by YUPS. "
            "You respond like a cheerful young person (18–25 age range), but you are also smart and helpful.\n\n"

            "Core Intelligence Rules:\n"
            "- Always understand user intent before replying\n"
            "- If unclear, ask a short clarifying question\n"
            "- Never give wrong or misleading info\n"
            "- Keep answers helpful even in casual mode\n"
            "- Think step-by-step internally but keep answers concise\n\n"

            "Personality & Style:\n"
            "- Use simple, natural language\n"
            "- Keep sentences short and engaging\n"
            "- Use contractions (you're, don't, etc.)\n"
            "- Add light humor when appropriate\n"
            "- Use emojis sparingly (max 1–2)\n\n"

            "Smart Behavior:\n"
            "- If user asks technical/data question → gently provide useful explanation\n"
            "- If unsure: 'Hmm, not totally sure, but here's what I think… 😅'\n\n"

            f"USER MESSAGE: {user_input}\n\n"
            "CASUAL RESPONSE:"
        )

    def _expert(self, user_input, context):
        return (
            f"You are a world-class AI Data Scientist using {self.model_name}, created by YUPS.\n\n"

            "Your personality:\n"
            "- 20+ years of experience equivalent\n"
            "- Precise, analytical, and deeply insightful\n"
            "- Calm, confident, mentor-like tone\n\n"

            "Core Intelligence Rules:\n"
            "- Understand the problem deeply before answering\n"
            "- Break complex problems step-by-step\n"
            "- Clearly state assumptions\n"
            "- Avoid hallucinations; say 'uncertain' if needed\n"
            "- Validate your answer before responding\n"
            "- Think step-by-step internally but keep output structured\n\n"

            "Data Science Reasoning Framework:\n"
            "1. Problem Understanding\n"
            "2. Data Requirements & Considerations\n"
            "3. Method/Algorithm Selection (with justification)\n"
            "4. Implementation Insight\n"
            "5. Limitations & Risks\n"
            "6. Optimization / Alternatives\n\n"

            "Response Structure:\n"
            "1. Direct Answer\n"
            "2. Deep Explanation\n"
            "3. Example (if applicable)\n"
            "4. Real-world Application\n"
            "5. Pro Tips\n\n"

            "Answer Quality Rules:\n"
            "- Avoid vague statements\n"
            "- Use examples where useful\n"
            "- Prefer practical insights over theory\n"
            "- Keep response structured and readable\n"
            "- Do not over-explain unnecessarily\n\n"

            "Adaptive Intelligence:\n"
            "- Adjust depth based on user knowledge level\n"
            "- Simple query → simple explanation\n"
            "- Advanced query → deeper technical insights\n\n"

            f"CONTEXT:\n{context}\n\n"
            f"USER QUESTION: {user_input}\n\n"
            "EXPERT RESPONSE:"
        )

    def _professional(self, user_input, context):
        return (
            f"You are a skilled AI Data Assistant using {self.model_name} (30–40 age range), created by YUPS.\n\n"

             "Your personality:\n"
            "- Practical, clear, and solution-oriented\n"
            "- Explains like a knowledgeable colleague\n"
            "- Uses analogies when helpful\n\n"

            "Core Intelligence Rules:\n"
            "- Understand the problem before answering\n"
            "- If ambiguous, ask for clarification\n"
            "- Do not assume missing data\n"
            "- Think step-by-step internally\n\n"

            "Data Science Approach:\n"
            "- Identify problem type (EDA, ML, stats, etc.)\n"
            "- Suggest best practical approach\n"
            "- Briefly explain why it works\n\n"

            "Response Structure:\n"
            "1. Direct Answer (1–2 lines)\n"
            "2. Key Points (bullets if needed)\n"
            "3. Actionable Steps\n\n"

            "Answer Quality Rules:\n"
            "- Keep it clear and concise\n"
            "- Avoid unnecessary jargon\n"
            "- Focus on actionable solutions\n\n"

            "Adaptive Intelligence:\n"
            "- Match explanation level to user knowledge\n\n"

            f"CONTEXT:\n{context}\n\n"
            f"USER QUESTION: {user_input}\n\n"
            "PROFESSIONAL RESPONSE:"
        )


def initialize_prompt_tracking():
    if "prompt_count" not in st.session_state:
        st.session_state.prompt_count = 0
    if "first_prompt_time" not in st.session_state:
        st.session_state.first_prompt_time = datetime.datetime.now()


def can_prompt():
    initialize_prompt_tracking()
    return st.session_state.prompt_count < PROMPT_LIMIT


def increment_prompt():
    st.session_state.prompt_count += 1
    if st.session_state.prompt_count == 1:
        st.session_state.first_prompt_time = datetime.datetime.now()


def get_reset_time():
    if "first_prompt_time" in st.session_state and st.session_state.first_prompt_time is not None:
        return st.session_state.first_prompt_time + datetime.timedelta(hours=COOLDOWN_HOURS)
    return datetime.datetime.now() + datetime.timedelta(hours=COOLDOWN_HOURS)


def format_reset_time(reset_time):
    if reset_time is None:
        return "Unknown"
    return reset_time.strftime("%Y-%m-%d at %H:%M %p")


def convert_df_for_analysis(df):
    """Convert DataFrame columns to appropriate numeric types"""
    df_clean = df.copy()
    for col in df_clean.columns:
        try:
            # Use coerce instead of ignore for better type conversion
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        except:
            pass

        if df_clean[col].dtype == 'object':
            try:
                df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')
            except:
                if df_clean[col].nunique() < 50:
                    le = LabelEncoder()
                    df_clean[col] = le.fit_transform(df_clean[col].astype(str))
    return df_clean


def create_requests_session_with_ssl():
    """Create a requests session with proper SSL configuration"""
    session = requests.Session()
    
    # Use certifi's certificate bundle
    session.verify = certifi.where()
    
    # Configure SSL context if needed
    from requests.adapters import HTTPAdapter
    from urllib3.poolmanager import PoolManager
    
    class SSLAdapter(HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            kwargs['cert_reqs'] = ssl.CERT_REQUIRED
            kwargs['ca_certs'] = certifi.where()
            return super().init_poolmanager(*args, **kwargs)
    
    session.mount('https://', SSLAdapter())
    
    return session


def chatbot_response(user_input, context=None, api_key=None, model_url=None, model_name=None):
    if not api_key or not model_url:
        yield "⚠️ Missing API key or model."
        return

    memory_system = MemorySystem()
    memory_context = memory_system.get_memory_context()

    if model_name not in AVAILABLE_MODELS:
        model_name = DEFAULT_MODEL

    model_config = AVAILABLE_MODELS[model_name]

    prompt_engine = PromptEngine(model_name=model_name)
    system_prompt, detected_mode = prompt_engine.build_prompt(
        user_input=user_input,
        context=str(context),
        memory_context=memory_context,
        manual_expert_mode=st.session_state.get('expert_mode', False)
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_config["model_id"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        "max_tokens": model_config["max_tokens"],
        "temperature": model_config["temperature"],
        "top_p": model_config["top_p"],
        "stream": True
    }

    session = st.session_state.get("_session")
    if not session:
        session = requests.Session()
        st.session_state["_session"] = session

    try:
        response = session.post(
            model_url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=300
        )

        full_text = ""

        for line in response.iter_lines():
            if not line:
                continue

            decoded = line.decode("utf-8")

            if decoded.startswith("data: "):
                data = decoded.replace("data: ", "").strip()

                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content", "")

                    if delta:
                        full_text += delta
                        yield full_text

                except:
                    continue

        # Save memory
        memory_system.add_to_short_term(user_input, full_text, detected_mode)
        memory_system.learn_from_interaction(user_input, detected_mode)

    except Exception as e:
        yield f"🚨 Error: {str(e)}"


def build_expert_context():
    context = {}

    # Dataset context
    if 'df' in st.session_state and st.session_state.df is not None:
        df = st.session_state.df

        # Clean and convert dataframe
        df_clean = convert_df_for_analysis(df)

        context['dataset'] = {
            'shape': f"{df_clean.shape[0]} rows × {df_clean.shape[1]} columns",
            'columns': list(df_clean.columns),
            'dtypes': {col: str(dtype) for col, dtype in df_clean.dtypes.items()},
            'missing_values': int(df_clean.isnull().sum().sum())
        }

        # Add statistical summary only for numeric columns
        import pandas as pd
        if isinstance(df_clean, pd.DataFrame):
            numeric_cols = df_clean.select_dtypes(include=np.number).columns
        else:
            numeric_cols = []
        
        # Check if numeric_cols has any elements and convert to list for compatibility
        if hasattr(numeric_cols, '__iter__') and not isinstance(numeric_cols, str):
            numeric_cols_list = list(numeric_cols)
        else:
            numeric_cols_list = []
            
        if numeric_cols_list and len(numeric_cols_list) > 0:
            context['dataset']['statistical_summary'] = df_clean[numeric_cols_list].describe().to_dict()

            # Add correlation matrix only if we have 2+ numeric columns
            if len(numeric_cols_list) > 1:
                context['dataset']['correlation_matrix'] = df_clean[numeric_cols_list].corr().to_dict()

    # Text/PDF context
    if 'text_data' in st.session_state and st.session_state.text_data:
        text = st.session_state.text_data
        if isinstance(text, str) and len(text) > 0:
            context['text_analysis'] = {
                'length': len(text),
                'preview': text[:500] + "..." if len(text) > 500 else text
            }

    # Image context
    if 'image_data' in st.session_state and st.session_state.image_data is not None:
        img = st.session_state.image_data
        context['image_analysis'] = {
            'format': getattr(img, 'format', 'Unknown'),
            'size': getattr(img, 'size', 'Unknown'),
            'mode': getattr(img, 'mode', 'Unknown')
        }

    return context


def extract_topics(text):
    return ["Data Analysis", "Business Insights", "Trends"]


def analyze_sentiment(text):
    return "Neutral"


def display_usage_status():
    initialize_prompt_tracking()
    reset_time = get_reset_time()

    # Create a more compact layout with model selector next to progress
    col1, col2, col3 = st.columns([0.5, 0.3, 0.2])

    with col1:
        if PROMPT_LIMIT > 0:
            st.progress(st.session_state.prompt_count / PROMPT_LIMIT,
                        text=f"**{st.session_state.prompt_count}/{PROMPT_LIMIT} prompts used**")

    with col2:
        if st.session_state.prompt_count >= PROMPT_LIMIT:
            st.warning(f"⏳ {format_reset_time(reset_time)}")
        else:
            st.info(f"🔄 {format_reset_time(reset_time)}")

    with col3:
        # Model selector dropdown
        selected_model = st.selectbox(
            "Model",
            options=list(AVAILABLE_MODELS.keys()),
            index=0 if "selected_model" not in st.session_state else list(AVAILABLE_MODELS.keys()).index(
                st.session_state.selected_model),
            label_visibility="collapsed",
            key="model_selector"
        )

        if selected_model != st.session_state.get("selected_model"):
            st.session_state.selected_model = selected_model
            model_info = AVAILABLE_MODELS.get(selected_model)
            if model_info is not None:
                st.session_state.model_url = model_info["url"]


def display_memory_status():
    """Display memory system status in an expander"""
    with st.expander("🧠 Memory & Learning Status", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Short-term Memory**")
            if st.session_state.get("short_term_memory"):
                for i, mem in enumerate(list(st.session_state.short_term_memory)[-3:], 1):
                    st.markdown(f"{i}. *{mem['user_input'][:50]}...*")
            else:
                st.markdown("*No recent interactions*")
        
        with col2:
            st.markdown("**User Preferences**")
            prefs = st.session_state.get("user_preferences", {})
            if prefs.get("preferred_mode"):
                st.markdown(f"Preferred: **{prefs['preferred_mode']}**")
            
            # Show mode distribution
            total = prefs.get("expert_count", 0) + prefs.get("professional_count", 0) + prefs.get("casual_count", 0)
            if total > 0:
                st.markdown(f"Expert: {prefs.get('expert_count', 0)} | Professional: {prefs.get('professional_count', 0)} | Casual: {prefs.get('casual_count', 0)}")
            
            # Show common topics
            if prefs.get("common_topics"):
                top_topics = sorted(prefs["common_topics"].items(), key=lambda x: x[1], reverse=True)[:3]
                st.markdown("**Common Topics:**")
                for topic, count in top_topics:
                    st.markdown(f"- {topic}: {count}")


def chatbot_ui():
    """Advanced AI Data Scientist Chat Interface with Memory & Learning"""

    st.markdown("## 🧠 AI Data Scientist Assistant")
    st.markdown("*Your intelligent partner for data analysis with memory & learning*")

    # Initialize memory systems
    memory_system = MemorySystem()
    memory_system.initialize_memory()
    
    feedback_system = FeedbackLearning()
    feedback_system.initialize_feedback()

    # Ensure the app uses the default model and API key
    if "selected_model" not in st.session_state or not st.session_state.selected_model:
        model_info = AVAILABLE_MODELS.get(DEFAULT_MODEL)
        if model_info is not None:
            st.session_state.selected_model = DEFAULT_MODEL
            st.session_state.model_url = model_info["url"]
        st.session_state.api_key = NVIDIA_API_KEY
        st.session_state.chat_history = []
        st.session_state.temperature = st.session_state.get('temperature', 0.15)

    # Expert mode toggle
    st.session_state.expert_mode = st.toggle(
        "🔬 Expert Mode (Manual Override)",
        value=st.session_state.get('expert_mode', False),
        help="Enable for detailed technical analysis and advanced explanations (overrides auto-detection)"
    )

    # Display usage status with integrated model selector
    display_usage_status()

    # Display memory status
    display_memory_status()

    # Build expert-level context
    context = build_expert_context()

    # Chat interface
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display conversation history
    chat_container = st.container(height=400, border=True)
    with chat_container:
        for msg in st.session_state.chat_history:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

    # ===== FIXED INPUT HANDLING (NO RERUN / NO FLICKER) =====

    # Initialize state (add this ONCE here)
    if "pending_input" not in st.session_state:
        st.session_state.pending_input = None

    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False

    # Chat input
    user_input = st.chat_input("Ask your AI Data Scientist...")

    # Store input safely (DO NOT process immediately)
    if user_input and not st.session_state.is_processing:
        st.session_state.pending_input = user_input
        st.session_state.is_processing = True

    # Process request ONLY ONCE
    if st.session_state.pending_input and st.session_state.is_processing:

        user_text = st.session_state.pending_input

        # Add user message
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_text
        })

        with chat_container:
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(user_text)

            with st.chat_message("assistant", avatar="🤖"):
                response_box = st.empty()
                full_response = ""

                # 🔥 STREAMING RESPONSE
                for chunk in chatbot_response(
                        user_text,
                        context=context,
                        api_key=st.session_state.api_key,
                        model_url=st.session_state.model_url,
                        model_name=st.session_state.selected_model
                ):
                    full_response = chunk
                    response_box.markdown(full_response)

        # Save final response
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": full_response
        })

        # Reset flags (VERY IMPORTANT)
        st.session_state.pending_input = None
        st.session_state.is_processing = False


# Example usage in your main app
if __name__ == "__main__":
    chatbot_ui()