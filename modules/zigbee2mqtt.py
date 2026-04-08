import json
import os
import logging
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from modules.config_loader import config
from modules import path_manager

logger = logging.getLogger(__name__)

_latest_data = {}
_data_lock = threading.Lock()
_mqtt_client = None


def _on_connect(client, userdata, flags, rc, properties=None):
    """Callback wywoływany po połączeniu z brokerem MQTT."""
    if rc == 0:
        topic = userdata.get('topic', 'zigbee2mqtt//Outdoor')
        logger.info(f"Połączono z brokerem MQTT. Subskrypcja tematu: {topic}")
        client.subscribe(topic)
    else:
        logger.error(f"Błąd połączenia z brokerem MQTT. Kod: {rc}")


def _on_message(client, userdata, msg):
    """Callback wywoływany przy otrzymaniu wiadomości MQTT."""
    global _latest_data
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        logger.debug(f"Otrzymano wiadomość MQTT z tematu {msg.topic}: {payload}")

        with _data_lock:
            _latest_data = {
                "topic": msg.topic,
                "temperature": payload.get("temperature"),
                "humidity": payload.get("humidity"),
                "battery": payload.get("battery"),
                "linkquality": payload.get("linkquality"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Natychmiastowy zapis do pliku cache
        _save_to_cache(_latest_data)

    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"Nie można zdekodować wiadomości MQTT: {e}")
    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania wiadomości MQTT: {e}", exc_info=True)


def _on_disconnect(client, userdata, rc, properties=None):
    """Callback wywoływany po rozłączeniu z brokerem MQTT."""
    if rc != 0:
        logger.warning(f"Nieoczekiwane rozłączenie z brokerem MQTT (kod: {rc}). Klient spróbuje się ponownie połączyć.")
    else:
        logger.info("Rozłączono z brokerem MQTT.")


def _save_to_cache(data):
    """Zapisuje odebrane dane do pliku cache."""
    file_path = os.path.join(path_manager.CACHE_DIR, 'zigbee2mqtt.json')
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        logger.error(f"Nie można zapisać danych Zigbee2MQTT do cache: {e}")


def start_mqtt_listener():
    """
    Uruchamia nieblokującego klienta MQTT subskrybującego czujnik Outdoor.
    Należy wywołać raz przy starcie aplikacji w osobnym wątku lub jako wątek tła.
    Klient automatycznie próbuje się ponownie połączyć po zerwaniu połączenia.
    """
    global _mqtt_client

    mqtt_cfg = config.get('mqtt', {})
    broker = mqtt_cfg.get('broker', 'localhost')
    port = mqtt_cfg.get('port', 1883)
    topic = mqtt_cfg.get('topic_outdoor', 'zigbee2mqtt//Outdoor')
    username = mqtt_cfg.get('username')
    password = mqtt_cfg.get('password')

    logger.info(f"Inicjalizacja klienta MQTT. Broker: {broker}:{port}, temat: {topic}")

    _mqtt_client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="waveshare-dashboard-outdoor",
        userdata={'topic': topic}
    )
    _mqtt_client.on_connect = _on_connect
    _mqtt_client.on_message = _on_message
    _mqtt_client.on_disconnect = _on_disconnect

    if username and password:
        logger.debug(f"Ustawianie uwierzytelniania MQTT dla użytkownika: {username}")
        _mqtt_client.username_pw_set(username, password)

    _mqtt_client.reconnect_delay_set(min_delay=5, max_delay=60)

    try:
        _mqtt_client.connect(broker, port, keepalive=60)
        # loop_start() uruchamia pętlę sieciową w osobnym wątku tła (daemon)
        _mqtt_client.loop_start()
        logger.info("Klient MQTT uruchomiony w tle.")
    except Exception as e:
        logger.error(f"Nie można połączyć się z brokerem MQTT ({broker}:{port}): {e}")


def stop_mqtt_listener():
    """Zatrzymuje klienta MQTT."""
    global _mqtt_client
    if _mqtt_client:
        logger.info("Zatrzymywanie klienta MQTT...")
        _mqtt_client.loop_stop()
        _mqtt_client.disconnect()
        _mqtt_client = None


def get_current_data():
    """Zwraca ostatnio odebrane dane z cache (plik lub pamięć)."""
    # Najpierw sprawdź pamięć RAM
    with _data_lock:
        if _latest_data:
            return dict(_latest_data)

    # Fallback: odczyt z pliku cache
    file_path = os.path.join(path_manager.CACHE_DIR, 'zigbee2mqtt.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return {}


if __name__ == '__main__':
    import time
    logging.basicConfig(level=logging.DEBUG)
    start_mqtt_listener()
    print("Nasłuchiwanie przez 30 sekund...")
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass
    stop_mqtt_listener()
    print("Ostatnie dane:", get_current_data())
