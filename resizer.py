from PIL import Image

image_path = "/home/jmusil/Downloads/Firmware(6)/Tutorial 08.png"
img = Image.open(image_path)

# Use the NEAREST algorithm to keep the pixelated style
original_size = (128, 64)
img_resized = img.resize(original_size, Image.NEAREST)

img_resized.save("path_to_save_resized_image.png")
