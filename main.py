import os
import requests
import openai
import random  # ランダム選択のためにrandomモジュールを追加
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
from gtts import gTTS
import json

# .env ファイルの読み込み
load_dotenv()

# APIキー設定
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 保存フォルダの作成
VIDEO_DIR = "videos"
AUDIO_DIR = "audio"
BGM_DIR = "bgm"
for dir_path in [VIDEO_DIR, AUDIO_DIR, BGM_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# BGMカテゴリの定義
BGM_CATEGORIES = {
    'inspirational': ['motivation', 'success', 'achieve', 'dream', 'believe'],
    'peaceful': ['nature', 'peace', 'heal', 'ocean', 'mountain'],
    'energetic': ['workout', 'push', 'forward', 'never give up'],
    'emotional': ['love', 'heart', 'feel', 'emotion'],
}

def split_phrases(text):
    """フレーズを適切に分割"""
    # まずピリオドで分割を試みる
    phrases = [phrase.strip() for phrase in text.split(". ") if phrase]
    
    # 1つしかない場合は、カンマやセミコロンでも分割を試みる
    if len(phrases) == 1 and len(phrases[0]) > 30:
        # カンマで分割
        comma_phrases = [phrase.strip() for phrase in text.split(", ") if phrase]
        if len(comma_phrases) > 1:
            return comma_phrases
        
        # セミコロンで分割
        semicolon_phrases = [phrase.strip() for phrase in text.split("; ") if phrase]
        if len(semicolon_phrases) > 1:
            return semicolon_phrases
        
        # 長い文を単語数で分割（例：10-15単語ごと）
        words = text.split()
        if len(words) > 15:
            phrases = []
            chunk_size = min(10, max(5, len(words) // 3))  # 単語数の1/3、最小5、最大10
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i+chunk_size])
                phrases.append(chunk)
            return phrases
    
    return phrases

def get_video_from_pexels(query):
    """Pexels APIから動画を取得（ランダム選択）"""
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=10"  # 取得数を増やす
    headers = {"Authorization": PEXELS_API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        videos = data.get("videos", [])
        
        if videos:
            # 取得した動画からランダムに選択
            random_video = random.choice(videos)
            
            # 選択した動画から適切な解像度のファイルを選ぶ
            hd_files = [file for file in random_video["video_files"] if file.get("height", 0) >= 720]
            
            if hd_files:
                # HD品質の動画ファイルがあればランダムに選択
                return random.choice(hd_files)["link"]
            else:
                # なければ最初のファイルを返す
                return random_video["video_files"][0]["link"]
    except requests.exceptions.RequestException as e:
        print(f"❌ 動画取得エラー: {e}")
    return None

def download_video(video_url, filename):
    """動画をダウンロード"""
    try:
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        with open(filename, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
        print(f"✅ ダウンロード完了: {filename}")
        return filename
    except requests.exceptions.RequestException as e:
        print(f"❌ ダウンロードエラー: {e}")
    return None

def create_text_to_speech(text, language_code='en'):
    """テキストを音声に変換（gTTSを使用）"""
    try:
        # 言語が日本語の場合は設定を変更
        if is_japanese(text):
            language_code = 'ja'
        
        # 音声ファイルの保存先
        audio_file = os.path.join(AUDIO_DIR, f'speech_{random.randint(1000, 9999)}.mp3')
        
        # gTTSを使用して音声を生成
        tts = gTTS(text=text, lang=language_code, slow=False)
        tts.save(audio_file)
        
        return audio_file
    except Exception as e:
        print(f"❌ 音声生成エラー: {e}")
        return None

def get_bgm_for_content(text):
    """テキストの内容に基づいて適切なBGMを選択"""
    try:
        # テキストを小文字に変換
        text_lower = text.lower()
        
        # 各カテゴリのスコアを計算
        category_scores = {}
        for category, keywords in BGM_CATEGORIES.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            category_scores[category] = score
        
        # 最高スコアのカテゴリを取得
        best_category = max(category_scores.items(), key=lambda x: x[1])[0]
        
        # カテゴリに基づいてBGMを選択
        category_dir = os.path.join(BGM_DIR, best_category)
        if os.path.exists(category_dir):
            bgm_files = [f for f in os.listdir(category_dir) if f.endswith(('.mp3', '.wav'))]
            if bgm_files:
                selected_bgm = os.path.join(category_dir, random.choice(bgm_files))
                print(f"✅ BGM選択: {best_category}/{os.path.basename(selected_bgm)}")
                return selected_bgm
        
        # カテゴリ別のBGMが見つからない場合は、ルートBGMディレクトリから選択
        root_bgm = get_random_bgm()
        if root_bgm:
            print(f"✅ BGM選択: {os.path.basename(root_bgm)}")
        return root_bgm
    except Exception as e:
        print(f"❌ BGM選択エラー: {e}")
        return None

def create_video_with_audio(video_file, text, speech_file, bgm_file, duration=5, target_resolution=(1280, 720)):
    """動画、テキスト、音声、BGMを組み合わせる"""
    try:
        # 動画の準備
        video = VideoFileClip(video_file).resize(target_resolution)
        clip_duration = min(video.duration, duration)
        video = video.subclip(0, clip_duration)
        
        # テキストの準備（既存のコードと同じ）
        aspect_ratio = target_resolution[0] / target_resolution[1]
        fontsize = int(target_resolution[1] * 0.05)
        text_position = ('center', 0.4) if aspect_ratio < 1 else ('center', 'center')
        
        txt_clip = TextClip(text, fontsize=fontsize, color='white', font='Arial',
                           stroke_color='black', stroke_width=2)
        txt_clip = txt_clip.set_position(text_position).set_duration(clip_duration)
        
        # 音声の準備
        speech_audio = AudioFileClip(speech_file)
        
        # BGMの準備
        if bgm_file:
            bgm = AudioFileClip(bgm_file)
            # BGMを動画の長さに合わせる
            if bgm.duration < clip_duration:
                bgm = bgm.loop(duration=clip_duration)
            else:
                bgm = bgm.subclip(0, clip_duration)
            # BGMの音量を下げる
            bgm = bgm.volumex(0.3)
            
            # 音声とBGMを合成
            final_audio = CompositeVideoClip([speech_audio, bgm]).set_duration(clip_duration)
        else:
            final_audio = speech_audio
        
        # 動画、テキスト、音声を合成
        final = CompositeVideoClip([video, txt_clip])
        final = final.set_audio(final_audio)
        
        return final
    except Exception as e:
        print(f"❌ 動画処理エラー: {e}")
        return None

def is_japanese(text):
    """テキストに日本語が含まれているかを判定"""
    # 日本語の文字コード範囲をチェック
    for char in text:
        # ひらがな、カタカナ、漢字の範囲
        if '\u3040' <= char <= '\u30ff' or '\u4e00' <= char <= '\u9fff':
            return True
    return False

def get_english_keywords(japanese_text):
    """日本語テキストから英語のキーワードを取得（簡易版）"""
    # 日本語フレーズに対応する英語キーワード
    japanese_to_english = {
        "諦め": "never give up",
        "頑張": "perseverance",
        "努力": "hard work",
        "成功": "success",
        "夢": "dream",
        "信じ": "believe",
        "自然": "nature",
        "海": "ocean",
        "山": "mountain",
        "平和": "peace",
        "心": "heart",
        "癒": "healing",
        "愛": "love",
        "希望": "hope",
        "未来": "future",
        "幸せ": "happiness",
        "喜び": "joy",
        "感謝": "gratitude",
        "挑戦": "challenge",
        "勇気": "courage",
        "強さ": "strength",
        "美しい": "beautiful",
        "素晴らしい": "wonderful",
        "前向き": "positive",
        "進む": "moving forward"
    }
    
    # 日本語テキストに含まれるキーワードを検索
    english_keywords = []
    for jp_word, en_word in japanese_to_english.items():
        if jp_word in japanese_text:
            english_keywords.append(en_word)
    
    # キーワードが見つからない場合はデフォルトのキーワード
    if not english_keywords:
        english_keywords = ["inspiration", "motivation", "nature"]
    
    return english_keywords

def download_video_for_phrase(phrase):
    """フレーズに基づいて動画を検索してダウンロード"""
    # 日本語かどうかを判定
    is_jp = is_japanese(phrase)
    
    # 検索クエリを最適化
    if is_jp:
        # 日本語の場合は英語キーワードに変換
        english_keywords = get_english_keywords(phrase)
        search_queries = english_keywords + ["inspiration", "motivation", "nature"]
        print(f"日本語フレーズを検出: '{phrase}'")
        print(f"英語キーワードに変換: {', '.join(english_keywords)}")
    else:
        # 英語の場合は従来の方法
        words = phrase.split()
        search_queries = [
            " ".join(words[:3]) if len(words) > 3 else phrase,  # 最初の3単語
            " ".join(words[:2]) if len(words) >= 2 else phrase,  # 最初の2単語
            words[0] if words else "nature",                     # 最初の1単語
            "inspiration" if "inspire" in phrase.lower() else None,  # インスピレーション関連
            "success" if any(w in phrase.lower() for w in ["success", "achieve", "goal"]) else None,  # 成功関連
            "motivation" if any(w in phrase.lower() for w in ["motivate", "push", "forward"]) else None,  # モチベーション関連
            "nature"  # 最終バックアップ
        ]
        # Noneを除去
        search_queries = [q for q in search_queries if q]
    
    # 各クエリを試す
    for query in search_queries:
        video_url = get_video_from_pexels(query)
        if video_url:
            print(f"✅ クエリ '{query}' で動画を見つけました")
            filename = os.path.join(VIDEO_DIR, f"video_{random.randint(1000, 9999)}.mp4")
            if download_video(video_url, filename):
                return filename
    
    print(f"❌ フレーズ '{phrase}' に対する動画が見つかりませんでした")
    return None

def generate_video(text, video_settings=None):
    if video_settings is None:
        video_settings = {
            'duration': 5,
            'resolution': (1280, 720),
            'fps': 24
        }
    
    try:
        phrases = split_phrases(text)
        print(f"\n{len(phrases)}個のフレーズに分割しました:")
        for i, phrase in enumerate(phrases, 1):
            print(f"フレーズ {i}: {phrase}")
        
        video_files = []
        for i, phrase in enumerate(phrases):
            # 動画のダウンロード
            video_file = download_video_for_phrase(phrase)
            if video_file:
                try:
                    # 音声の生成を試みる
                    speech_file = create_text_to_speech(phrase)
                except Exception as e:
                    print(f"音声生成をスキップします: {e}")
                    speech_file = None
                
                # BGMの選択
                bgm_file = get_bgm_for_content(phrase)
                
                if speech_file:
                    # 音声付きの動画を生成
                    final_clip = create_video_with_audio(
                        video_file,
                        phrase,
                        speech_file,
                        bgm_file,
                        duration=video_settings['duration'],
                        target_resolution=video_settings['resolution']
                    )
                else:
                    # 音声なしの動画を生成
                    final_clip = create_video_without_audio(
                        video_file,
                        phrase,
                        bgm_file,
                        duration=video_settings['duration'],
                        target_resolution=video_settings['resolution']
                    )
                
                if final_clip:
                    temp_output = os.path.join(VIDEO_DIR, f'temp_video_{i}.mp4')
                    final_clip.write_videofile(
                        temp_output,
                        fps=video_settings['fps'],
                        audio_codec='aac'
                    )
                    video_files.append(temp_output)
                    
                    # 使用済みの音声ファイルを削除
                    if speech_file and os.path.exists(speech_file):
                        try:
                            os.remove(speech_file)
                        except:
                            pass
        
        if video_files:
            # 最終的な動画を生成
            final_video_path = os.path.join(VIDEO_DIR, 'final_video.mp4')
            clips = [VideoFileClip(f) for f in video_files]
            final_video = concatenate_videoclips(clips)
            
            # 最終動画を書き出し
            final_video.write_videofile(
                final_video_path,
                fps=video_settings['fps'],
                audio_codec='aac'
            )
            
            # 一時ファイルを削除
            for file in video_files:
                try:
                    os.remove(file)
                except:
                    pass
            
            return final_video_path
            
    except Exception as e:
        print(f"❌ 動画生成エラー: {e}")
        return None

def create_video_without_audio(video_file, text, bgm_file, duration=5, target_resolution=(1280, 720)):
    """音声なしで動画、テキスト、BGMを組み合わせる"""
    try:
        # 動画の準備
        video = VideoFileClip(video_file).resize(target_resolution)
        clip_duration = min(video.duration, duration)
        video = video.subclip(0, clip_duration)
        
        # テキストの準備
        aspect_ratio = target_resolution[0] / target_resolution[1]
        fontsize = int(target_resolution[1] * 0.05)
        text_position = ('center', 0.4) if aspect_ratio < 1 else ('center', 'center')
        
        txt_clip = TextClip(text, fontsize=fontsize, color='white', font='Arial',
                           stroke_color='black', stroke_width=2)
        txt_clip = txt_clip.set_position(text_position).set_duration(clip_duration)
        
        # BGMの準備
        if bgm_file and os.path.exists(bgm_file):
            try:
                bgm = AudioFileClip(bgm_file)
                # BGMを動画の長さに合わせる
                if bgm.duration < clip_duration:
                    bgm = bgm.loop(duration=clip_duration)
                else:
                    bgm = bgm.subclip(0, clip_duration)
                # BGMの音量を調整
                bgm = bgm.volumex(0.5)  # 音声がないので、BGMの音量を少し上げる
                
                # 動画とテキストを合成
                final = CompositeVideoClip([video, txt_clip])
                final = final.set_audio(bgm)
            except Exception as e:
                print(f"❌ BGM処理エラー: {e}")
                final = CompositeVideoClip([video, txt_clip])
        else:
            # BGMなしの場合
            final = CompositeVideoClip([video, txt_clip])
        
        return final
    except Exception as e:
        print(f"❌ 動画処理エラー: {e}")
        return None

def get_random_bgm():
    """ランダムなBGMファイルを返す関数"""
    # BGMフォルダのパスを設定
    bgm_dir = os.path.join(os.path.dirname(__file__), 'bgm')
    os.makedirs(bgm_dir, exist_ok=True)
    
    # BGMファイルのリストを取得
    bgm_files = [f for f in os.listdir(bgm_dir) if f.endswith(('.mp3', '.wav'))]
    
    if bgm_files:
        # ランダムにBGMを選択
        import random
        return os.path.join(bgm_dir, random.choice(bgm_files))
    
    return None  # BGMが見つからない場合はNoneを返す

# テスト用のフレーズ
default_phrases = [
    # 英語のフレーズ
    "Never give up. Keep pushing forward. Believe in yourself.",
    "Success comes to those who persevere. Dreams become reality with hard work.",
    "Nature heals the soul. Ocean waves bring peace. Mountains inspire greatness.",
    # 日本語のフレーズ
    "諦めないで。前に進み続けよう。自分を信じて。",
    "成功は努力する人に訪れる。夢は努力によって現実になる。",
    "自然は心を癒す。海の波は平和をもたらす。山々は偉大さを与える。"
]

def get_user_input():
    """ユーザーからフレーズを入力してもらう"""
    print("\n===== 動画生成プログラム =====")
    print("1. デフォルトフレーズを使用")
    print("2. ランダムなデフォルトフレーズを使用")
    print("3. 自分でフレーズを入力")
    
    choice = input("\n選択してください (1-3): ").strip()
    
    if choice == "1":
        # すべてのデフォルトフレーズを表示
        print("\nデフォルトフレーズ一覧:")
        for i, phrase in enumerate(default_phrases):
            print(f"{i+1}. {phrase}")
        
        # 使用するフレーズを選択
        while True:
            try:
                idx = int(input("\n使用するフレーズの番号を選択してください: ").strip()) - 1
                if 0 <= idx < len(default_phrases):
                    return default_phrases[idx]
                else:
                    print("有効な番号を入力してください。")
            except ValueError:
                print("数字を入力してください。")
    
    elif choice == "2":
        # ランダムなデフォルトフレーズを選択
        selected = random.choice(default_phrases)
        print(f"\n選択されたフレーズ: {selected}")
        return selected
    
    elif choice == "3":
        # ユーザーが自分でフレーズを入力
        print("\nフレーズを入力してください。")
        print("ヒント: 複数のフレーズに分割するには以下の方法があります:")
        print("- ピリオド(.)で区切る: 'Never give up. Keep pushing forward. Believe in yourself.'")
        print("- カンマ(,)で区切る: 'Success is not found at the finish line, but in every step forward'")
        print("- セミコロン(;)で区切る: 'Dream big; Work hard; Stay focused'")
        print("- 長い文は自動的に複数のフレーズに分割されます")
        print("例1: 'Never give up. Keep pushing forward. Believe in yourself.'")
        print("例2: '諦めないで。前に進み続けよう。自分を信じて。'")
        
        user_phrase = input("\nフレーズ: ").strip()
        return user_phrase
    
    else:
        print("\n無効な選択です。ランダムなフレーズを使用します。")
        selected = random.choice(default_phrases)
        print(f"選択されたフレーズ: {selected}")
        return selected

# メイン処理
if __name__ == "__main__":
    # ユーザー入力を取得
    phrase = get_user_input()
    
    # 動画生成
    print(f"\n===== 以下のフレーズで動画を生成します =====\n{phrase}\n")
    generate_video(phrase)
