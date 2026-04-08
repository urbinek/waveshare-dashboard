import os
import json
import logging
from datetime import date, datetime, timezone
from astral.sun import sun
from astral import LocationInfo
from dateutil import tz

from modules.config_loader import config
from modules import path_manager, asset_manager
from modules import zigbee2mqtt as zigbee2mqtt_module

logger = logging.getLogger(__name__)


def _get_sunrise_sunset():
    """Oblicza czas wschodu i zachodu słońca."""
    try:
        location_config = config['location']
        loc = LocationInfo(
            "Warsaw", "Poland", "Europe/Warsaw",
            location_config['latitude'], location_config['longitude']
        )
        s = sun(loc.observer, date=date.today())
        local_tz = tz.gettz("Europe/Warsaw")
        sunrise = s['sunrise'].astimezone(local_tz).strftime('%H:%M')
        sunset = s['sunset'].astimezone(local_tz).strftime('%H:%M')
        return sunrise, sunset
    except Exception as e:
        logger.error(f"Błąd podczas obliczania czasu wschodu/zachodu słońca: {e}")
        return "--:--", "--:--"


def update_weather_data():
    """
    Tworzy ujednolicony plik weather.json z danych:
    - Airly: wilgotność, ciśnienie, CAQI
    - IMGW: temperatura powietrza ze stacji meteorologicznej
    - Zigbee2MQTT: lokalna temperatura z czujnika zewnętrznego
    - Open-Meteo: kod pogodowy WMO, ikona i opis (bezpłatne, bez klucza)
    """
    # --- Airly: wilgotność, ciśnienie ---
    airly_file_path = os.path.join(path_manager.CACHE_DIR, 'airly.json')
    humidity, pressure = "--", "--"
    try:
        with open(airly_file_path, 'r', encoding='utf-8') as f:
            airly_data = json.load(f)
        values = {item['name']: item['value']
                  for item in airly_data.get('current', {}).get('values', [])}
        humidity = round(values.get('HUMIDITY', 0)) if 'HUMIDITY' in values else "--"
        pressure = round(values.get('PRESSURE', 0)) if 'PRESSURE' in values else "--"
    except (IOError, json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Nie można odczytać lub przetworzyć pliku Airly: {e}.")

    # --- IMGW: temperatura z pobliskiej stacji meteorologicznej ---
    imgw_file_path = os.path.join(path_manager.CACHE_DIR, 'imgw.json')
    temp_imgw = "--"
    try:
        with open(imgw_file_path, 'r', encoding='utf-8') as f:
            imgw_data = json.load(f)
        val = imgw_data.get('temp_air')
        if val is not None:
            temp_imgw = round(val, 1)
    except (IOError, json.JSONDecodeError) as e:
        logger.warning(f"Plik IMGW nie jest dostępny: {e}.")

    # --- Zigbee2MQTT: lokalna temperatura z czujnika ---
    # Najpierw sprawdź dane w RAM (klient MQTT działa w tle),
    # potem fallback do pliku cache (jeśli były dane z poprzedniego uruchomienia)
    temp_local = "--"
    zigbee_ram = zigbee2mqtt_module.get_current_data()
    if zigbee_ram:
        val = zigbee_ram.get('temperature')
        if val is not None:
            temp_local = round(val, 1)
            logger.debug(f"Temperatura lokalna z RAM (MQTT): {temp_local}°C")
    else:
        # Fallback do pliku – normalny stan przy pierwszym starcie
        zigbee_file_path = os.path.join(path_manager.CACHE_DIR, 'zigbee2mqtt.json')
        try:
            with open(zigbee_file_path, 'r', encoding='utf-8') as f:
                zigbee_data = json.load(f)
            val = zigbee_data.get('temperature')
            if val is not None:
                temp_local = round(val, 1)
        except (IOError, json.JSONDecodeError):
            logger.info("Brak danych MQTT (czujnik Outdoor) – plik nie istnieje lub MQTT nie odebrał jeszcze wiadomości.")

    # --- Open-Meteo: ikona pogodowa i opis WMO ---
    open_meteo_file_path = os.path.join(path_manager.CACHE_DIR, 'open_meteo.json')
    weather_icon = None
    weather_description = "Brak danych"
    try:
        with open(open_meteo_file_path, 'r', encoding='utf-8') as f:
            meteo_data = json.load(f)
        weather_icon = meteo_data.get('icon_path')
        weather_description = meteo_data.get('description', 'Brak danych')
    except (IOError, json.JSONDecodeError) as e:
        logger.warning(f"Plik Open-Meteo nie jest dostępny: {e}.")
        # Fallback do ikony błędu synchronizacji
        weather_icon = asset_manager.get_path('icon_sync_problem')

    sunrise, sunset = _get_sunrise_sunset()

    final_weather_data = {
        "temp_local": temp_local,
        "temp_imgw": temp_imgw,
        "humidity": humidity,
        "pressure": pressure,
        "icon": weather_icon,
        "weather_description": weather_description,
        "sunrise": sunrise,
        "sunset": sunset,
        "timestamp": datetime.now(tz=timezone.utc).isoformat()
    }

    output_file_path = os.path.join(path_manager.CACHE_DIR, 'weather.json')
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(final_weather_data, f, ensure_ascii=False, indent=4)
        logger.debug("Pomyślnie zintegrowano dane pogodowe do weather.json.")
    except IOError as e:
        logger.error(f"Nie można zapisać finalnego pliku weather.json: {e}")
