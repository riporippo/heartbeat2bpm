import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import random
import serial
from time import sleep

# Spotify APIの認証設定
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id='',
    client_secret='',
    redirect_uri='http://localhost:8080',
    scope="user-modify-playback-state user-read-playback-state"))

def get_heart_rate():
    try:
        average = 0
        read_pulse = serial.Serial('COM6',9600,timeout=3)
        print("指を固定してください")
        sleep(3)
        for pulse in range(3):
            string = read_pulse.readline()
            print(string)
            if "No finger?" in str(string):
                average += 80
            else:
                average += int(string)
            sleep(3)
        return int(average / 3)
    except Exception as e:
        print(f"Error: 心拍数が取得できませんでした。{e}")
        default_heart_rate = 120
        print(f"デフォルトの心拍数 {default_heart_rate} BPM を使用します。")
        return default_heart_rate

def get_weather_and_pressure(city):
    api_key = ""
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

    response = requests.get(weather_url)
    data = response.json()

    if response.status_code == 200 and 'weather' in data and 'main' in data:
        weather = data['weather'][0]['main']
        pressure = data['main']['pressure']
        temperature = data['main']['temp']
        print(f"今日の{city}の天気は {weather} で、気温は {temperature}°C、気圧は {pressure} hPa です。")
        return weather, pressure
    else:
        print("Error: 天候データが取得できませんでした。レスポンス:", data)
        return None, None

def adjust_bpm_by_weather(heart_rate_bpm, weather, pressure):
    if weather == "Rain" or (pressure is not None and pressure < 1010):
        return max(heart_rate_bpm - 10, 60)
    elif weather == "Clear" and (pressure is not None and pressure > 1015):
        return min(heart_rate_bpm + 10, 160)
    else:
        return heart_rate_bpm

def get_genre_by_bpm(bpm):
    if bpm >= 60 and bpm < 80:
        return "jazz"
    elif bpm >= 80 and bpm < 110:
        return "R&B"
    elif bpm >= 110 and bpm < 130:
        return "Disco"
    elif bpm >= 130 and bpm < 160:
        return "Techno"
    else:
        return "French core"

def find_tracks_by_tempo(target_bpm, genre):
    # ランダムなオフセットで異なる曲が選ばれるように
    offset = random.randint(0, 50)
    results = sp.search(
        q=f"{genre} bpm:{target_bpm-10}-{target_bpm+10}",
        type="track",
        limit=10,
        offset=offset
    )
    tracks = results['tracks']['items']
    
    # 除外キーワードを含む曲を除外
    exclusion_keywords = ["ワークアウト", "BPM", "Workout", "EDM", "ランニング"]
    filtered_tracks = [
        track['uri'] for track in tracks
        if not any(keyword.lower() in track['name'].lower() for keyword in exclusion_keywords)
    ]
    return filtered_tracks if filtered_tracks else []

# 心拍数のBPMを取得
heart_rate_bpm = get_heart_rate()
# 天候と気圧を取得
city = "Tokyo"
weather, pressure = get_weather_and_pressure(city)

if weather and pressure:
    adjusted_bpm = adjust_bpm_by_weather(heart_rate_bpm, weather, pressure)
    
    # BPMに基づいてジャンルを決定
    genre = get_genre_by_bpm(adjusted_bpm)
    print(f"ジャンル: {genre}")

    # 選択したジャンルで曲を検索
    track_uris = find_tracks_by_tempo(adjusted_bpm, genre)

    def get_active_device_id():
        devices = sp.devices()
        for device in devices['devices']:
            if device['name'] == 'Pixel 8':
                return device['id']
        print("Error: No active device found.")
        return None

    device_id = get_active_device_id()

    if device_id and track_uris:
        sp.start_playback(device_id=device_id, uris=track_uris)
        print(f"{adjusted_bpm} BPMの{genre}曲を再生しています（天候と気圧を考慮）。")
    else:
        print("アクティブなデバイスが見つからなかったか、該当するBPMの曲が見つかりませんでした。")
else:
    print("天候と気圧のデータが取得できなかったため、選曲をスキップしました。")
