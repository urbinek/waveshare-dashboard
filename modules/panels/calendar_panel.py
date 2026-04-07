import logging
import textwrap
import datetime
from modules import drawing_utils

def draw_panel(draw, calendar_data, fonts, box_info):
    """Rysuje siatkę kalendarza."""
    logging.debug(f"Rysowanie panelu kalendarza w obszarze: {box_info['rect']}")
    rect = box_info['rect']
    adjustments = box_info.get('positional_adjustments', {})
    x_offset = adjustments.get('x', 0)
    y_offset = adjustments.get('y', 0)

    # --- Stałe i Ustawienia Layoutu ---
    cell_width = 53
    cell_height = 44
    grid_width = 7 * cell_width
    font_cal_header = fonts.get('calendar_header')
    font_cal_day = fonts.get('calendar_day')

    # --- Przygotowanie siatki kalendarza ---
    month_grid = calendar_data.get('month_calendar', [])
    grid_height = (len(month_grid) + 1) * cell_height if month_grid else 0

    # --- Wyśrodkowanie pionowe siatki ---
    box_width = rect[2] - rect[0]
    box_height = rect[3] - rect[1]

    grid_x_start = rect[0] + (box_width - grid_width) // 2 + x_offset
    grid_y_start = rect[1] + (box_height - grid_height) // 2 + y_offset

    # --- Rysowanie Nagłówków Dni Tygodnia ---
    days_of_week = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]
    if month_grid:
        header_center_y = grid_y_start + cell_height // 2
        for i, day_name in enumerate(days_of_week):
            x = grid_x_start + (i * cell_width) + (cell_width // 2)
            draw.text((x, header_center_y), day_name, font=font_cal_header, fill=drawing_utils.BLACK, anchor="mm")

        # Draw underline for header
        line_y = grid_y_start + cell_height
        draw.line([(grid_x_start, line_y), (grid_x_start + grid_width, line_y)], fill=drawing_utils.BLACK, width=1)

    # --- Rysowanie Siatki Kalendarza ---
    if month_grid:
        grid_body_y_start = grid_y_start + cell_height
        for week_idx, week in enumerate(month_grid):
            for day_idx, day_info in enumerate(week):
                day_str = str(day_info.get('day', ''))
                cell_x = grid_x_start + (day_idx * cell_width)
                cell_y = grid_body_y_start + (week_idx * cell_height)

                is_today = day_info.get('is_today', False)
                is_holiday = day_info.get('is_holiday', False)
                has_event = day_info.get('has_event', False)
                day_date_str = day_info.get('date')
                day_date = None
                if day_date_str:
                    day_date = datetime.date.fromisoformat(day_date_str)

                text_x = cell_x + cell_width // 2
                text_y = cell_y + cell_height // 2
                current_font = fonts['calendar_header'] if is_today else font_cal_day
                
                is_upcoming_holiday = is_holiday and day_date and day_date >= datetime.date.today()

                if day_info.get('is_current_month'):
                    if is_holiday:
                        if is_upcoming_holiday:
                            # Upcoming holiday: black square, white text
                            draw.rectangle((cell_x, cell_y, cell_x + cell_width, cell_y + cell_height), fill=drawing_utils.BLACK)
                            draw.text((text_x, text_y), day_str, font=current_font, fill=drawing_utils.WHITE, anchor="mm")
                        else:
                            # Past holiday: dark gray text
                            draw.text((text_x, text_y), day_str, font=current_font, fill=drawing_utils.DARK_GRAY, anchor="mm")
                    elif has_event:
                        # Event (not a holiday): black square, white text
                        draw.rectangle((cell_x, cell_y, cell_x + cell_width, cell_y + cell_height), fill=drawing_utils.BLACK)
                        draw.text((text_x, text_y), day_str, font=current_font, fill=drawing_utils.WHITE, anchor="mm")
                    else:
                        # Normal day
                        text_color = drawing_utils.BLACK
                        if day_date and day_date < datetime.date.today():
                            text_color = drawing_utils.LIGHT_GRAY
                        draw.text((text_x, text_y), day_str, font=current_font, fill=text_color, anchor="mm")

                if is_today:
                    text_bbox = draw.textbbox((text_x, text_y), day_str, font=current_font, anchor="mm")
                    underline_y = text_bbox[3] + 2
                    underline_color = drawing_utils.WHITE if has_event or is_upcoming_holiday else drawing_utils.BLACK
                    draw.line([(text_bbox[0], underline_y), (text_bbox[2], underline_y)], fill=underline_color, width=2)
