"""
Generuje ikonę dla ACMC - Bramka Modbus LG
Motyw: LG zielony + kwadrat
"""
from PIL import Image, ImageDraw, ImageFont
import os

def make_acmc_icon(path="acmc.ico"):
    sizes = [256, 128, 64, 48, 32, 16]
    frames = []
    
    # Kolory: LG logo zielone + gwiazdy
    lg_green = (0, 180, 0, 255)      # LG zielony
    dark_bg = (20, 30, 50, 255)      # ciemne tło
    silver = (200, 200, 200, 255)    # srebrny (Modbus)
    orange = (255, 140, 0, 255)      # pomarańczowy (aktywność)
    
    for sz in sizes:
        img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        cx, cy = sz // 2, sz // 2
        
        # === TŁO: zaokrąglony kwadrat ciemny ===
        margin = max(1, sz // 16)
        r = sz // 6
        d.rounded_rectangle(
            [margin, margin, sz - margin, sz - margin],
            radius=r, fill=dark_bg
        )
        
        # === KWADRAT: srebrny (Modbus) ===
        quad_m = sz * 0.15
        quad_sz = sz * 0.7
        d.rounded_rectangle(
            [quad_m, quad_m, quad_m + quad_sz, quad_m + quad_sz],
            radius=max(1, sz // 20),
            fill=(50, 60, 80, 255),
            outline=silver,
            width=max(1, sz // 32)
        )
        
        # === LITERY LG - zielone w kwadracie ===
        # Rysujemy stylizowane "LG"
        # L - pionowa i pozioma linia
        l_x = quad_m + quad_sz * 0.15
        l_y_top = quad_m + quad_sz * 0.15
        l_y_bot = quad_m + quad_sz * 0.75
        l_x_bottom = l_x + quad_sz * 0.15
        
        line_width = max(1, sz // 32)
        
        # L - pionowa
        d.rectangle(
            [l_x - line_width//2, l_y_top, l_x + line_width//2, l_y_bot],
            fill=lg_green
        )
        # L - pozioma (dół)
        d.rectangle(
            [l_x, l_y_bot - line_width//2, l_x_bottom + line_width, l_y_bot + line_width//2],
            fill=lg_green
        )
        
        # G - prawy bok (zaokrąglony)
        g_x = cx + quad_sz * 0.1
        g_y_top = quad_m + quad_sz * 0.15
        g_y_bot = quad_m + quad_sz * 0.75
        g_h = (g_y_bot - g_y_top) / 2
        
        # Górna część G
        d.arc(
            [g_x - quad_sz * 0.15, g_y_top, g_x + quad_sz * 0.15, g_y_top + g_h * 2],
            0, 180,
            fill=lg_green,
            width=max(1, sz // 32)
        )
        # Dolna część G
        d.rectangle(
            [g_x, g_y_bot - g_h * 0.5, g_x + quad_sz * 0.1, g_y_bot],
            fill=lg_green
        )
        
        # === KROPKI AKTYWNOŚCI (pomarańczowe) ===
        dot_r = max(1, sz // 24)
        dot_y = quad_m + quad_sz * 0.85
        
        for i in range(3):
            dot_x = quad_m + quad_sz * (0.2 + i * 0.3)
            d.ellipse(
                [dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r],
                fill=orange
            )
        
        frames.append(img)
    
    # Zapisz jako .ico (multi-size)
    frames[0].save(
        path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:]
    )
    print(f"✓ Ikona ACMC zapisana: {path}  ({os.path.getsize(path):,} bytes)")

if __name__ == "__main__":
    make_acmc_icon()
