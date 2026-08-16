from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import json
import os
import uuid
import base64
import io
import csv
import pandas as pd
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)
CORS(app)

# ==========================================
# KONFIGURASI SUPER
# ==========================================
AI_CONFIG = {
    "name": "NEXA",
    "personality": "Profesional & tegas",
    "language": "Bilingual",
    "tone": "Semi-formal"
}

PERPLEXITY_API_KEY = "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"
PERPLEXITY_URL = "https://api.perplexity.ai/search"

# ==========================================
# DATABASE SIMULASI (pakai Supabase/Firebase untuk production)
# ==========================================
sessions = {}
users = {}
schedules = {}
analytics = {
    "total_queries": 0,
    "command_usage": {},
    "active_users": 0,
    "popular_modes": {}
}

# ==========================================
# KNOWLEDGE BASE DINAMIS (bisa diupdate via API)
# ==========================================
KNOWLEDGE_BASE = {
    "company": "PT NEXA Teknologi",
    "products": ["NEXA AI", "Data Hub", "Cloud Sync"],
    "sop": "Response time < 1 jam.",
    "faq": {
        "support": "Hubungi support@nexa.ai",
        "pricing": "Mulai Rp 1.000.000/bulan"
    }
}

# ==========================================
# SPECIAL COMMANDS (diperluas)
# ==========================================
SPECIAL_COMMANDS = {
    "/deep": "Analisis mendalam dengan framework 5W+1H",
    "/fast": "Jawaban 1 paragraf maksimal",
    "/creative": "Brainstorming 10 ide liar",
    "/code": "Mode programmer + unit test",
    "/data": "Analisis data + visualisasi rekomendasi",
    "/teach": "Step-by-step dengan analogi",
    "/role": "Switch persona (contoh: /role lawyer)",
    "/schedule": "Buat pengingat (format: /schedule [pesan] [tanggal]",
    "/image": "Generate gambar (placeholder)",
    "/upload": "Upload file CSV/JSON untuk analisis",
    "/stats": "Lihat statistik penggunaan"
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_session(session_id):
    if session_id not in sessions:
        sessions[session_id] = {
            "history": [],
            "mode": "normal",
            "role": None,
            "user_id": None,
            "avatar": "https://i.imgur.com/default_avatar.png"
        }
    return sessions[session_id]

def log_command(cmd):
    analytics["total_queries"] += 1
    if cmd in analytics["command_usage"]:
        analytics["command_usage"][cmd] += 1
    else:
        analytics["command_usage"][cmd] = 1

def build_prompt(user_input, session):
    history_text = "\n".join([f"User: {h['user']}\nAI: {h['ai']}" for h in session["history"][-10:]])
    mode_desc = {
        "normal": "Jawab profesional.",
        "deep": "Analisis mendalam.",
        "fast": "Singkat padat.",
        "creative": "Ide out-of-the-box.",
        "code": "Kode + penjelasan.",
        "data": "Analisis data.",
        "teach": "Mentor step-by-step."
    }.get(session["mode"], "Jawab profesional.")
    
    role_instruction = f"Bertindak sebagai {session['role']}." if session.get("role") else ""
    
    return f"""
Anda adalah {AI_CONFIG['name']}, {AI_CONFIG['personality']}. 
Bahasa: {AI_CONFIG['language']}. Tone: {AI_CONFIG['tone']}.
{role_instruction}
Mode: {session['mode']} — {mode_desc}

Knowledge: {json.dumps(KNOWLEDGE_BASE, indent=2)}

History (10 turn):
{history_text}

User: {user_input}

Instruksi:
- Pahami konteks & slang.
- Jika tidak tahu, akui jujur.
- Tolak permintaan ilegal.
- Berikan disclaimer medis/legal/finansial.
- Gunakan emoji secukupnya.
- Akhiri dengan follow-up.

Jawab:
"""

# ==========================================
# API ENDPOINTS
# ==========================================
@app.route('/', methods=['POST'])
def nexa_response():
    data = request.get_json()
    user_input = data.get('input', '').strip()
    session_id = data.get('session_id', 'default')
    file_data = data.get('file', None)  # untuk upload file
    
    if not user_input and not file_data:
        return jsonify({"error": "Input kosong"}), 400

    session = get_session(session_id)
    analytics["total_queries"] += 1

    # ===== HANDLE COMMANDS =====
    cmd_parts = user_input.lower().split()
    cmd = cmd_parts[0] if cmd_parts else ""

    # /role
    if cmd == "/role" and len(cmd_parts) > 1:
        new_role = cmd_parts[1]
        session["role"] = new_role if new_role != "default" else None
        log_command("/role")
        return jsonify({
            "answer": f"🔄 Role switched to: {new_role.upper()}",
            "avatar": session["avatar"],
            "session_id": session_id
        })

    # /schedule
    if cmd == "/schedule" and len(cmd_parts) >= 3:
        try:
            message = " ".join(cmd_parts[1:-1])
            date_str = cmd_parts[-1]
            schedule_date = datetime.strptime(date_str, "%Y-%m-%d")
            schedule_id = str(uuid.uuid4())
            schedules[schedule_id] = {
                "message": message,
                "date": schedule_date.isoformat(),
                "user_id": session_id,
                "done": False
            }
            log_command("/schedule")
            return jsonify({
                "answer": f"📅 Jadwal '{message}' disimpan pada {date_str} (ID: {schedule_id})",
                "avatar": session["avatar"]
            })
        except:
            return jsonify({"answer": "❌ Format salah. Gunakan: /schedule [pesan] YYYY-MM-DD"})

    # /image
    if cmd == "/image":
        log_command("/image")
        # Placeholder image generation (gunakan Unsplash API)
        query = " ".join(cmd_parts[1:]) if len(cmd_parts) > 1 else "random"
        image_url = f"https://source.unsplash.com/random/800x600/?{query}"
        return jsonify({
            "answer": f"🖼️ Gambar untuk '{query}':\n{image_url}",
            "avatar": session["avatar"],
            "image_url": image_url
        })

    # /stats
    if cmd == "/stats":
        log_command("/stats")
        return jsonify({
            "answer": f"📊 Statistik:\n- Total queries: {analytics['total_queries']}\n- Command usage: {json.dumps(analytics['command_usage'], indent=2)}\n- Active sessions: {len(sessions)}",
            "avatar": session["avatar"]
        })

    # /upload (file di-handle via base64)
    if cmd == "/upload" and file_data:
        try:
            file_content = base64.b64decode(file_data['content']).decode('utf-8')
            file_type = file_data['type']
            if file_type == 'csv':
                df = pd.read_csv(io.StringIO(file_content))
                summary = df.describe().to_string()
                return jsonify({
                    "answer": f"📁 CSV uploaded!\nSummary:\n{summary}\n\nIngin analisis lebih lanjut?",
                    "avatar": session["avatar"]
                })
            elif file_type == 'json':
                data_json = json.loads(file_content)
                return jsonify({
                    "answer": f"📁 JSON uploaded!\nKeys: {list(data_json.keys())}\n\nIngin saya proses?",
                    "avatar": session["avatar"]
                })
        except Exception as e:
            return jsonify({"answer": f"❌ Error membaca file: {str(e)}"})

    # Default mode switching
    if cmd in SPECIAL_COMMANDS and cmd != "/role":
        session["mode"] = cmd.replace("/", "")
        log_command(cmd)
        return jsonify({
            "answer": f"⚡ Mode switched: {SPECIAL_COMMANDS[cmd]}",
            "avatar": session["avatar"]
        })

    # ===== PERPLEXITY API CALL =====
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": build_prompt(user_input, session),
        "max_results": 1,
        "max_tokens_per_page": 512
    }

    try:
        response = requests.post(PERPLEXITY_URL, headers=headers, json=payload, timeout=30)
        result = response.json()
        raw_answer = result.get("results", [{}])[0].get("text", "Maaf, saya belum bisa menjawab itu.")
    except Exception as e:
        raw_answer = f"⚠️ Error: {str(e)}"

    # Post-processing
    if any(word in user_input.lower() for word in ["medis", "dokter", "obat"]):
        raw_answer += "\n\n⚠️ *Disclaimer: Bukan saran medis.*"
    if any(word in user_input.lower() for word in ["investasi", "saham", "legal"]):
        raw_answer += "\n\n⚠️ *Disclaimer: Bukan saran keuangan/hukum.*"

    session["history"].append({
        "user": user_input,
        "ai": raw_answer,
        "timestamp": datetime.now().isoformat()
    })

    final_answer = raw_answer + "\n\n📌 *Ada yang bisa saya bantu lagi?*"

    return jsonify({
        "answer": final_answer,
        "avatar": session["avatar"],
        "history": session["history"][-10:],
        "session_id": session_id
    })

@app.route('/reset', methods=['POST'])
def reset_session():
    data = request.get_json()
    session_id = data.get('session_id', 'default')
    if session_id in sessions:
        sessions[session_id] = {
            "history": [],
            "mode": "normal",
            "role": None,
            "user_id": None,
            "avatar": "https://i.imgur.com/default_avatar.png"
        }
    return jsonify({"message": "Session reset", "session_id": session_id})

@app.route('/dashboard', methods=['GET'])
def dashboard():
    return '''
    <html>
    <head><title>NEXA Analytics</title></head>
    <body style="font-family: sans-serif; background: #111; color: #fff; padding: 20px;">
        <h1>📊 NEXA Dashboard</h1>
        <p>Total Queries: {}</p>
        <p>Active Sessions: {}</p>
        <p>Command Usage: {}</p>
        <p>Popular Modes: {}</p>
        <a href="/" style="color: cyan;">Back to Chat</a>
    </body>
    </html>
    '''.format(
        analytics["total_queries"],
        len(sessions),
        json.dumps(analytics["command_usage"], indent=2),
        json.dumps(analytics["popular_modes"], indent=2)
    )

# ==========================================
# SCHEDULER THREAD (sederhana)
# ==========================================
def check_schedules():
    while True:
        now = datetime.now()
        for sched_id, sched in list(schedules.items()):
            if not sched["done"]:
                sched_date = datetime.fromisoformat(sched["date"])
                if now >= sched_date:
                    sched["done"] = True
                    # Kirim notifikasi (bisa via webhook)
                    print(f"🔔 REMINDER: {sched['message']} untuk user {sched['user_id']}")
        time.sleep(60)  # cek setiap menit

threading.Thread(target=check_schedules, daemon=True).start()

# Handler untuk Vercel
def handler(request):
    return app(request)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
