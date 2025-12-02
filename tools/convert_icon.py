"""Convert logo.png to icon.ico for the executable with proper Windows icon format."""
from pathlib import Path
from PIL import Image

# Load the PNG image
logo_path = Path(__file__).parent / "assets" / "logo.png"
icon_path = Path(__file__).parent / "assets" / "icon.ico"

if not logo_path.exists():
    print(f"Error: {logo_path} not found")
    exit(1)

# Load the image
try:
    img = Image.open(logo_path)
    
    # Keep transparency if available for better quality
    if img.mode in ('RGBA', 'LA', 'P'):
        # For transparent images, preserve alpha channel
        if img.mode == 'P':
            img = img.convert('RGBA')
    else:
        img = img.convert('RGBA')
    
    # Create multiple sizes for Windows icon (256, 128, 64, 48, 32, 16)
    # Windows uses different sizes in different contexts
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    
    # Save as ICO with multiple resolutions for proper Windows display
    img.save(icon_path, format='ICO', sizes=icon_sizes)
    print(f"Successfully created {icon_path} with multiple resolutions")
    print(f"Sizes included: {', '.join(f'{w}x{h}' for w, h in icon_sizes)}")
    
except Exception as e:
    print(f"Error: {e}")
    exit(1)
