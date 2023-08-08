import json
import re
from collections import defaultdict
from pathlib import Path

import pytesseract
from PIL import Image

from common import OCR_RESULTS_FILE, get_screen_text_content


def get_text_from_image(image_path: str | Path) -> str:
    image = Image.open(image_path)

    # Optional: Preprocess the image (e.g., resize, thresholding)
    # image = image.resize((256, 128), Image.BICUBIC)
    image = image.resize((512, 256), Image.BICUBIC)
    # image = image.resize((1024, 512), Image.BICUBIC)

    return pytesseract.image_to_string(image)


def length_penalty(text1: str, text2: str) -> float:
    return 1 - abs(len(text1) - len(text2)) / (len(text1) + len(text2))


def jaccard_similarity(text1: str, text2: str) -> float:
    tokens1 = set(text1.lower().split())
    tokens2 = set(text2.lower().split())
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    if union == 0:
        return 0
    similarity = intersection / union
    penalty = length_penalty(text1, text2)
    return similarity * penalty


def generate_report() -> None:
    res: dict[str, dict[str, int]] = defaultdict(dict)

    screens_content = get_screen_text_content()
    for flow_name, flow_data in screens_content.items():
        for index, screen_info in enumerate(flow_data, start=1):
            description = screen_info["description"]
            img_name = f"{flow_name}{index}"
            img_src = Path(f"static/{flow_name}/{img_name}.png")
            if not img_src.exists():
                continue
            extracted_text = get_text_from_image(img_src)

            # remove all the content of {xxx} and [xxx] from description
            description = re.sub(r"\{.*?\}", "", description)
            description = re.sub(r"\[.*?\]", "", description)

            try:
                main_text = description.split("||")[-2].strip()
            except IndexError:
                main_text = description

            potential_title = description.split("||")[0].strip()
            has_title = potential_title and potential_title.upper() == potential_title
            has_buttons = "<" in description and ">" in description

            split = extracted_text.split("\n")
            if split[-1] == "\x0c":
                split = split[:-1]
            if has_title:
                split = split[1:]
            if has_buttons:
                split = split[:-1]

            extracted_text = " ".join(split)

            similarity = jaccard_similarity(extracted_text, main_text)
            res[flow_name][img_name] = int(similarity * 100)

    with open(OCR_RESULTS_FILE, "w") as f:
        json.dump(res, f, indent=4)


if __name__ == "__main__":
    # image_path = "static/Tutorial/Tutorial1.png"
    # extracted_text = get_text_from_image(image_path)
    # print(extracted_text)

    generate_report()
