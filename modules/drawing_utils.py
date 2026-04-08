import logging
import os
import io
import textwrap
from functools import lru_cache
from PIL import Image, ImageFont

from modules import asset_manager

# Definicje kolorów dla 4-poziomowej skali szarości
WHITE = 255        # Gray1
LIGHT_GRAY = 170   # Gray2
DARK_GRAY = 85     # Gray3
BLACK = 0          # Gray4

# Aliasy dla czytelności
GRAY1 = WHITE
GRAY2 = LIGHT_GRAY
GRAY3 = DARK_GRAY
GRAY4 = BLACK

try:
    from cairosvg import svg2png
    SVG_RENDERER = 'cairosvg'
except ImportError:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
    SVG_RENDERER = 'svglib'
    logging.warning("Biblioteka 'cairosvg' nie jest zainstalowana. Używam wolniejszej biblioteki 'svglib'.")

@lru_cache(maxsize=None)
def load_fonts():
    """
    Wczytuje wszystkie zdefiniowane w konfiguracji czcionki.
    """
    logging.info("Wczytywanie czcionek do pamięci podręcznej...")
    fonts = {}
    try:
        fonts['large'] = ImageFont.truetype(asset_manager.get_path('font_bold'), 117)
        fonts['medium'] = ImageFont.truetype(asset_manager.get_path('font_bold'), 32)
        fonts['small'] = ImageFont.truetype(asset_manager.get_path('font_regular'), 22)
        fonts['small_bold'] = ImageFont.truetype(asset_manager.get_path('font_bold'), 22)
        fonts['small_holiday'] = ImageFont.truetype(asset_manager.get_path('font_regular'), 26)
        fonts['small_bold_holiday'] = ImageFont.truetype(asset_manager.get_path('font_bold'), 26)
        fonts['calendar_header'] = ImageFont.truetype(asset_manager.get_path('font_bold'), 24)
        fonts['calendar_day'] = ImageFont.truetype(asset_manager.get_path('font_regular'), 24)
        fonts['tiny'] = ImageFont.truetype(asset_manager.get_path('font_regular'), 18)
        fonts['tiny_scaled'] = ImageFont.truetype(asset_manager.get_path('font_regular'), 20)
        fonts['ellipsis'] = ImageFont.truetype(asset_manager.get_path('font_regular'), 11)
        fonts['weather_temp'] = ImageFont.truetype(asset_manager.get_path('font_bold'), 79)
        fonts['weather_temp_scaled'] = ImageFont.truetype(asset_manager.get_path('font_bold'), 87)
        fonts['weather_temp_imgw'] = ImageFont.truetype(asset_manager.get_path('font_bold'), 44)
        logging.info("Wszystkie czcionki wczytane pomyślnie.")
    except (IOError, KeyError) as e:
        logging.critical(f"Nie udało się wczytać pliku czcionki: {e}. Sprawdź konfigurację w config.yaml.")
        fonts['large'] = ImageFont.load_default()
        fonts['medium'] = ImageFont.load_default()
        fonts['small'] = ImageFont.load_default()
        fonts['small_bold'] = ImageFont.load_default()
        fonts['weather_temp'] = ImageFont.load_default()
    return fonts

@lru_cache(maxsize=128)
def render_svg_with_cache(svg_path, size):
    """
    Renderuje plik SVG do obiektu obrazu Pillow, z agresywnym cachingiem.
    """
    if not svg_path or not os.path.exists(svg_path):
        logging.error(f"Plik SVG nie istnieje: {svg_path}")
        return None

    logging.debug(f"Renderowanie SVG (cache miss): {svg_path}")

    try:
        if SVG_RENDERER == 'cairosvg':
            png_data = svg2png(url=svg_path, output_width=size, output_height=size)
            return Image.open(io.BytesIO(png_data)).convert("RGBA")
        else:
            drawing = svg2rlg(svg_path)
            in_memory_file = io.BytesIO()
            renderPM.drawToFile(drawing, in_memory_file, fmt="PNG", bg=0xFFFFFF, configPIL={'transparent': 1})
            in_memory_file.seek(0)
            return Image.open(in_memory_file).resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
    except Exception as e:
        logging.error(f"Nie udało się zrenderować SVG '{svg_path}': {e}")
        return None

def draw_error_message(draw_obj, message, fonts, panel_config):
    """Rysuje komunikat o błędzie w zadanym obszarze."""
    rect = panel_config.get('rect', [0, 0, 800, 480])
    x1, y1, x2, y2 = rect
    font = fonts.get('small', ImageFont.load_default())
    char_width_approx = font.getlength('W')
    max_chars = (x2 - x1 - 20) / char_width_approx if char_width_approx > 0 else 30
    wrapped_text = textwrap.fill(message, width=int(max_chars))
    draw_obj.text((x1 + (x2 - x1) / 2, y1 + (y2 - y1) / 2), wrapped_text, font=font, fill=0, anchor="mm", align="center")
