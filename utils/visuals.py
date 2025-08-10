from PIL import Image, ImageDraw, ImageFont

def draw_root_cause_diagram(df):
    """
    Creates a simple root cause diagram from events in a DataFrame.
    Always returns a PIL image so Streamlit st.image() won't break.
    """
    # Create blank image
    img_width, img_height = 900, 600
    img = Image.new("RGB", (img_width, img_height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()

    # If no data, show "No events"
    if df.empty:
        draw.text((20, 20), "No events found for this file.", fill="black", font=font)
        return img

    # Extract unique events
    events = df["Alarm Name"].unique().tolist() if "Alarm Name" in df.columns else []
    if not events:
        draw.text((20, 20), "No Alarm Name data found.", fill="black", font=font)
        return img

    # Draw header
    draw.text((20, 20), "Root Cause Diagram", fill="black", font=font)

    # Draw boxes for each event
    box_width, box_height = 250, 40
    x_start, y_start = 50, 80
    y_gap = 70

    for i, event in enumerate(events):
        top_left = (x_start, y_start + i * y_gap)
        bottom_right = (x_start + box_width, y_start + box_height + i * y_gap)
        draw.rectangle([top_left, bottom_right], outline="black", width=2)
        draw.text((top_left[0] + 5, top_left[1] + 10), str(event), fill="black", font=font)

        # Draw arrow to next event
        if i < len(events) - 1:
            arrow_start = (x_start + box_width, y_start + box_height // 2 + i * y_gap)
            arrow_end = (x_start + box_width + 50, y_start + box_height // 2 + i * y_gap)
            draw.line([arrow_start, arrow_end], fill="black", width=2)
            # Arrow head
            draw.polygon([
                (arrow_end[0], arrow_end[1]),
                (arrow_end[0] - 10, arrow_end[1] - 5),
                (arrow_end[0] - 10, arrow_end[1] + 5)
            ], fill="black")

    return img





