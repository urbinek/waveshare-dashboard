import logging
import threading
import argparse
import os
import sys
import datetime
import json
from apscheduler.schedulers.blocking import BlockingScheduler
from modules import time, weather, google_calendar, display, path_manager, startup_screens, asset_manager, airly, imgw, open_meteo, zigbee2mqtt
from modules.config_loader import config

class CenteredFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style='%', module_width=16, level_width=8):
        super().__init__(fmt, datefmt, style)
        self.module_width = module_width
        self.level_width = level_width

    def format(self, record):
        record.module_centered = record.module.center(self.module_width)
        record.levelname_centered = record.levelname.center(self.level_width)
        return super().format(record)


should_flip = False


def update_all_data_sources(refresh_intervals, last_update_times, verbose_mode=False):
    logging.info("Rozpoczynanie aktualizacji wszystkich źródeł danych...")
    now = datetime.datetime.now()

    # IMGW – temperatura z pobliskiej stacji meteorologicznej
    imgw_interval = datetime.timedelta(minutes=refresh_intervals.get('imgw_minutes', 60))
    if now - last_update_times.get('imgw', datetime.datetime.min) >= imgw_interval:
        imgw_thread = threading.Thread(target=imgw.update_imgw_data, args=(verbose_mode,))
        imgw_thread.start()
        imgw_thread.join()
        last_update_times['imgw'] = now
    else:
        logging.info(f"Pominięto aktualizację IMGW. Następna aktualizacja za {(imgw_interval - (now - last_update_times.get('imgw', datetime.datetime.min))).total_seconds() / 60:.1f} minut.")

    # Open-Meteo – ikony pogodowe WMO (bezpłatne, bez klucza)
    open_meteo_interval = datetime.timedelta(minutes=refresh_intervals.get('open_meteo_minutes', 60))
    if now - last_update_times.get('open_meteo', datetime.datetime.min) >= open_meteo_interval:
        open_meteo_thread = threading.Thread(target=open_meteo.update_open_meteo_data, args=(verbose_mode,))
        open_meteo_thread.start()
        open_meteo_thread.join()
        last_update_times['open_meteo'] = now
    else:
        logging.info(f"Pominięto aktualizację Open-Meteo. Następna aktualizacja za {(open_meteo_interval - (now - last_update_times.get('open_meteo', datetime.datetime.min))).total_seconds() / 60:.1f} minut.")

    # Airly
    airly_interval = datetime.timedelta(minutes=refresh_intervals.get('airly_minutes', 15))
    if now - last_update_times.get('airly', datetime.datetime.min) >= airly_interval:
        airly_thread = threading.Thread(target=airly.update_airly_data, args=(verbose_mode,))
        airly_thread.start()
        airly_thread.join()
        last_update_times['airly'] = now
    else:
        logging.info(f"Pominięto aktualizację Airly. Następna aktualizacja za {(airly_interval - (now - last_update_times.get('airly', datetime.datetime.min))).total_seconds() / 60:.1f} minut.")

    # Google Calendar
    google_calendar_interval = datetime.timedelta(minutes=refresh_intervals.get('google_calendar_minutes', 1))
    if now - last_update_times.get('google_calendar', datetime.datetime.min) >= google_calendar_interval:
        google_calendar_thread = threading.Thread(target=google_calendar.update_calendar_data, args=(verbose_mode,))
        google_calendar_thread.start()
        google_calendar_thread.join()
        last_update_times['google_calendar'] = now
    else:
        logging.info(f"Pominięto aktualizację Google Calendar. Następna aktualizacja za {(google_calendar_interval - (now - last_update_times.get('google_calendar', datetime.datetime.min))).total_seconds() / 60:.1f} minut.")

    time.update_time_data()
    weather.update_weather_data()
    logging.info("Zakończono aktualizację wszystkich źródeł danych.")

def deep_refresh_job(layout_config, refresh_intervals, last_update_times, draw_borders_flag=False, verbose_mode=False):
    try:
        logging.info("Rozpoczynanie zaplanowanego, głębokiego odświeżenia ekranu.")
        update_all_data_sources(refresh_intervals, last_update_times, verbose_mode)
        display.update_display(
            layout_config,
            force_full_refresh=True,
            draw_borders=draw_borders_flag,
            apply_pixel_shift=True,
            flip=should_flip
        )
    except Exception as e:
        logging.error(f"Błąd podczas głębokiego odświeżenia: {e}", exc_info=True)

def main_update_job(layout_config, refresh_intervals, last_update_times, draw_borders_flag=False, verbose_mode=False):
    try:
        logging.info("Rozpoczynanie cogodzinnej, standardowej aktualizacji.")
        update_all_data_sources(refresh_intervals, last_update_times, verbose_mode)
        display.update_display(
            layout_config,
            force_full_refresh=False,
            draw_borders=draw_borders_flag,
            apply_pixel_shift=False,
            flip=should_flip
        )
    except Exception as e:
        logging.error(f"Błąd podczas głównej aktualizacji: {e}", exc_info=True)

def time_update_job(layout_config, draw_borders_flag=False):
    now = datetime.datetime.now()
    if now.hour == 21 and now.minute == 37:
        logging.info("Aktywacja Easter Egga...")
        try:
            startup_screens.display_easter_egg(display.EPD_LOCK, flip=should_flip)
        except Exception as e:
            logging.error(f"Błąd podczas wyświetlania Easter Egga: {e}", exc_info=True)
    else:
        logging.debug("Uruchamianie częściowej aktualizacji ekranu (tylko czas)...")
        try:
            time.update_time_data()
            weather.update_weather_data()  # odświeża temp. z MQTT bez zapytań API
            display.partial_update_time(layout_config, draw_borders=draw_borders_flag, flip=should_flip)
        except Exception as e:
            logging.error(f"Błąd podczas częściowej aktualizacji: {e}", exc_info=True)

def main():
    parser = argparse.ArgumentParser(description="Waveshare E-Paper Dashboard")
    parser.add_argument('--draw-borders', action='store_true', help='Rysuje granice wokół paneli.')
    parser.add_argument('--service', action='store_true', help='Optymalizuje logowanie dla systemd.')
    parser.add_argument('--2137', dest='show_easter_egg_on_start', action='store_true', help='Wyświetla Easter Egg przy starcie.')
    parser.add_argument('--no-splash', action='store_true', help='Pomija ekran powitalny.')
    parser.add_argument('--verbose', action='store_true', help='Włącza logowanie DEBUG.')
    parser.add_argument('--flip', action='store_true', help='Obraca obraz o 180 stopni.')
    args = parser.parse_args()

    log_format = '[%(module_centered)s][%(levelname_centered)s] %(message)s' if args.service else '%(asctime)s [%(module_centered)s][%(levelname_centered)s] %(message)s'
    formatter = CenteredFormatter(fmt=log_format, datefmt='%Y-%m-%d %H:%M:%S', module_width=15, level_width=8)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    if not args.verbose:
        logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    if args.service and not args.verbose:
        logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
        logging.getLogger('apscheduler.scheduler').setLevel(logging.WARNING)

    logging.info("--- Inicjalizacja Dashboardu Waveshare ---")

    layout_config = config.get('panels', {})
    if not layout_config:
        logging.critical("Brak konfiguracji layoutu w pliku config.yaml. Aplikacja nie może kontynuować.")
        sys.exit(1)

    refresh_intervals = config.get('refresh_intervals', {})
    if not refresh_intervals:
        logging.warning("Brak konfiguracji interwałów odświeżania w pliku config.yaml. Użycie wartości domyślnych.")
        refresh_intervals = {
            'imgw_minutes': 60,
            'open_meteo_minutes': 60,
            'airly_minutes': 16,
            'google_calendar_minutes': 1
        }

    LAST_UPDATE_TIMES_FILE = os.path.join(path_manager.CACHE_DIR, 'last_update_times.json')

    def _save_last_update_times(last_update_times_data):
        logger.info("Zapisywanie czasów ostatniej aktualizacji...")
        try:
            serializable_times = {k: v.isoformat() for k, v in last_update_times_data.items()}
            with open(LAST_UPDATE_TIMES_FILE, 'w', encoding='utf-8') as f:
                json.dump(serializable_times, f, ensure_ascii=False, indent=4)
            logger.info("Pomyślnie zapisano czasy ostatniej aktualizacji.")
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania czasów ostatniej aktualizacji: {e}", exc_info=True)

    def _load_last_update_times():
        logger.info("Wczytywanie czasów ostatniej aktualizacji...")
        if os.path.exists(LAST_UPDATE_TIMES_FILE):
            try:
                with open(LAST_UPDATE_TIMES_FILE, 'r', encoding='utf-8') as f:
                    loaded_times_str = json.load(f)
                loaded_times = {}
                for k, v in loaded_times_str.items():
                    try:
                        # Try parsing with microseconds
                        loaded_times[k] = datetime.datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%f")
                    except ValueError:
                        # If microseconds are not present, try parsing without them
                        loaded_times[k] = datetime.datetime.strptime(v, "%Y-%m-%dT%H:%M:%S")
                logger.info("Pomyślnie wczytano czasy ostatniej aktualizacji.")
                return loaded_times
            except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Nie można wczytać lub przetworzyć pliku czasów ostatniej aktualizacji ({e}). Zostaną użyte domyślne wartości.")
                return {}
        logger.info("Plik czasów ostatniej aktualizacji nie istnieje. Zostaną użyte domyślne wartości.")
        return {}

    # Load last update times or initialize
    loaded_times = _load_last_update_times()
    last_update_times = {
        'imgw': loaded_times.get('imgw', datetime.datetime.min),
        'open_meteo': loaded_times.get('open_meteo', datetime.datetime.min),
        'airly': loaded_times.get('airly', datetime.datetime.min),
        'google_calendar': loaded_times.get('google_calendar', datetime.datetime.min)
    }

    try:
        os.makedirs(path_manager.CACHE_DIR, exist_ok=True)
        asset_manager.sync_assets_to_cache()
        asset_manager.initialize_runtime_paths()
        if not asset_manager.verify_assets():
            logging.critical("Weryfikacja zasobów nie powiodła się. Sprawdź logi.")
            sys.exit(1)
    except Exception as e:
        logging.critical(f"Błąd krytyczny podczas inicjalizacji zasobów: {e}.", exc_info=True)
        sys.exit(1)

    # Uruchomienie klienta MQTT w tle (odbiera dane z czujnika Outdoor na bieżąco)
    logging.info("Uruchamianie klienta MQTT (Zigbee2MQTT / Outdoor)...")
    zigbee2mqtt.start_mqtt_listener()

    global should_flip
    should_flip = config['app'].get('flip_display', False) or args.flip

    splash_thread = None
    if args.show_easter_egg_on_start:
        splash_thread = threading.Thread(target=startup_screens.display_easter_egg, args=(display.EPD_LOCK, should_flip), name="EasterEggThread")
    elif not args.no_splash:
        splash_thread = threading.Thread(target=startup_screens.display_splash_screen, args=(display.EPD_LOCK, should_flip), name="SplashThread")

    if splash_thread:
        splash_thread.start()

    update_all_data_sources(refresh_intervals, last_update_times, args.verbose)

    if splash_thread:
        logging.info("Oczekiwanie na zakończenie ekranu powitalnego...")
        splash_thread.join()

    logging.info("Wykonywanie pierwszego, pełnego renderowania ekranu...")
    display.update_display(
        layout_config,
        force_full_refresh=True,
        draw_borders=args.draw_borders,
        apply_pixel_shift=True,
        flip=should_flip)
    logging.info("Pierwsze renderowanie zakończone.")

    scheduler = BlockingScheduler(timezone="Europe/Warsaw")
    scheduler.add_job(time_update_job, 'cron', minute='*', second=1, id='time_update_job', kwargs={'layout_config': layout_config, 'draw_borders_flag': args.draw_borders})
    scheduler.add_job(main_update_job, 'cron', hour='0-2,4-23', minute=0, second=5, id='main_update_job', kwargs={'layout_config': layout_config, 'draw_borders_flag': args.draw_borders, 'verbose_mode': args.verbose, 'refresh_intervals': refresh_intervals, 'last_update_times': last_update_times})
    scheduler.add_job(deep_refresh_job, 'cron', hour=0, minute=0, second=5, id='deep_refresh_job', kwargs={'layout_config': layout_config, 'draw_borders_flag': args.draw_borders, 'verbose_mode': args.verbose, 'refresh_intervals': refresh_intervals, 'last_update_times': last_update_times})

    logging.info("--- Harmonogram uruchomiony. Aplikacja działa poprawnie. ---")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Otrzymano sygnał zamknięcia. Czyszczenie ekranu...")
        display.clear_display()
        logging.info("Aplikacja zamknięta.")
    finally:
        zigbee2mqtt.stop_mqtt_listener()
        _save_last_update_times(last_update_times)


if __name__ == "__main__":
    main()
