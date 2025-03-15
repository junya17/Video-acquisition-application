import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import main as video_generator

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = video_generator.VIDEO_DIR
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB制限

# 動画の解像度オプション
RESOLUTIONS = {
    '720p': (1280, 720),
    '1080p': (1920, 1080),
    '480p': (854, 480)
}

@app.route('/')
def index():
    # デフォルトフレーズを取得
    default_phrases = video_generator.default_phrases
    return render_template('index.html', default_phrases=default_phrases, resolutions=RESOLUTIONS)

@app.route('/generate', methods=['POST'])
def generate():
    # フォームからデータを取得
    phrase_type = request.form.get('phrase_type', 'custom')
    
    if phrase_type == 'default':
        # デフォルトフレーズを使用
        phrase_index = int(request.form.get('default_phrase', 0))
        phrase = video_generator.default_phrases[phrase_index]
    elif phrase_type == 'random':
        # ランダムなデフォルトフレーズを使用
        import random
        phrase = random.choice(video_generator.default_phrases)
    else:
        # カスタムフレーズを使用
        phrase = request.form.get('custom_phrase', '')
    
    # 動画設定を取得
    resolution_key = request.form.get('resolution', '720p')
    resolution = RESOLUTIONS.get(resolution_key, (1280, 720))
    
    duration = int(request.form.get('duration', 5))
    fps = int(request.form.get('fps', 24))
    
    # 動画設定を作成
    video_settings = {
        'duration': duration,
        'resolution': resolution,
        'fps': fps
    }
    
    # 動画を生成
    video_path = video_generator.generate_video(phrase, video_settings)
    
    if video_path:
        # 成功した場合、結果ページにリダイレクト
        video_filename = os.path.basename(video_path)
        return redirect(url_for('result', video=video_filename))
    else:
        # 失敗した場合、エラーメッセージを表示
        return render_template('error.html', message="動画の生成に失敗しました。")

@app.route('/result')
def result():
    video = request.args.get('video', '')
    return render_template('result.html', video=video)

@app.route('/videos/<filename>')
def video_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # videosディレクトリが存在することを確認
    os.makedirs(video_generator.VIDEO_DIR, exist_ok=True)
    app.run(debug=True) 