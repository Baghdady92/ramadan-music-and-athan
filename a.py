import requests
import schedule
import time
import pygame
import os
import json
from datetime import datetime, timedelta
import threading

# Configuration
API_URL = "https://hq.alkafeel.net/Api/init/init.php?timezone=+3&long=44&lati=32&v=jsonPrayerTimes"
ADHAN_FILE = "athan.mp3"
MUSIC_FOLDER = "music_folder"
PRAYER_TIMES_FILE = 'prayer_times.json'

# Global Variables
music_files = []
current_music_index = 0
music_playing = False
music_thread = None
scheduled_prayer_times = []

# Initialize pygame mixer
pygame.mixer.pre_init(44100, -16, 2, 4096)
pygame.mixer.init()

# Fetch prayer times with caching
def fetch_prayer_times():
    today_str = datetime.now().strftime('%Y-%m-%d')

    if os.path.exists(PRAYER_TIMES_FILE):
        try:
            with open(PRAYER_TIMES_FILE, 'r') as file:
                cached_data = json.load(file)
                if cached_data.get('date') == today_str:
                    print("Loaded prayer times from cache.")
                    return cached_data['times']
        except Exception as e:
            print(f"Error reading cached prayer times: {e}")

    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()

        times = {
            "fajir": data.get("fajir"),
            "doher": data.get("doher"),
            "sunset": data.get("sunset"),
            "maghrib": data.get("maghrib")
        }

        with open(PRAYER_TIMES_FILE, 'w') as file:
            json.dump({'date': today_str, 'times': times}, file)

        print("Fetched prayer times successfully from API and cached locally.")
        return times

    except Exception as e:
        print(f"Error fetching prayer times from API: {e}")
        return {}

# Schedule prayer times
def schedule_prayer_times(prayer_times):
    global scheduled_prayer_times
    scheduled_prayer_times.clear()

    for prayer_name, prayer_time in prayer_times.items():
        if not prayer_time:
            continue

        today = datetime.now()
        hour, minute = map(int, prayer_time.split(":"))

        scheduled_time = today.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if prayer_name in ["sunset", "maghrib"]:
            scheduled_time += timedelta(hours=12)

        if scheduled_time < today:
            print(f"{prayer_name} time ({prayer_time}) has already passed today.")
            continue

        schedule_time_str = scheduled_time.strftime("%H:%M")
        schedule.every().day.at(schedule_time_str).do(play_adhan, prayer_name)
        print(f"Scheduled {prayer_name} at {schedule_time_str}")

        scheduled_prayer_times.append((prayer_name, scheduled_time))

    scheduled_prayer_times.sort(key=lambda x: x[1])

# Audio functions
def play_adhan(prayer_name):
    print(f"\nPlaying Adhan for {prayer_name}...")
    stop_music()
    play_audio_file(ADHAN_FILE, block=True)

    resume_time = datetime.now() + timedelta(minutes=15)
    resume_time_str = resume_time.strftime("%H:%M")
    schedule.every().day.at(resume_time_str).do(start_music)
    print(f"Music scheduled to resume at {resume_time_str}")

def load_music_files():
    global music_files
    music_files.clear()

    if not os.path.isdir(MUSIC_FOLDER):
        print(f"Music folder '{MUSIC_FOLDER}' not found.")
        return

    for file in os.listdir(MUSIC_FOLDER):
        if file.lower().endswith((".mp3", ".wav", ".ogg")):
            music_files.append(os.path.join(MUSIC_FOLDER, file))
    music_files.sort()
    print(f"Loaded {len(music_files)} music files.")

def start_music():
    global music_playing, music_thread

    if not music_files:
        print("No music files found, cannot start music.")
        return

    if music_playing:
        return

    print("Starting background music playback...")
    music_playing = True
    music_thread = threading.Thread(target=play_music_loop, daemon=True)
    music_thread.start()

def stop_music():
    global music_playing
    if music_playing:
        pygame.mixer.music.stop()
        music_playing = False
        print("Music stopped for Adhan.")

def play_music_loop():
    global current_music_index, music_playing

    while music_playing:
        file_to_play = music_files[current_music_index]
        pygame.mixer.music.load(file_to_play)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy() and music_playing:
            time.sleep(1)

        current_music_index = (current_music_index + 1) % len(music_files)
        if not music_playing:
            break

def play_audio_file(filepath, block=False):
    pygame.mixer.music.load(filepath)
    pygame.mixer.music.play()

    if block:
        while pygame.mixer.music.get_busy():
            time.sleep(1)

def get_next_athan():
    now = datetime.now()
    for prayer_name, p_datetime in scheduled_prayer_times:
        if p_datetime > now:
            return prayer_name, p_datetime
    return None

def main():
    load_music_files()
    start_music()

    prayer_times = fetch_prayer_times()
    schedule_prayer_times(prayer_times)

    print("Starting main loop. Waiting for prayer times...")

    while True:
        schedule.run_pending()

        next_athan = get_next_athan()
        if next_athan:
            prayer_name, next_time = next_athan
            remaining = next_time - datetime.now()

            total_seconds = int(remaining.total_seconds())
            hours, minutes, seconds = total_seconds // 3600, (total_seconds % 3600) // 60, total_seconds % 60

            countdown_str = f"Next Adhan ({prayer_name}) in {hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            countdown_str = "No more Adhans scheduled for today."

        print(countdown_str, end="\r", flush=True)
        time.sleep(1)

if __name__ == "__main__":
    main()