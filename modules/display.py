import logging
import os
import json
import sys
import textwrap
import random
import threading
from PIL import Image, ImageDraw, ImageChops
from filelock import FileLock

from modules.config_loader import config
from modules import path_manager, drawing_utils, asset_manager
from modules.panels import time_panel, weather_panel, events_panel, calendar_panel

# Zmieniono na sterownik dla wyświetlacza czarno-białego
from waveshare_epd import epd7in5_V2

EPD_WIDTH = epd7in5_V2.EPD_WIDTH
EPD_HEIGHT = epd7in5_V2.EPD_HEIGHT

# Używamy jednego pliku cache dla obrazu w skali szarości
IMAGE_PATH = os.path.join(path_manager.CACHE_DIR, 'image.png')
IMAGE_LOCK_PATH = os.path.join(path_manager.CACHE_DIR, 'image.lock')

EPD_LOCK = threading.Lock()
_FLIP_LOGGED = False

def _shift_image(image, dx, dy):
    """Przesuwa obraz o (dx, dy) pikseli, wypełniając tło białym kolorem."""
    shifted_image = Image.new(image.mode, image.size, drawing_utils.WHITE)
    shifted_image.paste(image, (dx, dy))
    return shifted_image

def safe_read_json(file_name, default_data=None):
    """Bezpiecznie wczytuje dane z pliku JSON."""
    if default_data is None:
        default_data = {}
    file_path = os.path.join(path_manager.CACHE_DIR, file_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logging.warning(f"Nie można odczytać pliku {file_path}: {e}. Używam danych domyślnych.")
        return default_data

def generate_image(layout_config, draw_borders=False):
    """Generuje obraz w skali szarości do wyświetlenia."""
    time_data = safe_read_json('time.json', {'time': '??:??', 'date': 'Brak daty', 'weekday': 'Brak dnia'})
    weather_data = safe_read_json('weather.json', {
        'icon': asset_manager.get_path('icon_sync_problem'),
        'temp_local': '--', 'temp_imgw': '--',
        'sunrise': '--:--', 'sunset': '--:--',
        'humidity': '--', 'pressure': '--',
        'weather_description': ''
    })
    airly_data = safe_read_json('airly.json', {
        "current": {"indexes": [{"name": "AIRLY_CAQI", "value": 0, "level": "UNKNOWN", "description": "Brak danych"}]}
    })
    calendar_data = safe_read_json('calendar.json', {
        'upcoming_events': [],
        'unusual_holiday': '', 'unusual_holiday_desc': '',
        'month_calendar': []
    })

    # Tworzymy jeden obraz w trybie 'L' (skala szarości)
    image = Image.new('L', (EPD_WIDTH, EPD_HEIGHT), drawing_utils.WHITE)
    draw = ImageDraw.Draw(image)

    fonts = drawing_utils.load_fonts()

    # Przekazujemy ten sam obiekt `draw` do wszystkich paneli.
    # Panele muszą zostać zaktualizowane, aby używać kolorów z `drawing_utils`.
    if layout_config.get('time', {}).get('enabled', True):
        time_panel.draw_panel(image, draw, time_data, weather_data, fonts, layout_config['time'])
    else:
        logging.info("Panel 'time' jest wyłączony w konfiguracji. Pomijanie.")

    if layout_config.get('weather_and_air', {}).get('enabled', True):
        weather_panel.draw_panel(image, draw, weather_data, airly_data, fonts, layout_config['weather_and_air'])
    else:
        logging.info("Panel 'weather_and_air' jest wyłączony w konfiguracji. Pomijanie.")

    if calendar_data.get('error') == 'AUTH_ERROR':
        error_message = "Błąd autoryzacji Kalendarza Google. Uruchom skrypt `modules/google_calendar.py` ręcznie."
        if layout_config.get('calendar', {}).get('enabled', True):
            drawing_utils.draw_error_message(draw, error_message, fonts, layout_config['calendar'])
        if layout_config.get('events', {}).get('enabled', True):
            drawing_utils.draw_error_message(draw, error_message, fonts, layout_config['events'])
    else:
        if layout_config.get('events', {}).get('enabled', True):
            events_panel.draw_panel(image, draw, calendar_data, fonts, layout_config['events'])
        if layout_config.get('calendar', {}).get('enabled', True):
            calendar_panel.draw_panel(draw, calendar_data, fonts, layout_config['calendar'])

    if draw_borders:
        logging.info("Rysowanie granic paneli (tryb deweloperski).")
        for panel_name, panel_config in layout_config.items():
            if panel_config.get('enabled', True) and 'rect' in panel_config:
                draw.rectangle(panel_config['rect'], outline=drawing_utils.BLACK)

    unusual_holiday_title = calendar_data.get('unusual_holiday', '')
    unusual_holiday_desc = calendar_data.get('unusual_holiday_desc', '')

    if unusual_holiday_title and "Brak nietypowych świąt" not in unusual_holiday_title:
        logging.debug(f"Rysowanie nietypowego święta: '{unusual_holiday_title}'")
        font_title = fonts.get('small_bold')
        font_desc = fonts.get('small')

        unusual_holiday_config = config.get('unusual_holiday', {})
        y_offset = unusual_holiday_config.get('y_offset', 0)

        y_start_area = 400
        area_height = EPD_HEIGHT - y_start_area
        y_center_area = y_start_area + area_height // 2

        max_width_chars_title = 45
        max_width_chars_desc = 55

        wrapped_title = textwrap.wrap(unusual_holiday_title, width=max_width_chars_title)
        title_line_height = font_title.getbbox("A")[3] - font_title.getbbox("A")[1] + 5
        total_title_height = len(wrapped_title) * title_line_height

        wrapped_desc = []
        total_desc_height = 0
        if unusual_holiday_desc:
            wrapped_desc = textwrap.wrap(unusual_holiday_desc, width=max_width_chars_desc)
            desc_line_height = font_desc.getbbox("A")[3] - font_desc.getbbox("A")[1] + 4
            total_desc_height = len(wrapped_desc) * desc_line_height + 5

        total_block_height = total_title_height + total_desc_height

        # Przesunięcie o -20px w górę + dodatkowy offset z config.yaml
        current_y = y_center_area - total_block_height // 2 - 10 + y_offset

        for line in wrapped_title:
            draw.text((EPD_WIDTH // 2, current_y), line, font=font_title, fill=drawing_utils.BLACK, anchor="mt")
            current_y += title_line_height

        if wrapped_desc:
            current_y += 5
            for line in wrapped_desc:
                draw.text((EPD_WIDTH // 2, current_y), line, font=font_desc, fill=drawing_utils.BLACK, anchor="mt")
                current_y += desc_line_height
    return image

def _execute_display_update(img, mode, flip, clear_screen=False, rect=None, quiet=False):
    """
    Prywatna funkcja pomocnicza do obsługi komunikacji z wyświetlaczem E-Ink.
    """
    global _FLIP_LOGGED
    logging.debug(f"_execute_display_update: Rozpoczęcie dla trybu: {mode}, flip: {flip}, rect: {rect}")
    try:
        with EPD_LOCK:
            if mode == 'full':
                log_level = logging.DEBUG if quiet else logging.INFO
                logging.log(log_level, f"Rozpoczynanie aktualizacji wyświetlacza (tryb: {mode}).")
            elif mode == 'partial':
                log_level = logging.DEBUG
                logging.log(log_level, f"Rozpoczynanie aktualizacji wyświetlacza (tryb: {mode}). Obszar: {rect}")
            else:
                raise ValueError(f"Nieznany tryb aktualizacji: {mode}")

            if flip:
                if not _FLIP_LOGGED:
                    logging.info("Obracanie obrazu o 180 stopni.")
                    _FLIP_LOGGED = True
                else:
                    logging.debug("Obracanie obrazu o 180 stopni.")
                img_display = img.rotate(180)
            else:
                img_display = img

            epd = epd7in5_V2.EPD()
            if mode == 'full':
                epd.init()
                if clear_screen:
                    logging.debug("Czyszczenie ekranu przed pełnym odświeżeniem.")
                    epd.Clear()
                epd.display(epd.getbuffer(img_display))
            elif mode == 'partial':
                epd.init_part()
                # display_Partial expects x, y, w, h
                # Transform rect if display is flipped
                if flip:
                    transformed_rect = (
                        EPD_WIDTH - rect[2],
                        EPD_HEIGHT - rect[3],
                        EPD_WIDTH - rect[0],
                        EPD_HEIGHT - rect[1]
                    )
                    logging.debug(f"Oryginalny rect: {rect}, Transformed rect: {transformed_rect}")
                    epd.display_Partial(epd.getbuffer(img_display), transformed_rect[0], transformed_rect[1], transformed_rect[2] - transformed_rect[0], transformed_rect[3] - transformed_rect[1])
                else:
                    epd.display_Partial(epd.getbuffer(img_display), rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])

            epd.sleep()
            logging.debug(f"_execute_display_update: Zakończenie dla trybu: {mode}")
            logging.log(log_level, f"Aktualizacja wyświetlacza (tryb: {mode}) zakończona.")
    except Exception as e:
        logging.error(f"Wystąpił błąd podczas komunikacji z wyświetlaczem: {e}", exc_info=True)

def update_display(layout_config, force_full_refresh=False, draw_borders=False, apply_pixel_shift=False, flip=False, quiet=False):
    """Generuje nowy obraz i wykonuje pełne odświeżenie wyświetlacza."""
    logging.debug("update_display: Rozpoczęcie.")
    try:
        log_level = logging.DEBUG if quiet else logging.INFO
        logging.log(log_level, "Generowanie nowego obrazu do pełnego odświeżenia.")
        img = generate_image(layout_config, draw_borders=draw_borders)
        if apply_pixel_shift:
            max_shift = 2
            dx = random.randint(-max_shift, max_shift)
            dy = random.randint(-max_shift, max_shift)
            logging.info(f"Stosowanie przesunięcia pikseli o ({dx}, {dy}) w celu ochrony ekranu.")
            img = _shift_image(img, dx, dy)
        with FileLock(IMAGE_LOCK_PATH):
            img.save(IMAGE_PATH, "PNG")
        _execute_display_update(img, mode='full', flip=flip, clear_screen=force_full_refresh, quiet=quiet)
    except Exception as e:
        logging.error(f"Wystąpił błąd podczas przygotowywania pełnej aktualizacji: {e}", exc_info=True)
    logging.debug("update_display: Zakończenie.")

def partial_update_time(layout_config, draw_borders=False, flip=False):
    """Wyświetlacz czarno-biały nie wspiera szybkiej aktualizacji. Wykonywane jest pełne odświeżenie."""
    logging.debug("Wyświetlacz nie wspiera częściowej aktualizacji. Wykonywanie pełnego odświeżenia (tryb cichy).")
    update_display(layout_config, force_full_refresh=False, draw_borders=draw_borders, apply_pixel_shift=False, flip=flip, quiet=True)

def clear_display():
    """Inicjalizuje wyświetlacz i czyści jego zawartość."""
    logging.debug("clear_display: Rozpoczęcie.")
    try:
        with EPD_LOCK:
            logging.info("Czyszczenie wyświetlacza e-ink...")
            epd = epd7in5_V2.EPD()
            epd.init()
            epd.Clear()
            epd.sleep()
            logging.info("Wyświetlacz wyczyszczony.")
    except Exception as e:
        logging.error(f"Wystąpił błąd podczas czyszczenia wyświetlacza: {e}", exc_info=True)
    logging.debug("clear_display: Zakończenie.")
