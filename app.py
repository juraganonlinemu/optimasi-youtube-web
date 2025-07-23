### --- APLIKASI WEB OPTIMASI YOUTUBE - VERSI FINAL --- ###

import os
import io
import json
from datetime import datetime
from collections import Counter

# Flask dan pustaka web
from flask import Flask, request, render_template, send_file
import gunicorn

# Pustaka untuk API dan file
import requests
import openpyxl
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

# --- Konfigurasi Aplikasi Flask ---
app = Flask(__name__)

# --- Atur Kunci API dari Environment Variables Hosting ---
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Konfigurasi Model Gemini (sama seperti skrip asli) ---
gemini_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model_name_to_check = 'gemini-1.5-pro-latest'
        gemini_model = genai.GenerativeModel(model_name_to_check)
        gemini_model.generate_content("test", generation_config={"temperature": 0.0})
        print(f"✅ Gemini API berhasil dikonfigurasi dengan model: {model_name_to_check}.")
    except Exception as e:
        print(f"⚠️ PERINGATAN: Gagal mengkonfigurasi Gemini API. Detail: {e}")
        gemini_model = None
else:
    print("ℹ️ Info: Kunci API Gemini tidak ditemukan. Menggunakan template fallback.")

# --- SEMUA FUNGSI PEMBANTU DARI SKRIP ASLI ---

def get_google_trends_suggestions(query: str, content_type: str = "general") -> list[str]:
    print(f"-> Menganalisis tren untuk '{query}' (simulasi)...")
    base_trends = [f"{query} {datetime.now().year}", f"tren {query}", f"apa itu {query}"]
    if content_type == "movie":
        base_trends.extend([f"{query} alur cerita", f"{query} review", f"{query} ending", f"{query} pemeran", f"{query} analisis"])
    elif content_type == "tutorial":
        base_trends.extend([f"cara {query}", f"tutorial {query}", f"panduan {query}", f"{query} untuk pemula"])
    else:
        base_trends.extend([f"review {query}", f"tips {query}", f"panduan {query}"])
    return list(set(base_trends))

def get_Youtube_results(query: str, max_results: int = 5) -> list[dict]:
    if not YOUTUBE_API_KEY:
        print("-> PERINGATAN: YouTube API Key tidak ditemukan. Menggunakan data simulasi.")
        return [{"title": f"Video Simulasi 1 tentang {query}", "description": "Deskripsi simulasi.", "videoId": "sim_id_1"}]
    
    base_url = "https://www.googleapis.com/youtube/v3/search"
    params = {"part": "snippet", "q": query, "type": "video", "maxResults": max_results, "key": YOUTUBE_API_KEY}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        return [{"title": item["snippet"]["title"], "description": item["snippet"]["description"], "videoId": item["id"]["videoId"]} for item in data.get("items", [])]
    except requests.exceptions.HTTPError as e:
        print(f"-> ERROR YouTube API: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"-> ERROR Jaringan: {e}")
        return []

def get_video_tags(video_id: str) -> list[str]:
    if not YOUTUBE_API_KEY:
        return [f"tag_simulasi_{video_id}"]
    
    base_url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "snippet", "id": video_id, "key": YOUTUBE_API_KEY}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        if not items: return []
        return items[0].get("snippet", {}).get("tags", [])
    except requests.exceptions.RequestException:
        return []

def determine_content_type(theme: str) -> str:
    theme_lower = theme.lower()
    movie_keywords = {"film", "movie", "review", "alur cerita", "trailer", "ending", "aktor", "pemeran", "sinopsis", "analisis"}
    tutorial_keywords = {"cara", "tips", "panduan", "tutorial", "belajar", "membuat", "mengatasi"}
    if any(keyword in theme_lower for keyword in movie_keywords) or (theme_lower.split()[-1].isdigit() and len(theme_lower.split()[-1]) == 4):
        return "movie"
    if any(keyword in theme_lower for keyword in tutorial_keywords):
        return "tutorial"
    return "general"

COMMON_WORDS = {"dan", "atau", "yang", "untuk", "dari", "di", "ini", "itu", "video", "terbaru", "lengkap", "dengan", "adalah", "tentang", "the", "a", "an", "is", "of", "in", "to", "for", "with", "from", "on", "at", "by", "this", "that", "it", "its", "cara", "tips", "panduan", "tutorial", "membuat", "belajar", "mengatasi", "full", "trailer", "clip", "episode", "season", "part", "vs", "film", "movie", "review", "alur", "cerita", "sinopsis", "teori", "analisis", "pemeran", "ulasan"}

def analyze_keywords(competitor_videos: list[dict]) -> list[str]:
    all_keywords = []
    print("-> Menganalisis Kata Kunci dari Kompetitor...")
    for video in competitor_videos:
        text_to_analyze = f"{video['title']} {video['description']}".lower()
        all_keywords.extend(text_to_analyze.split())
        video_tags = get_video_tags(video['videoId'])
        if video_tags:
            all_keywords.extend([tag.lower() for tag in video_tags])
            
    sanitized_keywords = [word.strip(".,?!()[]{}") for word in all_keywords]
    filtered_keywords = [word for word in sanitized_keywords if word not in COMMON_WORDS and len(word) > 3 and not word.isdigit()]
    keyword_counts = Counter(filtered_keywords)
    top_keywords = [word for word, count in keyword_counts.most_common(20)]
    print(f"-> Kata Kunci Populer: {', '.join(top_keywords)}")
    return top_keywords

def generate_content_with_gemini(theme, main_points, content_type, competitor_titles, top_keywords):
    if not gemini_model:
        return None
    print("-> Menggunakan Gemini API...")
    context_summary = f"Tema Utama Video: \"{theme}\"\nJenis Konten: {content_type.capitalize()}\nPoin Utama: {', '.join(main_points)}\nKata Kunci Relevan: {', '.join(top_keywords[:10])}\nContoh Judul Kompetitor: {'; '.join(competitor_titles[:3])}"
    
    # --- PERUBAHAN DI SINI ---
    prompt = f"""
    Anda adalah ahli strategi konten YouTube. Berdasarkan data berikut, buat metadata optimal dalam format JSON yang valid, tanpa teks tambahan sebelum atau sesudah JSON.

    {context_summary}

    PENTING: Seluruh output (judul, deskripsi, dan tag) HARUS dalam Bahasa Indonesia.

    Format JSON:
    {{
      "titles": ["Judul 1", "Judul 2", "Judul 3", "Judul 4", "Judul 5"],
      "description": "Deskripsi lengkap (sekitar 150 kata) yang mengelaborasi poin utama...",
      "tags": ["tag1", "tag2", "tag3"]
    }}
    """
    # --- AKHIR PERUBAHAN ---

    try:
        response = gemini_model.generate_content(prompt)
        clean_response_text = response.text.strip().replace("```json", "").replace("```", "")
        content = json.loads(clean_response_text)
        return content['titles'], content['description'], content['tags']
    except Exception as e:
        print(f"-> ERROR Gemini: {e}")
        return None

def generate_fallback_content(theme, main_points, content_type, top_keywords, trend_suggestions):
    print("-> Menggunakan template fallback...")
    theme_sanitized = "".join(c for c in theme if c.isalnum() or c == ' ').strip()
    if content_type == "movie":
        titles = [f"REVIEW {theme_sanitized.upper()}: Sebagus Kata Orang?", f"Alur Cerita Lengkap {theme_sanitized}", f"Fakta Tersembunyi di Film {theme_sanitized}"]
    else:
        titles = [f"CARA MUDAH {theme_sanitized.upper()}", f"Panduan Lengkap {theme_sanitized}", f"TIPS & TRIK {theme_sanitized}"]
    points_elaboration = "\n\n".join([f"➡️ **{point.strip()}**\nDalam bagian ini, kita akan membahas {point.strip().lower()}." for point in main_points])
    description = f"🚀 Di video ini, kita akan menyelami dunia **{theme_sanitized}**!\n\n👇 APA YANG AKAN ANDA PELAJARI:\n{points_elaboration}\n\n🔔 Jangan lupa untuk LIKE, KOMENTAR, dan SUBSCRIBE!\n\n#{theme_sanitized.replace(' ', '')} #{content_type}"
    tags = list(set([theme_sanitized.lower()] + top_keywords + trend_suggestions + [content_type]))
    return titles, description.strip(), tags[:25]


def create_excel_in_memory(theme, content_type, titles, description, tags):
    """Membuat file Excel di memori, bukan di disk."""
    output = io.BytesIO()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Optimasi YouTube"
    headers = ["Tema", "Jenis Konten", "Judul Rekomendasi 1", "Judul Rekomendasi 2", "Judul Rekomendasi 3", "Judul Rekomendasi 4", "Judul Rekomendasi 5", "Deskripsi Rekomendasi", "Tag Rekomendasi"]
    sheet.append(headers)
    row_data = [theme, content_type.capitalize()] + titles[:5] + [description, ", ".join(tags)]
    sheet.append(row_data)
    workbook.save(output)
    output.seek(0)
    return output

# --- RUTE APLIKASI WEB ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        theme = request.form['theme']
        main_points_str = request.form['main_points']
        main_points = [p.strip() for p in main_points_str.split(',') if p.strip()]

        print(f"Menerima permintaan untuk tema: '{theme}'")
        
        # --- Logika Optimasi Utama Dijalankan Di Sini ---
        content_type = determine_content_type(theme)
        trend_suggestions = get_google_trends_suggestions(theme, content_type)
        competitor_videos = get_Youtube_results(theme, max_results=5)
        
        top_keywords = []
        if competitor_videos:
            top_keywords = analyze_keywords(competitor_videos)
        
        competitor_titles = [v['title'] for v in competitor_videos]
        
        result = generate_content_with_gemini(theme, main_points, content_type, competitor_titles, top_keywords)
        if result:
            titles, description, tags = result
        else:
            titles, description, tags = generate_fallback_content(theme, main_points, content_type, top_keywords, trend_suggestions)
        
        # --- Membuat dan Mengirim File Excel ---
        excel_file_memory = create_excel_in_memory(theme, content_type, titles, description, tags)
        
        sanitized_theme = "".join(c for c in theme if c.isalnum()).strip()[:20]
        timestamp = datetime.now().strftime("%y%m%d")
        download_filename = f"OptYT_{sanitized_theme}_{timestamp}.xlsx"
        
        return send_file(
            excel_file_memory,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=download_filename
        )
    
    # Jika metodenya GET, tampilkan formulir HTML
    return render_template('index.html')

# Baris ini hanya untuk pengujian di komputer lokal
if __name__ == '__main__':
    app.run(debug=True)