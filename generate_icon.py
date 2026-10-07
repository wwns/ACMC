from PIL import Image, ImageDraw, ImageFont
w,h = 256,256
img = Image.new('RGBA',(w,h),(0,120,220,255))
d = ImageDraw.Draw(img)
# prosty znak "A"
try:
    f = ImageFont.load_default()
    d.text((w*0.28,h*0.18), 'A', font=f, fill=(255,255,255,255))
except Exception:
    d.rectangle([w*0.2,h*0.2,w*0.8,h*0.8], fill=(255,255,255,255))
img.save('acmc_icon.ico')
print('Wygenerowano acmc_icon.ico')
