import re
import time
import pytesseract
from PIL import Image, ImageEnhance, ImageOps
import mss
import numpy as np
import cv2
from fuzzywuzzy import fuzz

import config  # ensures tesseract_cmd is set on import


def preprocess_image_for_red_text(image):
    image = image.convert("RGB")
    image_array = np.array(image)
    red_pixels = np.all(image_array[:, :, :3] == (231, 19, 19), axis=-1)
    image_array[red_pixels] = [0, 0, 0]
    return Image.fromarray(image_array)


def preprocess_image_for_white_text_on_red(image):
    arr = np.array(image.convert("RGB"))
    # White pixels: R,G,B all high. Red bg: R high, G+B low.
    # Min of G and B channels isolates white (high) from red (near zero).
    gb_min = np.minimum(arr[:, :, 1], arr[:, :, 2])
    # Invert: white text → black (0), red bg → white (255)
    binary = np.where(gb_min > 80, 0, 255).astype(np.uint8)
    result = Image.fromarray(binary, mode="L")
    return result.resize((result.width * 2, result.height * 2), Image.LANCZOS)


def preprocess_image_for_black_text_on_yellow(image):
    grayscale = image.convert("L")
    enhanced = ImageOps.autocontrast(grayscale)
    return enhanced.point(lambda x: 0 if x < 128 else 255)


def fuzzy_match(extracted_text, target_texts, threshold=70):
    cleaned = extracted_text.strip().upper()
    for target in target_texts:
        if fuzz.partial_ratio(cleaned, target.strip().upper()) >= threshold:
            return target
    return None


def fuzzy_match_strict(extracted_text, target_texts, threshold=85):
    cleaned = extracted_text.strip().upper()
    if len(cleaned) < 4:
        return None
    for target in target_texts:
        if fuzz.partial_ratio(cleaned, target.strip().upper()) >= threshold:
            return target
    return None


def _safe_save(image, filename):
    """Best-effort debug screenshot dump. Never let a disk hiccup kill the bot."""
    try:
        image.save(filename)
    except OSError as e:
        print(f"Could not save debug image '{filename}': {e}")


def _grab_region(top_left_x, top_left_y, bottom_right_x, bottom_right_y):
    with mss.mss() as sct:
        monitor = sct.monitors[config.MONITOR_INDEX]
        bbox = {
            "left": monitor["left"] + top_left_x,
            "top": monitor["top"] + top_left_y,
            "width": bottom_right_x - top_left_x,
            "height": bottom_right_y - top_left_y,
        }
        screenshot = sct.grab(bbox)
        return Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)


def get_enemies_remaining():
    with mss.mss() as sct:
        monitor = sct.monitors[config.MONITOR_INDEX]
        bbox = {
            "left": monitor["left"] + 1490,
            "top": monitor["top"] + 748,
            "width": 116,
            "height": 13,
        }
        screenshot = sct.grab(bbox)
        image = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)
        _safe_save(image, "debug_original.png")

        image_array = np.array(image)
        mask = cv2.inRange(
            image_array,
            np.array([0, 130, 120]),
            np.array([60, 255, 255]),
        )

        if cv2.countNonZero(mask) == 0:
            print("No turquoise pixels detected.")
            return None

        filtered = cv2.bitwise_and(image_array, image_array, mask=mask)
        img = Image.fromarray(filtered).convert("L")
        img = ImageEnhance.Contrast(img).enhance(1.5)
        img = img.point(lambda p: p > 170 and 255)
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        _safe_save(img, "debug_preprocessed.png")

        text = pytesseract.image_to_string(img, config="--psm 6 --oem 3")
        print(f"Extracted text: {text}")
        return True if text.strip() else None


def get_enemies_remaining_count(top_left_x=503, top_left_y=1000, bottom_right_x=706, bottom_right_y=1022):
    """Read the 'Enemies Remaining: N' label and return N as an int, or None if unreadable."""
    image = _grab_region(top_left_x, top_left_y, bottom_right_x, bottom_right_y)
    _safe_save(image, "debug_enemies_remaining.png")

    grayscale = image.convert("L")
    enhanced = ImageOps.autocontrast(grayscale)
    upscaled = enhanced.resize((enhanced.width * 2, enhanced.height * 2), Image.LANCZOS)
    _safe_save(upscaled, "debug_enemies_remaining_processed.png")

    text = pytesseract.image_to_string(upscaled, config="--oem 3 --psm 7")
    print(f"Extracted text: {text}")

    matches = re.findall(r"\d+", text)
    if matches:
        count = int(matches[-1])
        print(f"Enemies remaining: {count}")
        return count
    print("Could not parse enemies remaining count.")
    return None


def extract_text(top_left_x, top_left_y, bottom_right_x, bottom_right_y):
    image = _grab_region(top_left_x, top_left_y, bottom_right_x, bottom_right_y)
    _safe_save(image, "debug_original_ocr.png")
    text = pytesseract.image_to_string(
        image,
        config="--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789",
    ).strip()
    print(f"Extracted text: {text}")
    return text


def search_words(word_list, top_left_x, top_left_y, bottom_right_x, bottom_right_y, threshold=50, red_bg=False):
    image = _grab_region(top_left_x, top_left_y, bottom_right_x, bottom_right_y)
    _safe_save(image, "debug_original_search.png")
    if red_bg:
        image = preprocess_image_for_white_text_on_red(image)
    text = pytesseract.image_to_string(
        image,
        config="--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    )
    print(f"Extracted text: {text}")
    matched = fuzzy_match_strict(text, word_list, threshold)
    if matched:
        print(f"Found '{matched}'. Exiting the loop.")
        return True
    print(f"None of the words {word_list} found. Continuing...")
    return False


def search_words_stacked(target_texts, top_left_x, top_left_y, bottom_right_x, bottom_right_y, threshold=70, psm=6):
    offsets = [(0, 0), (-2, 0), (2, 0), (0, -2), (0, 2)]  # slight shifts per attempt
    for dx, dy in offsets:
        image = _grab_region(top_left_x + dx, top_left_y + dy, bottom_right_x + dx, bottom_right_y + dy)
        processed = preprocess_image_for_black_text_on_yellow(image)
        _safe_save(processed, "debug_stacked_image.png")
        text = pytesseract.image_to_string(
            processed,
            config="--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        )
        print(f"Extracted text (offset {dx},{dy}):\n{text}")
        if all(fuzzy_match_strict(text, [t], threshold) for t in target_texts):
            print("All target texts found!")
            return True
    print(f"Not all targets found after {len(offsets)} attempts.")
    return False


def search_boss_name(top_left_x, top_left_y, bottom_right_x, bottom_right_y):
    """Return 'zori', 'auros', 'platonius', or None. One screenshot per attempt, all three checked."""
    for attempt in range(5):
        if attempt > 0:
            time.sleep(0.05)
        image = _grab_region(top_left_x, top_left_y, bottom_right_x, bottom_right_y)
        upscaled = image.resize((image.width * 2, image.height * 2), Image.LANCZOS)
        _safe_save(upscaled, "debug_boss_name.png")
        text = pytesseract.image_to_string(
            upscaled,
            config="--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        )
        text = text.strip()
        print(f"Boss name read (attempt {attempt+1}): {text}")
        if len(text) < 5:
            continue
        if fuzzy_match(text, ["Platonius"], threshold=70):
            print("Found Platonius.")
            return "platonius"
        if fuzzy_match(text, ["Zori Kurn", "ZoriKurn"], threshold=70):
            print("Found Zori Kurn.")
            return "zori"
        if fuzzy_match(text, ["Auros Kurn", "AurosKurn", "Avros Kurn", "AvrosKurn"], threshold=70):
            print("Found Auros Kurn.")
            return "auros"
    print("No boss name detected.")
    return None


def search_zori_kurn(top_left_x, top_left_y, bottom_right_x, bottom_right_y):
    return search_boss_name(top_left_x, top_left_y, bottom_right_x, bottom_right_y) == "zori"


def search_auros_kurn(top_left_x, top_left_y, bottom_right_x, bottom_right_y):
    return search_boss_name(top_left_x, top_left_y, bottom_right_x, bottom_right_y) == "auros"


def search_return_to_towne(top_left_x, top_left_y, bottom_right_x, bottom_right_y):
    image = _grab_region(top_left_x, top_left_y, bottom_right_x, bottom_right_y)
    _safe_save(image, "debug_original_towne.png")
    processed = preprocess_image_for_black_text_on_yellow(image)
    _safe_save(processed, "debug_processed_towne.png")
    text = pytesseract.image_to_string(
        processed,
        config="--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    )
    print(f"Extracted text: {text}")
    if fuzzy_match_strict(text, ["RETURNTOTOWNE"]):
        print("Found 'RETURNTOTOWNE'. Exiting the loop.")
        return True
    print("'TOWNE' not found. Continuing...")
    return False
