import requests
import schedule
import time
import pygame
import os
from datetime import datetime, timedelta
import threading   # added import

# 1. Configuration
API_URL = "https://hq.alkafeel.net/Api/init/init.php?timezone=+3&long=44&lati=32&v=jsonPrayerTimes"

# Paths to audio files
ADHAN_FILE = "athan.mp3"  # Path to the Adhan audio
MUSIC_FOLDER = "music_folder"  # Path to the folder with continuous background music

# 2. Global Variables
music_files = []
current_music_index = 0
music_playing = False
music_thread = None   # added global music thread variable

# We'll store the scheduled prayer times here for countdown purposes
scheduled_prayer_times = []  # List of tuples like [(prayer_name, prayer_datetime), ...]

# 3. Initialize pygame mixer
pygame.mixer.pre_init(44100, -16, 2, 4096)  # (Frequency, Size, Channels, Buffer)
pygame.mixer.init()

def fetch_prayer_times():
    """
    Fetch prayer times from the given API and return as a dictionary of prayer -> time (HH:MM).
    Expected JSON structure (example):
      {
        "prayerTimes": {
          "Fajr": "05:13",
          "Sunrise": "06:34",
          "Dhuhr": "12:15",
          "Asr": "15:30",
          "Maghrib": "18:22",
          "Isha": "19:46"
        }
      }
    """
    try:
        response = requests.get(API_URL)
        data = response.json()
        
        times = data
        obj = {
            "fajir": times.get("fajir"),
            "doher": times.get("doher"),
            "sunset": times.get("sunset"),
            "maghrib": times.get("maghrib")
                    }
        print(f"Fetched prayer times successfully.\n {obj}")
        return obj
    except Exception as e:
        print(f"Error fetching prayer times: {e}")
        return {}

def schedule_prayer_times(prayer_times):
    """
    Given a dictionary of prayer times (e.g., {"Fajr":"05:13", ...}),
    schedule the Adhan for each using the 'schedule' library.
    Also populate 'scheduled_prayer_times' for countdown display.
    """
    global scheduled_prayer_times
    scheduled_prayer_times.clear()  # Clear any old data

    for prayer_name, prayer_time in prayer_times.items():
        if not prayer_time:
            continue
        
        # Parse "HH:MM" into a datetime for today
        today = datetime.now()
        hour, minute = map(int, prayer_time.split(":"))
        
        # Create a datetime object for the prayer time (today)
        scheduled_time = today.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if prayer_name in ["sunset", "maghrib"]:
            scheduled_time += timedelta(hours=12)
        
        # If time already passed today, skip or add +1 day if you want tomorrow’s time
        if scheduled_time < today:
            print(f"{prayer_name} time ({prayer_time}) has already passed today.")
            continue
        
        # Convert to a schedule time string "HH:MM"
        schedule_time_str = scheduled_time.strftime("%H:%M")
        
        # Use schedule to run play_adhan at HH:MM
        schedule.every().day.at(schedule_time_str).do(play_adhan, prayer_name)
        
        print(f"Scheduled {prayer_name} at {schedule_time_str}")
        
        # Keep track of the datetime for next-athan countdown
        scheduled_prayer_times.append((prayer_name, scheduled_time))

    # Sort by datetime so we can easily find the next upcoming prayer
    scheduled_prayer_times.sort(key=lambda x: x[1])

def play_adhan(prayer_name):
    """
    Stop the music, play the Adhan, wait 15 minutes, and then resume music.
    """
    print(f"\nPlaying Adhan for {prayer_name}...")
    stop_music()
    
    # Play the Adhan (blocking)
    play_audio_file(ADHAN_FILE, block=True)
    
    # Schedule music to resume after 15 minutes from now
    resume_time = datetime.now() + timedelta(minutes=15)
    resume_time_str = resume_time.strftime("%H:%M")
    schedule.every().day.at(resume_time_str).do(start_music)
    print(f"Music scheduled to resume at {resume_time_str}")

def load_music_files():
    """
    Load all music file paths from the MUSIC_FOLDER.
    """
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
    """
    Start (or resume) playing background music in a loop.
    """
    global music_playing, music_thread
    
    if not music_files:
        print("No music files found, cannot start music.")
        return
    
    if music_playing:
        # Already playing
        return
    
    print("Starting background music playback...")
    music_playing = True
    # Launch music loop in separate thread
    music_thread = threading.Thread(target=play_music_loop, daemon=True)
    music_thread.start()

def stop_music():
    """
    Stop the background music immediately.
    """
    global music_playing
    if music_playing:
        pygame.mixer.music.stop()
        music_playing = False
        print("Music stopped for Adhan.")

def play_music_loop():
    """
    Loop through the music files continuously.
    """
    global current_music_index, music_playing
    
    while music_playing:
        file_to_play = music_files[current_music_index]
        pygame.mixer.music.load(file_to_play)
        pygame.mixer.music.play()
        
        # Wait until the track finishes or music_playing changes
        while pygame.mixer.music.get_busy() and music_playing:
            time.sleep(1)
        
        # Move to the next track
        current_music_index = (current_music_index + 1) % len(music_files)
        
        if not music_playing:
            break

def play_audio_file(filepath, block=False):
    """
    Play a single audio file. If block=True, wait until playback finishes.
    """
    pygame.mixer.music.load(filepath)
    pygame.mixer.music.play()
    
    if block:
        while pygame.mixer.music.get_busy():
            time.sleep(1)

def get_next_athan():
    """
    Returns (prayer_name, datetime_object) for the next upcoming prayer.
    If all prayers for today have passed, returns None.
    """
    now = datetime.now()
    for prayer_name, p_datetime in scheduled_prayer_times:
        if p_datetime > now:
            return prayer_name, p_datetime
    return None

def main():
    # 1. Load background music
    load_music_files()
    
    
    # 2. Start music
    
    start_music()
    
    
    # 3. Fetch today's prayer times
    prayer_times = fetch_prayer_times()
    
    # 4. Schedule Adhan for each prayer time & store in scheduled_prayer_times
    schedule_prayer_times(prayer_times)
    
    print("Starting main loop. Waiting for prayer times...")
    
    
    
    # 5. Main loop with countdown to the next Adhan
    while True:
        # Make sure we run pending schedule tasks
        schedule.run_pending()
        
        next_athan = get_next_athan()
        if next_athan:
            prayer_name, next_time = next_athan
            now = datetime.now()
            remaining = next_time - now
            
            # Break down the remaining time
            total_seconds = int(remaining.total_seconds())
            if total_seconds < 0:
                # Just in case time has passed within the same loop iteration
                countdown_str = f"Next prayer ({prayer_name}) is now."
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                countdown_str = (f"Next Adhan ({prayer_name}) in "
                                 f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            # No more prayers scheduled today or all have passed
            countdown_str = "No more Adhans scheduled for today."
        
        # Print countdown on the same line
        print(countdown_str, end="\r", flush=True)
        
        time.sleep(1)  # Update every second

if __name__ == "__main__":
    main()
