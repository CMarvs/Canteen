#!/usr/bin/env python3
"""
Create a default placeholder image for menu items
"""
import os

try:
    from PIL import Image, ImageDraw, ImageFont
    
    # Create a 180x180 image with a light gray background
    img = Image.new('RGB', (180, 180), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    
    # Add a border
    draw.rectangle([0, 0, 179, 179], outline=(200, 200, 200), width=2)
    
    # Try to use a default font, fall back to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
    
    # Draw placeholder text
    text = "🍽️ No Image"
    # Calculate text position (center)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (180 - text_width) // 2
    y = (180 - text_height) // 2
    
    draw.text((x, y), text, fill=(150, 150, 150), font=font)
    
    # Ensure directory exists
    os.makedirs('static/images/menu_items', exist_ok=True)
    
    # Save the image
    img.save('static/images/menu_items/default.jpg', 'JPEG', quality=90)
    print("✅ Default image created: static/images/menu_items/default.jpg")

except ImportError:
    print("⚠️ PIL/Pillow not installed. Creating a basic gray image without text...")
    import struct
    import zlib
    
    # Create a minimal PNG (180x180 gray image) without PIL
    width, height = 180, 180
    
    # PNG file signature
    png_signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk (image header)
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
    ihdr_chunk = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
    
    # IDAT chunk (image data) - just gray pixels
    raw_data = b''
    gray_value = b'\xf0\xf0\xf0'  # Light gray RGB
    for y in range(height):
        raw_data += b'\x00'  # Filter type for each row
        for x in range(width):
            raw_data += gray_value
    
    compressed_data = zlib.compress(raw_data)
    idat_crc = zlib.crc32(b'IDAT' + compressed_data) & 0xffffffff
    idat_chunk = struct.pack('>I', len(compressed_data)) + b'IDAT' + compressed_data + struct.pack('>I', idat_crc)
    
    # IEND chunk (image end)
    iend_crc = zlib.crc32(b'IEND') & 0xffffffff
    iend_chunk = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
    
    # Write PNG file
    os.makedirs('static/images/menu_items', exist_ok=True)
    with open('static/images/menu_items/default.jpg', 'wb') as f:
        f.write(png_signature + ihdr_chunk + idat_chunk + iend_chunk)
    
    print("✅ Default image created (as PNG): static/images/menu_items/default.jpg")

except Exception as e:
    print(f"❌ Error creating default image: {e}")
    print("Please create a 180x180px image manually and save it to: static/images/menu_items/default.jpg")
