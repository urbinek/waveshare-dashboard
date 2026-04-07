import logging
import datetime
from dateutil import parser
import textwrap
from PIL import Image # Add Image import

from modules.config_loader import config
from modules import drawing_utils

def draw_panel(image, draw, calendar_data, fonts, box_info):
    """Rysuje listę nadchodzących wydarzeń w zdefiniowanym obszarze (box)."""
    logging.debug(f"Rysowanie panelu wydarzeń w obszarze: {box_info['rect']}")
    rect = box_info['rect']
    adjustments = box_info.get('positional_adjustments', {})
    x_offset = adjustments.get('x', 0)
    y_offset = adjustments.get('y', 0)

    line_height = 30
    time_width = 70
    left_padding = 5
    top_padding = 10

    font_event = fonts.get('small')
    font_date = fonts.get('small_bold', font_event)

    max_events = config['google_calendar']['max_upcoming_events']
    events = calendar_data.get('upcoming_events', [])[:max_events]

    y_start_block = rect[1] + top_padding + y_offset
    x_start = rect[0] + left_padding + x_offset # Use x_offset

    title_text = "Nadchodzące:"
    draw.text((x_start, y_start_block), title_text, font=fonts['small_bold'], fill=drawing_utils.BLACK)
    title_bbox = draw.textbbox((x_start, y_start_block), title_text, font=fonts['small_bold'])
    line_y = title_bbox[3] + 2
    draw.line([(title_bbox[0], line_y), (title_bbox[2], line_y)], fill=drawing_utils.BLACK, width=1)

    if not events:
        draw.text((x_start, y_start_block + line_height), "- Brak wydarzeń -", font=font_event, fill=drawing_utils.BLACK)
        return

    today = datetime.date.today()
    holiday_dates_set = {datetime.date.fromisoformat(d) for d in calendar_data.get('holiday_dates', [])}

    for i, event in enumerate(events):
        y_slot_top = y_start_block + ((i + 1) * line_height)
        y_centered = y_slot_top + (line_height // 2)

        start_str = event.get('start')
        if not start_str:
            continue

        try:
            event_dt_obj = parser.isoparse(start_str)
            summary = event.get('summary', 'Brak tytułu')

            # Use black text on white background for all events
            text_color = drawing_utils.BLACK

            # Format date as DD.MM
            time_formatted = event_dt_obj.strftime('%d.%m')

            # Draw date (bold)
            draw.text((x_start, y_centered), time_formatted, font=font_date, fill=text_color, anchor="lm")

            # Truncate and draw summary
            max_len = 30
            display_summary = textwrap.shorten(summary, width=max_len, placeholder="")
            draw.text((x_start + time_width, y_centered), display_summary, font=font_event, fill=text_color, anchor="lm")

            if len(summary) > max_len:
                text_width = draw.textlength(display_summary, font=font_event)
                ellipsis_x = x_start + time_width + text_width
                font_ellipsis = fonts.get('ellipsis')
                draw.text((ellipsis_x, y_centered), "...", font=font_ellipsis, fill=text_color, anchor="lm")

        except (ValueError, TypeError) as e:
            logging.warning(f"Nie udało się przetworzyć daty wydarzenia '{start_str}': {e}")