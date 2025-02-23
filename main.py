import requests  # kept for context
import json
import os
import time
import datetime
import sys
import logging
import ssl  # still available if needed
# Removed: asyncio, aiohttp

def get_athan_times():
    url = "https://hq.alkafeel.net/Api/init/init.php?timezone=+3&long=44&lati=32&v=jsonPrayerTimes"
    response = requests.get(url, verify=False)  # disable certificate verification
    data = response.json()
    print(data)
    # sample output remains unchanged
    return data

def play_athan():
    try:
        os.system("afplay athan.mp3")
    except Exception as e:
        logging.error("Failed to play athan: %s", e)

def check_and_play_athan(prayer_times):
    now = datetime.datetime.now()
    current_time = f"{now.hour}:{now.minute:02d}"
    for key in ['fajir', 'sunrise', 'doher', 'sunset', 'maghrib']:
        prayer_time = prayer_times.get(key)
        if prayer_time and prayer_time.strip() == current_time:
            play_athan()

def get_next_prayer_time(prayer_times):
    now = datetime.datetime.now()
    next_prayer = None
    next_prayer_name = None
    for key in ['fajir', 'sunrise', 'doher', 'sunset', 'maghrib']:
        p_time_str = prayer_times.get(key)
        if p_time_str:
            try:
                hour, minute = map(int, p_time_str.strip().split(':'))
                pt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if pt <= now:
                    pt += datetime.timedelta(days=1)
                if not next_prayer or pt < next_prayer:
                    next_prayer = pt
                    next_prayer_name = key
            except Exception:
                continue
    return next_prayer_name, next_prayer

def main_loop():
    prayer_times = get_athan_times()
    while True:
        check_and_play_athan(prayer_times)
        name, next_prayer = get_next_prayer_time(prayer_times)
        if next_prayer:
            time_left = next_prayer - datetime.datetime.now()
            print(f"Next prayer '{name}' in {time_left}")
        time.sleep(10)

if __name__ == '__main__':
    main_loop()


