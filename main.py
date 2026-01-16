




import os
import time
import re
import threading
import webbrowser
import speech_recognition as sr
from openai import OpenAI
import pyttsx3
import pygame
from flask import Flask, render_template, jsonify, request
import logging

# CUSTOM MODULES
import prompts
import memory
import automation 
import youtube_helper
# ==========================================
#        SETTINGS
# ==========================================
# 🔴 PASTE YOUR KEYS HERE

# Plst replace with your actual Groq API key 
# offical webiste: https://groq.com/ 
# Get your free API key from Groq to use 
GROQ_API_KEY = "YOUR_GROQ_API_KEY"  #<-------------------#// Replace with your Groq API key <---------------------------------------------
# YOUTUBE_API_KEY = "API-KEY-HERE"  # Currently disabled in code

ROBOT_SPEED = 140

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app = Flask(__name__)

shared_data = {
    "status": "idle", "last_text": "", "mode": None, "running": True,
    "available_voices": [], "current_voice_id": None, "target_voice_id": None     
}

client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)

# ==========================================
#        LOGIC
# ==========================================
def assistant_logic():
    engine = pyttsx3.init()
    engine.setProperty('rate', ROBOT_SPEED)
    
    voices = engine.getProperty('voices')
    voice_list = [{"id": v.id, "name": v.name.replace("Microsoft", "").strip()} for v in voices]
    shared_data["available_voices"] = voice_list
    default_id = voices[1].id if len(voices) > 1 else voices[0].id
    engine.setProperty('voice', default_id)
    shared_data["current_voice_id"] = default_id
    shared_data["target_voice_id"] = default_id

    def speak(text, force_google_lang=None):
        shared_data["status"] = "speaking"
        shared_data["last_text"] = text
        print(f"Genius: {text}")

        if shared_data["target_voice_id"] != shared_data["current_voice_id"]:
            try: engine.setProperty('voice', shared_data["target_voice_id"])
            except: pass

        use_google = False
        lang_code = 'en'
        if force_google_lang: use_google = True; lang_code = force_google_lang
        elif re.search(r'[\u0900-\u097F]', text): use_google = True; lang_code = 'hi'

        if use_google:
            from gtts import gTTS
            try:
                tts = gTTS(text=text, lang=lang_code, slow=False)
                fname = f"temp_{int(time.time())}.mp3"
                tts.save(fname)
                pygame.mixer.init(); pygame.mixer.music.load(fname); pygame.mixer.music.play()
                while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
                pygame.mixer.quit(); os.remove(fname)
            except: pass
        else:
            try: engine.say(text); engine.runAndWait()
            except: pass
        shared_data["status"] = "listening"

    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True

    while shared_data["mode"] is None:
        if not shared_data["running"]: return
        time.sleep(0.5)

    choice = shared_data["mode"]
    active_prompt = prompts.get_prompt(choice)
    memory.init_memory(active_prompt)
    listen_lang = "hi-IN" if choice == '2' else "en-IN"
    
    speak("System Online. I am ready.")

    with sr.Microphone() as source: recognizer.adjust_for_ambient_noise(source, duration=1)

    while shared_data["running"]:
        try:
            with sr.Microphone() as source:
                print("Listening...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
                shared_data["status"] = "processing"
                text = recognizer.recognize_google(audio, language=listen_lang)
                shared_data["last_text"] = text
                print(f"User: {text}")
                cmd = text.lower()

                if "stop" in cmd or "exit" in cmd:
                    speak("Goodbye."); os._exit(0)

                # --- 1. CODING MODE (FIXED & CLEANED) ---
                if "build" in cmd or "code" in cmd or "create a website" in cmd:
                    speak("I am building the premium project now.")
                    try:
                        # === STRICT "ALL-IN-ONE" PROMPT ===
                        sys_prompt = (
    "You are a World-Class Creative Frontend Developer (Awwwards-level)."
    "Your Goal: Create a VISUALLY STUNNING, High-Performance Single-Page Website."
    
    "CRITICAL INSTRUCTIONS:"
    "1. OUTPUT FORMAT: A single, raw HTML string starting with <!DOCTYPE html>."
    "2. NO MARKDOWN: Do not use ```html or markdown ticks. Just pure code."
    "3. STRUCTURE: Merge all CSS into <style> and JS into <script> tags."
    
    "DESIGN & CSS REQUIREMENTS (Must use 80% CSS / 20% JS):"
    "- THEME: 'Midnight Luxury'. Deep blacks (#0a0a0a), Gold gradients, and Noise textures."
    "- ADVANCED CSS: Use CSS Variables (:root), CSS Grid for complex layouts, and clamp() for responsive typography."
    "- VISUALS: Implement 'Glassmorphism' (backdrop-filter: blur), 'Neumorphism', or 'Aurora Gradients'."
    "- ANIMATIONS: Use @keyframes for entrance animations. Use 'transform: translate3d' for hardware-accelerated smoothness."
    "- INTERACTIVITY: Create a custom cursor, magnetic buttons (using JS/CSS), and hover reveal effects."
    "- IMAGES: Use '[https://source.unsplash.com/random/1920x1080/?abstract,dark,gold](https://source.unsplash.com/random/1920x1080/?abstract,dark,gold)' for backgrounds."
    
    "CONTENT:"
    "- Hero Section: Big bold typography, parallax scrolling effect."
    "- Services: Grid layout with hover-tilt cards."
    "- Footer: Minimalist and clean."
    
    "Generate the code now. Make it look expensive."
)
                        
                        completion = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": text}],
                            temperature=0.1
                        )
                        code_content = completion.choices[0].message.content
                        
                        # === THE FIX: EXTRACT ONLY HTML ===
                        # This Regex looks for <!DOCTYPE html> ... </html> and ignores everything else.
                        match = re.search(r"(<!DOCTYPE html>[\s\S]*</html>)", code_content, re.IGNORECASE)
                        if match:
                            code_content = match.group(1)
                        else:
                            # Fallback cleaner if Regex misses
                            code_content = code_content.replace("```html", "").replace("```", "").replace("**index.html**", "").strip()

                        lang = "python" if "python" in cmd else "html"
                        result = automation.create_coding_project(code_content, lang)
                        speak(result)
                        continue
                    except Exception as e:
                        print(f"CODING ERROR: {e}") 
                        speak("I faced an error while creating the code.")
                        continue
 
 # ... (Coding Mode logic is above here) ...

                # --- 2. WRITING MODE ---
                if "write" in cmd and ("essay" in cmd or "letter" in cmd):
                    # ... (Your existing writing logic) ...
                    pass # (Keep your existing code here)

                # ==========================================
                #  NEW: YOUTUBE SEARCH (NO API KEY)
                # ==========================================
                if "play" in cmd or ("youtube" in cmd and "search" in cmd):
                    speak("Searching YouTube...")
                    # Call the function from the new file
                    result = youtube_helper.search_video(cmd)
                    speak(result)
                    continue

                # --- 3. AUTOMATION ---
                # app_res = automation.execute(text, YOUTUBE_API_KEY)
                app_res = automation.execute(text, None) 
                if app_res:
                    speak(app_res)
                    continue
                
                # ... (Chat logic continues below) ...
                # --- 2. WRITING MODE ---
                if "write" in cmd and ("essay" in cmd or "letter" in cmd):
                    app_target = "word" if "word" in cmd else "notepad"
                    speak(f"Writing in {app_target}...")
                    try:
                        sys_prompt = "Write the content directly. No intros."
                        completion = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": text}],
                            max_tokens=800
                        )
                        content = completion.choices[0].message.content
                        result = automation.type_and_save(content, app_target)
                        speak(result)
                        continue
                    except:
                        speak("I could not generate the text.")
                        continue

                # --- 3. AUTOMATION ---
                # app_res = automation.execute(text, YOUTUBE_API_KEY)
                app_res = automation.execute(text, None)
                if app_res:
                    speak(app_res)
                    continue

                # --- 4. CHAT ---
                memory.add_user_message(text)
                try:
                    completion = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=memory.get_messages(),
                        max_tokens=100
                    )
                    res = completion.choices[0].message.content
                    memory.add_ai_message(res)
                    speak(res)
                except: speak("Connection failed.")

        except Exception as e:
            shared_data["status"] = "listening"

# ROUTES
@app.route('/')
def index(): return render_template('index.html')
@app.route('/status')
def status(): return jsonify(shared_data)
@app.route('/get_voices')
def get_voices(): return jsonify(shared_data["available_voices"])
@app.route('/set_voice', methods=['POST'])
def set_voice():
    data = request.json
    shared_data["target_voice_id"] = data['voice_id']
    return "OK"
@app.route('/start_mode/<mode>')
def start_mode(mode): shared_data["mode"] = mode; return "OK"
@app.route('/shutdown')
def shutdown():
    shared_data["running"] = False
    threading.Thread(target=lambda: (time.sleep(1), os._exit(0))).start()
    return "Bye"

if __name__ == "__main__":
    if "PASTE" in GROQ_API_KEY: print("❌ ERROR: Paste Key!")
    else:
        thread = threading.Thread(target=assistant_logic)
        thread.daemon = True; thread.start()
        webbrowser.open('http://127.0.0.1:5000')
        app.run(port=5000)



