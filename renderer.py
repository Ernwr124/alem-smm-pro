import textwrap
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps

def get_fonts():
    try:
        f_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 75)
        f_regular = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except:
        f_bold = ImageFont.load_default()
        f_regular = ImageFont.load_default()
    return f_bold, f_regular

def create_dynamic_clone(images, title, subtitle, layout_data=None):
    """Сборка клона на основе данных от Vision AI"""
    if not layout_data: layout_data = {"image_count": 4, "text_position": "bottom", "text_align": "left"}
    
    w, h = 1080, 1350 
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    ic = layout_data.get("image_count", 4)

    # 1. ДИНАМИЧЕСКАЯ СЕТКА ИЗОБРАЖЕНИЙ
    if ic == 1:
        img = ImageOps.fit(images[0], (w, h), Image.Resampling.LANCZOS).convert("RGBA")
        canvas.paste(img, (0, 0))
    elif ic == 2:
        img1 = ImageOps.fit(images[0], (w, h//2), Image.Resampling.LANCZOS).convert("RGBA")
        img2 = ImageOps.fit(images[1] if len(images)>1 else images[0], (w, h//2), Image.Resampling.LANCZOS).convert("RGBA")
        canvas.paste(img1, (0, 0))
        canvas.paste(img2, (0, h//2))
    else:
        gw, gh = w // 2, h // 2
        positions = [(0, 0), (gw, 0), (0, gh), (gw, gh)]
        for i in range(4):
            img = ImageOps.fit(images[i] if i < len(images) else images[-1], (gw, gh), Image.Resampling.LANCZOS).convert("RGBA")
            canvas.paste(img, positions[i])

    # 2. ДИНАМИЧЕСКИЙ ГРАДИЕНТ
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    o_draw = ImageDraw.Draw(overlay)
    t_pos = layout_data.get("text_position", "bottom")
    
    if t_pos == "bottom":
        for y in range(h // 2, h):
            alpha = int(245 * ((y - h // 2) / (h // 2)))
            o_draw.line([(0, y), (w, y)], fill=(15, 15, 20, alpha))
    elif t_pos == "top":
        for y in range(0, h // 2):
            alpha = int(245 * (1 - (y / (h // 2))))
            o_draw.line([(0, y), (w, y)], fill=(15, 15, 20, alpha))
    else: # center
        for y in range(h // 3, 2 * (h // 3)):
            o_draw.line([(0, y), (w, y)], fill=(15, 15, 20, 200))
    
    canvas.alpha_composite(overlay)

    # 3. ДИНАМИЧЕСКИЙ ТЕКСТ (ЗАЩИТА ОТ ОБРЕЗАНИЯ)
    draw = ImageDraw.Draw(canvas)
    f_bold, f_regular = get_fonts()
    align = layout_data.get("text_align", "left")
    
    # Умный перенос: чем длиннее слово, тем уже ширина блока
    wrap_width = 16 if align == "left" else 22
    wrapped_title = textwrap.fill(title.upper(), width=wrap_width)
    wrapped_sub = textwrap.fill(subtitle, width=wrap_width * 2)

    # Высчитываем размеры текстового блока
    t_bbox = draw.multiline_textbbox((0, 0), wrapped_title, font=f_bold)
    s_bbox = draw.multiline_textbbox((0, 0), wrapped_sub, font=f_regular)
    text_h = (t_bbox[3] - t_bbox[1]) + (s_bbox[3] - s_bbox[1]) + 40

    # Координаты по Y
    if t_pos == "bottom": start_y = h - text_h - 150
    elif t_pos == "top": start_y = 150
    else: start_y = (h - text_h) // 2

    # Координаты по X (Выравнивание)
    if align == "center":
        draw.multiline_text((w//2, start_y), wrapped_title, font=f_bold, fill="white", align="center", anchor="ma", spacing=15)
        draw.multiline_text((w//2, start_y + (t_bbox[3] - t_bbox[1]) + 40), wrapped_sub, font=f_regular, fill="#D0D0D0", align="center", anchor="ma", spacing=10)
    elif align == "right":
        draw.multiline_text((w-60, start_y), wrapped_title, font=f_bold, fill="white", align="right", anchor="ra", spacing=15)
        draw.multiline_text((w-60, start_y + (t_bbox[3] - t_bbox[1]) + 40), wrapped_sub, font=f_regular, fill="#D0D0D0", align="right", anchor="ra", spacing=10)
    else:
        draw.multiline_text((60, start_y), wrapped_title, font=f_bold, fill="white", align="left", spacing=15)
        draw.multiline_text((60, start_y + (t_bbox[3] - t_bbox[1]) + 40), wrapped_sub, font=f_regular, fill="#D0D0D0", align="left", spacing=10)

    out = "dynamic_post.png"
    canvas.convert("RGB").save(out, "PNG")
    return out

# Старые функции оставляем для сторис и каруселей
def create_elite_collage(images, title, subtitle): return create_dynamic_clone(images, title, subtitle)
def create_carousel_pages(images, slides_data, main_title, main_subtitle):
    paths = []
    w, h = 1080, 1350
    f_bold, f_regular = get_fonts()
    for i, img in enumerate(images):
        canvas = ImageOps.fit(img, (w, h), Image.Resampling.LANCZOS).convert("RGBA")
        overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        o_draw = ImageDraw.Draw(overlay)
        for y in range(h // 2 - 100, h):
            alpha = int(245 * ((y - (h // 2 - 100)) / (h - (h // 2 - 100))))
            o_draw.line([(0, y), (w, y)], fill=(10, 10, 15, alpha))
        canvas.alpha_composite(overlay)
        draw = ImageDraw.Draw(canvas)
        if i == 0:
            wrapped = textwrap.fill(main_title.upper(), width=16)
            draw.multiline_text((60, h - 350), wrapped, font=f_bold, fill="white", spacing=15)
        else:
            wrapped = textwrap.fill(slides_data[i].get("text", ""), width=35)
            draw.multiline_text((60, h - 300), wrapped, font=f_regular, fill="white", spacing=15)
        out = f"carousel_slide_{i}.png"
        canvas.convert("RGB").save(out, "PNG")
        paths.append(out)
    return paths

def create_story(image, text):
    w, h = 1080, 1920
    canvas = ImageOps.fit(image, (w, h), Image.Resampling.LANCZOS).convert("RGBA")
    out = "story_post.png"
    canvas.convert("RGB").save(out, "PNG")
    return out
