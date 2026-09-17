import random
import string
import subprocess
import time
import threading
import pytesseract
from pytesseract import image_to_string
from PIL import Image, ImageEnhance, ImageOps
import mss
from screeninfo import get_monitors
import numpy as np
import cv2
from fuzzywuzzy import fuzz
import sys
import json
import requests
import os
import time


STATE_FILE = "gold_state.json"

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def print_monitor_info():
    monitors = get_monitors()
    for monitor in monitors:
        print(f"Monitor: {monitor.name}, Width: {monitor.width}, Height: {monitor.height}, Left: {monitor.x}, Top: {monitor.y}")

# Print the monitor information to find the coordinates
print_monitor_info()

def get_enemies_remaining():
    with mss.mss() as sct:
        monitor = sct.monitors[2]  # Adjust index to your monitor
        bbox = {
            "left": monitor["left"] + 1475,
            "top": monitor["top"] + 770,
            "width": 1583 - 1475,
            "height": 782 - 770,
                }
        screenshot = sct.grab(bbox)
        image = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)

        # Save the unedited original image for debugging
        image.save("debug_original.png")

        # Convert the image to a numpy array
        image_array = np.array(image)

        # Define the turquoise color range
        lower_turquoise = np.array([0, 130, 120])  # Lower bound for turquoise
        upper_turquoise = np.array([60, 255, 255])  # Upper bound for turquoise

        # Apply color mask to isolate turquoise text
        mask = cv2.inRange(image_array, lower_turquoise, upper_turquoise)

        # Check if the mask has any non-zero pixels
        if cv2.countNonZero(mask) == 0:
            print("No turquoise pixels detected.")
            return None

        # Apply the mask to the image to retain only turquoise text
        filtered_image = cv2.bitwise_and(image_array, image_array, mask=mask)

        # Convert the result back to a PIL Image
        image_filtered = Image.fromarray(filtered_image)

        # Convert to grayscale to enhance contrast (after isolating turquoise)
        image_filtered = image_filtered.convert("L")

        # Enhance contrast to make the text more distinct
        image_filtered = ImageEnhance.Contrast(image_filtered).enhance(1.5)

        # Apply a threshold to binarize the image
        image_filtered = image_filtered.point(lambda p: p > 170 and 255)  # Adjust threshold value

        # Resize the image to improve OCR accuracy
        image_filtered = image_filtered.resize(
            (image_filtered.width * 2, image_filtered.height * 2), Image.LANCZOS
        )

        # Save the debug preprocessed image
        image_filtered.save("debug_preprocessed.png")

        # Perform OCR
        extracted_text = pytesseract.image_to_string(image_filtered, config='--psm 6 --oem 3')
        print(f"Extracted text: {extracted_text}")

        # Check if any text is detected
        if extracted_text.strip():  # Strip removes any leading/trailing whitespace
            return True
        else:
            return None




# List of BlueStacks instances (IPs, ports, and corresponding window names)
instances = [
    {"ip": "127.0.0.1:5585", "window_title": "BlueStacks App Player 3"},
    {"ip": "127.0.0.1:5556", "window_title": "BlueStacks App Player 1"},
    {"ip": "127.0.0.1:5575", "window_title": "BlueStacks App Player 2"},
    {"ip": "127.0.0.1:5595", "window_title": "BlueStacks App Player 4"},
    {"ip": "127.0.0.1:5605", "window_title": "BlueStacks App Player 5"}
]

def connect_bluestacks_devices():
    """Automatically connect all BlueStacks instances to ADB."""
    print("Connecting BlueStacks devices...")
    for instance in instances:
        ip = instance["ip"]
        try:
            # Connect the ADB device
            subprocess.run(f"adb connect {ip}", shell=True, check=True)
            print(f"Connected to {ip}")
        except subprocess.CalledProcessError:
            print(f"Failed to connect to {ip}")
    print("Finished connecting devices.\n")

def check_adb_devices():
    """List all connected ADB devices."""
    print("Checking connected ADB devices...\n")
    subprocess.run("adb devices", shell=True)

def wait_for_user_confirmation():
    """Pause execution until the user presses Enter."""
    input("Press Enter to start the script after verifying connections...")

def tap_on_instance(instance, x, y):
    subprocess.run(f"adb -s {instance} shell input tap {x} {y}", shell=True)

def send_text(instance, text):
    subprocess.run(f"adb -s {instance} shell input text {text}", shell=True)

def send_keystroke(instance, key_code):
    subprocess.run(f"adb -s {instance} shell input keyevent {key_code}", shell=True)

def mouse_button_down(instance, x, y):
    subprocess.run(f"adb -s {instance} shell input swipe {x} {y} {x} {y} 100", shell=True)

def mouse_button_up(instance, x, y):
    subprocess.run(f"adb -s {instance} shell input swipe {x} {y} {x} {y} 0", shell=True)

def hold_left_click(instance, x, y, duration=3):
    # Simulate holding the left mouse button down
    mouse_button_down(instance, x, y)
    time.sleep(duration)
    # Simulate releasing the left mouse button
    mouse_button_up(instance, x, y)

def host_game():
    # Example: Tap on coordinates (600, 25) for instance 1 (127.0.0.1:5555)
    tap_on_instance(instances[0]["ip"], 580, 45)

    # Wait for 3 seconds before the next tap
    time.sleep(2)

    tap_on_instance(instances[0]["ip"], 243, 497)
    time.sleep(1)
    tap_on_instance(instances[0]["ip"], 333, 110)
    tap_on_instance(instances[0]["ip"], 830, 310)
    tap_on_instance(instances[0]["ip"], 108, 484)
    send_text(instances[0]["ip"], "".join(random.choices(string.ascii_lowercase, k=3)))
    send_keystroke(instances[0]["ip"], 66)
    time.sleep(1)
    tap_on_instance(instances[0]["ip"], 448, 487)

# Refactored join_game function to use multithreading
def join_game():
    def tap_and_send(instance, x1, y1, x2, y2, key_code):
        tap_on_instance(instance["ip"], x1, y1)
        time.sleep(0.5)
        tap_on_instance(instance["ip"], x2, y2)
        time.sleep(0.5)
        send_keystroke(instance["ip"], key_code)

    # Create threads for instances 2, 3, 4, and 5 (indices 1, 2, 3, 4)
    threads = []
    for instance in instances[1:]:  # This will include instances 2, 3, 4, and 5
        t = threading.Thread(target=tap_and_send, args=(instance, 476, 41, 652, 211, 66,))
        threads.append(t)
        t.start()

    # Wait for all threads to finish
    for t in threads:
        t.join()

def invite():
    tap_on_instance(instances[0]["ip"], 27, 28)
    time.sleep(0.5)
    tap_on_instance(instances[0]["ip"], 637, 36)
    time.sleep(0.2)
    tap_on_instance(instances[0]["ip"], 305, 206)
    tap_on_instance(instances[0]["ip"], 305, 297)
    tap_on_instance(instances[0]["ip"], 305, 387)
    tap_on_instance(instances[0]["ip"], 305, 454)
    tap_on_instance(instances[0]["ip"], 35, 33)
    return

def hold_left_click(instance, x, y, duration=3000):
    """
    Simulates holding a left click for a specific duration at the given coordinates.

    Parameters:
        instance (str): IP of the ADB instance.
        x (int): X coordinate.
        y (int): Y coordinate.
        duration (int): Duration to hold in milliseconds (default: 3000ms).
    """
    # Send a swipe command with the hold duration
    subprocess.run(f"adb -s {instance} shell input swipe {x} {y} {x} {y} {duration}", shell=True)

def hold_click_all_instances(instances, x, y, duration=3000):
    """
    Simulates holding a left click on all instances concurrently.

    Parameters:
        instances (list): List of instance IPs.
        x (int): X coordinate.
        y (int): Y coordinate.
        duration (int): Duration to hold in milliseconds.
    """
    threads = []

    # Create a thread for each instance
    for instance in instances:
        thread = threading.Thread(target=hold_left_click, args=(instance["ip"], x, y, duration))
        threads.append(thread)

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

def tap_all_instances(instances, x, y):
    """
    Simulates a tap on all instances concurrently using ADB.

    Parameters:
        instances (list): List of instance IPs or ports.
        x (int): X coordinate.
        y (int): Y coordinate.
    """
    def tap(instance_ip, x, y):
        """
        Sends an ADB tap command to a single instance.

        Parameters:
            instance_ip (str): IP or port of the instance.
            x (int): X coordinate.
            y (int): Y coordinate.
        """
        try:
            command = f"adb -s {instance_ip} shell input tap {x} {y}"
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error tapping on instance {instance_ip}: {e}")

    threads = []

    # Create a thread for each instance
    for instance in instances:
        thread = threading.Thread(target=tap, args=(instance["ip"], x, y))
        threads.append(thread)

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

def use_buffs():
    tap_all_instances(instances, 773, 140)
    time.sleep(0.2)
    tap_all_instances(instances, 773, 220)
    time.sleep(0.2)
    tap_all_instances(instances, 773, 290)

def use_skills():
    potspam(1)
    time.sleep(0.2)
    tap_all_instances(instances, 925, 140)
    potspam(1)
    time.sleep(0.2)
    tap_all_instances(instances, 925, 220)
    potspam(1)
    time.sleep(0.2)
    tap_all_instances(instances, 925, 295)
    time.sleep(0.2)
    potspam(1)
    time.sleep(0.2)
    tap_all_instances(instances, 925, 370)
    potspam(1)
    time.sleep(0.2)
    tap_all_instances(instances, 847, 373)
    time.sleep(0.2)
    tap_all_instances(instances, 847, 295)
    time.sleep(0.2)
    tap_all_instances(instances, 680, 493)
    time.sleep(0.2)
    potspam(1)
    time.sleep(0.2)

def respawn():
    tap_all_instances(instances, 390, 415)

def potspam(reps):
    for i in range(reps):
        tap_all_instances(instances, 680, 493)
        tap_all_instances(instances, 680, 493)

def battle(repetitions):
    for i in range(repetitions):
        use_buffs()
        use_skills()


# Preprocessing function for red background and white text
def preprocess_image_for_red_text(image):
    # Convert to RGB
    image = image.convert("RGB")
    # Define the target red color range
    red_rgb = (231, 19, 19)
    # Convert to numpy array
    image_array = np.array(image)

    # Create a mask for red pixels (you can adjust the range if needed)
    red_pixels = np.all(image_array[:, :, :3] == red_rgb, axis=-1)

    # Make the red pixels black (if any)
    image_array[red_pixels] = [0, 0, 0]  # Set red pixels to black

    # Convert the image back to PIL format
    processed_image = Image.fromarray(image_array)

    return processed_image

def preprocess_image_for_black_text_on_yellow(image):
    """
    Preprocesses the image to improve OCR for black text on yellow background.
    Converts to grayscale, enhances contrast, and applies thresholding.
    """
    grayscale = image.convert("L")  # Convert to grayscale
    enhanced = ImageOps.autocontrast(grayscale)  # Enhance contrast
    binary = enhanced.point(lambda x: 0 if x < 128 else 255)  # Binarize
    return binary

def extract_text(top_left_x, top_left_y, bottom_right_x, bottom_right_y):
    """
    Extracts text from a defined screen region using OCR.

    Args:
        top_left_x (int): X-coordinate of the top-left corner of the box.
        top_left_y (int): Y-coordinate of the top-left corner of the box.
        bottom_right_x (int): X-coordinate of the bottom-right corner of the box.
        bottom_right_y (int): Y-coordinate of the bottom-right corner of the box.

    Returns:
        str: Extracted text from the region.
    """
    with mss.mss() as sct:
        # Access monitor 2
        monitor = sct.monitors[2]  # Adjust if needed

        bbox = {
            "left": monitor["left"] + top_left_x,
            "top": monitor["top"] + top_left_y,
            "width": bottom_right_x - top_left_x,
            "height": bottom_right_y - top_left_y
        }

        # Capture screenshot of defined area
        screenshot = sct.grab(bbox)
        image = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)

        # Save debug image
        image.save("debug_original_ocr.png")
        print("Saved debug_original_ocr.png")

        # OCR
        extracted_text = pytesseract.image_to_string(
            image,
            config="--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789"
        ).strip()

        print(f"Extracted text: {extracted_text}")

        return extracted_text

def search_words(word_list, top_left_x, top_left_y, bottom_right_x, bottom_right_y, threshold=50):
    """
    Searches for specified words within a defined screen region using OCR and fuzzy matching.
    
    Args:
        word_list (list): A list of target words to search for.
        top_left_x (int): X-coordinate of the top-left corner of the search box.
        top_left_y (int): Y-coordinate of the top-left corner of the search box.
        bottom_right_x (int): X-coordinate of the bottom-right corner of the search box.
        bottom_right_y (int): Y-coordinate of the bottom-right corner of the search box.
        threshold (int): Fuzzy matching threshold (default is 50).

    Returns:
        bool: True if a match is found, False otherwise.
    """
    with mss.mss() as sct:
        # Access monitor 2
        monitor = sct.monitors[2]  # Adjust monitor index as per your setup
        bbox = {
            "left": monitor["left"] + top_left_x,
            "top": monitor["top"] + top_left_y,
            "width": bottom_right_x - top_left_x,
            "height": bottom_right_y - top_left_y
        }

        # Capture the screenshot of the defined area
        screenshot = sct.grab(bbox)
        image = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)

        # Save the original screenshot for debugging
        image.save("debug_original_search.png")
        print("Saved debug_original_search.png")

        # Perform OCR on the image
        extracted_text = pytesseract.image_to_string(image, config="--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)
        print(f"Extracted text: {extracted_text}")

        # Use fuzzy matching to check if any target word matches
        matched_text = fuzzy_match_strict(extracted_text, word_list, threshold)
        if matched_text:
            print(f"Found '{matched_text}'. Exiting the loop.")
            return True  # Exit the loop if a match is found
        else:
            print(f"None of the words {word_list} found. Continuing...")
            return False  # Continue if no match is found

def search_words_stacked(target_texts, top_left_x, top_left_y, bottom_right_x, bottom_right_y, threshold=80, psm=6):
    """
    Searches for all target texts stacked one above the other within a specified region of the screen.
    """
    with mss.mss() as sct:
        monitor = sct.monitors[2]  # Use monitor 2
        bbox = {
            "left": monitor["left"] + top_left_x,
            "top": monitor["top"] + top_left_y,
            "width": bottom_right_x - top_left_x,
            "height": bottom_right_y - top_left_y
        }

        # Capture the screenshot of the defined area
        screenshot = sct.grab(bbox)
        image = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)

        # Preprocess the image (optional, for better OCR accuracy)
        processed_image = preprocess_image_for_black_text_on_yellow(image)
        processed_image.save("debug_stacked_image.png")  # Save for debugging

        # Perform OCR with specified PSM
        extracted_text = pytesseract.image_to_string(processed_image, config="--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
        print(f"Extracted text:\n{extracted_text}")

        # Check if all target texts are present
        for target in target_texts:
            if not fuzzy_match_strict(extracted_text, [target], threshold):
                print(f"'{target}' not found. Continuing search...")
                return False  # If any target is missing, return False

        print("All target texts found!")
        return True  # If all targets are found, return True

# Fuzzy match function
def fuzzy_match(extracted_text, target_texts, threshold=70):
    # Clean the extracted text by stripping whitespace and converting to uppercase
    cleaned_text = extracted_text.strip().upper()

    # Perform fuzzy matching to allow for slight variations
    for target in target_texts:
        cleaned_target = target.strip().upper()
        if fuzz.partial_ratio(cleaned_text, cleaned_target) >= threshold: #used to be partial_ratio
            return target  # Return the matched string if it passes the threshold
    return None  # Return None if no match is found

def fuzzy_match_strict(extracted_text, target_texts, threshold=85):
    # Clean the extracted text by stripping whitespace and converting to uppercase
    cleaned_text = extracted_text.strip().upper()

    if len(cleaned_text) < 4:
        return None


    # Perform fuzzy matching to allow for slight variations
    for target in target_texts:
        cleaned_target = target.strip().upper()
        if fuzz.partial_ratio(cleaned_text, cleaned_target) >= threshold:
            return target  # Return the matched string if it passes the threshold
    return None  # Return None if no match is found

# Your search function with preprocessing and fuzzy matching
def search_zori_kurn(top_left_x, top_left_y, bottom_right_x, bottom_right_y):
    with mss.mss() as sct:
        monitor = sct.monitors[2]  # Correctly referencing monitor index 2
        bbox = {
            "left": monitor["left"] + top_left_x,
            "top": monitor["top"] + top_left_y,
            "width": bottom_right_x - top_left_x,
            "height": bottom_right_y - top_left_y
        }

        # Capture the screenshot of the defined area
        screenshot = sct.grab(bbox)
        image = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)

        # Save the unedited original screenshot for debugging
        image.save("debug_original_zori.png")
        print("Saved debug_original_zori.png")

        # Perform OCR on the image
        extracted_text = pytesseract.image_to_string(image, config="--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)
        print(f"Extracted text: {extracted_text}")

        # Fuzzy match the extracted text against the target "ZORI"
        target_texts = ["ZoriKurn"]
        matched_text = fuzzy_match(extracted_text, target_texts)

        if matched_text:
            print(f"Found '{matched_text}'. Exiting the loop.")
            return True  # Exit the loop
        else:
            print("'ZORI' not found. Continuing...")
            return False  # Continue the loop

def search_auros_kurn(top_left_x, top_left_y, bottom_right_x, bottom_right_y):
    with mss.mss() as sct:
        monitor = sct.monitors[2]  # Correctly referencing monitor index 2
        bbox = {
            "left": monitor["left"] + top_left_x,
            "top": monitor["top"] + top_left_y,
            "width": bottom_right_x - top_left_x,
            "height": bottom_right_y - top_left_y
        }

        # Capture the screenshot of the defined area
        screenshot = sct.grab(bbox)
        image = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)

        # Save the unedited original screenshot for debugging
        image.save("debug_original_auros.png")
        print("Saved debug_original_auros.png")

        # Perform OCR on the image
        extracted_text = pytesseract.image_to_string(image, config="--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)
        print(f"Extracted text: {extracted_text}")

        # Fuzzy match the extracted text against the target "AUROS"
        target_texts = ["AurosKurn"]
        matched_text = fuzzy_match(extracted_text, target_texts)

        if matched_text:
            print(f"Found '{matched_text}'. Exiting the loop.")
            return True  # Exit the loop
        else:
            print("'AUROS' not found. Continuing...")
            return False  # Continue the loop

def search_return_to_towne(top_left_x, top_left_y, bottom_right_x, bottom_right_y):
    with mss.mss() as sct:
        monitor = sct.monitors[2]  # Adjust for your monitor configuration
        bbox = {
            "left": monitor["left"] + top_left_x,
            "top": monitor["top"] + top_left_y,
            "width": bottom_right_x - top_left_x,
            "height": bottom_right_y - top_left_y
        }

        # Capture the screenshot of the defined area
        screenshot = sct.grab(bbox)
        image = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)

        # Save the original screenshot for debugging
        image.save("debug_original_towne.png")
        print("Saved debug_original_towne.png")

        # Preprocess the image for OCR (if needed for better results)
        processed_image = preprocess_image_for_black_text_on_yellow(image)
        processed_image.save("debug_processed_towne.png")  # Save preprocessed image for debugging
        print("Saved debug_processed_towne.png")

        # Perform OCR on the preprocessed image
        extracted_text = pytesseract.image_to_string(processed_image, config="--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)
        print(f"Extracted text: {extracted_text}")

        # Fuzzy match the extracted text against the target "RETURN" and "TOWNE"
        target_texts = ["RETURNTOTOWNE"]
        matched_text = fuzzy_match_strict(extracted_text, target_texts)

        if matched_text:
            print(f"Found '{matched_text}'. Exiting the loop.")
            return True  # Exit the loop
        else:
            print("'TOWNE' not found. Continuing...")
            return False  # Continue the loop


def mob_clear():
    print("Starting mob clearing...")

    total_fail_count = 0

    while True:

        if search_words(["platonius"], 351, 463, 793, 485, 80) or search_words(["AurosKurn"], 351, 463, 793, 485, 80):
            print("Zori dead")
            break

        if search_return_to_towne(410, 823, 758, 866):
            break

        # Bottom left
        hold_click_all_instances(instances, 17, 446, 1000)
        battle(2)
        respawn()

        if search_zori_kurn(351, 463, 793, 485):
            print("Found 'Zori Kurn'. Stopping mob clearing.")
            break
        else:
            print("'Zori Kurn' NOT found. Moving on to the next area.")

        # Top left
        if search_words(["platonius"], 351, 463, 793, 485, 80) or search_words(["AurosKurn"], 351, 463, 793, 485, 80):
            print("Zori dead")
            break

        if search_return_to_towne(409, 823, 725, 866):
            break

        respawn()
        hold_click_all_instances(instances, 114, 415, 2250)
        battle(2)
        respawn()

        if search_zori_kurn(351, 463, 793, 485):
            print("Found 'Zori Kurn'. Stopping mob clearing.")
            break
        else:
            print("'Zori Kurn' NOT found. Moving on to the next area.")

        # Top right
        if search_words(["platonius"], 351, 463, 793, 485, 80) or search_words(["AurosKurn"], 351, 463, 793, 485, 80):
            print("Zori dead")
            break

        if search_return_to_towne(409, 823, 725, 866):
            break

        respawn()
        hold_click_all_instances(instances, 140, 485, 3000)
        battle(2)
        respawn()

        if search_zori_kurn(351, 463, 793, 485):
            print("Found 'Zori Kurn'. Stopping mob clearing.")
            break
        else:
            print("'Zori Kurn' NOT found. Moving on to the next area.")

        # Bottom right
        if search_words(["platonius"], 351, 463, 793, 485, 80) or search_words(["AurosKurn"], 351, 463, 793, 485, 80):
            print("Zori dead")
            break

        if search_return_to_towne(409, 823, 725, 866):
            break

        respawn()
        hold_click_all_instances(instances, 26, 440, 2000)
        battle(2)
        respawn()

        if search_zori_kurn(351, 463, 793, 485):
            print("Found 'Zori Kurn'. Stopping mob clearing.")
            break
        else:
            print("'Zori Kurn' NOT found. Restarting loop.")

        total_fail_count += 1
        if total_fail_count >= 30:
            break

        



def first_boss_battle():
    print("Fighting First Boss")

    fail_count = 0  # To track consecutive failures to find "Zori Kurn"
    
    while True:
        # Perform the battle
        battle(1)
        respawn()
        tap_all_instances(instances, 522, 65)

        # Check for "Zori Kurn" after each battle
        if not search_zori_kurn(351, 463, 793, 485):
            fail_count += 1
            print(f"'Zori Kurn' NOT found. Failure count: {fail_count}")

        # End the battle if "Zori Kurn" is NOT found after three consecutive checks
        if fail_count >= 2:
            print("Failed to detect 'Zori Kurn' three times in a row. Ending battle.")
            break
        if search_words(["platonius"], 351, 463, 793, 485, 80):
            print("platonius spawned, moving on")
            break
        if search_return_to_towne(409, 823, 725, 866):  # Fixed function name
            break  # Break the loop once "Return to Towne" is found

def second_boss_battle():
    print("Fighting Second Boss")

    fail_count = 0  # Tracks consecutive failures
    tapped_once = False  # Tracks if tap_all_instances has already been executed

    while True:
        # Perform the battle
        tap_all_instances(instances, 480, 310)
        hold_click_all_instances(instances, 80, 506, 1000)
        battle(1)
        respawn()

        # Check for "Auros Kurn" after each battle
        if not search_auros_kurn(351, 463, 793, 485):
            fail_count += 1
            print(f"'Auros Kurn' NOT found. Failure count: {fail_count}")
        else:
            fail_count = 0  # Reset the failure count if "Auros Kurn" is found
            print("'Auros Kurn' found. Continuing the battle.")

        if search_words(["platonius"], 351, 463, 793, 485, 80):
            print("platonius spawned, moving on")
            break
        if search_return_to_towne(409, 823, 725, 866):  # Fixed function name
            break  # Break the loop once "Return to Towne" is found

        # If "Auros Kurn" is NOT found after three consecutive checks
        if fail_count >= 2:
            if not tapped_once:
                # Perform tap actions only once
                print("Performing reset actions...")
                use_buffs()
                hold_click_all_instances(instances, 84, 392, 3000)
                battle(1)
                hold_click_all_instances(instances, 84, 493, 3000)
                tapped_once = True  # Mark that reset actions were performed
                fail_count = 0  # Reset the failure counter to continue
            else:
                # Exit the loop if this is the second occurrence of three failures
                print("Exiting loop after second set of three failures.")
                break

            
    

def final_boss_battle():
    print("Fighting Final Boss")
    fail_count = 0
    while True:  # Keep looping until we find "Return to Towne"
        # Call the function to search for the "Return to Towne" text
        if search_return_to_towne(409, 823, 725, 866) or fail_count == 20:  # Fixed function name
            break  # Break the loop once "Return to Towne" is found
        fail_count = fail_count + 1
        battle(1)  # Engage in the battle
        respawn()  # Respawn

def log_out():
    tap_all_instances(instances, 28, 27)
    time.sleep(0.4)
    tap_all_instances(instances, 828, 501)
    time.sleep(0.4)

def loot():
    hold_click_all_instances(instances, 39, 411, 1000)
    hold_click_all_instances(instances, 140, 450, 800)
    hold_click_all_instances(instances, 39, 487, 800)
    hold_click_all_instances(instances, 140, 450, 800)

def go_to_inv():
    tap_all_instances(instances, 480, 44)
    time.sleep(0.5)
    tap_all_instances(instances, 276, 33)

def sell_all():
    tap_all_instances(instances, 778, 503)
    time.sleep(0.1)
    tap_all_instances(instances, 830, 185)
    time.sleep(0.1)
    tap_all_instances(instances, 472, 368)
    time.sleep(0.1)
    tap_all_instances(instances, 830, 250)
    time.sleep(0.1)
    tap_all_instances(instances, 472, 368)
    time.sleep(0.1)
    tap_all_instances(instances, 830, 315)
    time.sleep(0.1)
    tap_all_instances(instances, 472, 368)
    time.sleep(0.1)
    tap_all_instances(instances, 830, 380)
    time.sleep(0.1)
    tap_all_instances(instances, 472, 368)
    time.sleep(0.1)
    tap_all_instances(instances, 830, 445)
    time.sleep(0.1)
    tap_all_instances(instances, 472, 368)
    time.sleep(0.1)
    tap_all_instances(instances, 925, 31)

def clear_inv():
    go_to_inv()
    time.sleep(0.3)
    clean_rare_loot()
    time.sleep(0.1)
    tap_all_instances(instances, 603, 101)
    clean_rare_loot()
    tap_all_instances(instances, 650, 101)
    clean_rare_loot()
    time.sleep(0.1)
    tap_all_instances(instances, 693, 101)
    clean_rare_loot()
    time.sleep(0.1)
    tap_all_instances(instances, 740, 101)
    clean_rare_loot()
    time.sleep(0.1)
    tap_all_instances(instances, 782, 101)
    clean_rare_loot()
    time.sleep(0.1)
    

def navigate_to_top():
    for i in range(2):
        hold_click_all_instances(instances, 50, 410, 1500)
        hold_click_all_instances(instances, 120, 410, 1500)

def clean_rare_loot():
    for i in range(8):
        tap_all_instances(instances, 700, 242)
        time.sleep(0.1)
        tap_all_instances(instances, 693, 505)
        time.sleep(0.1)
        tap_all_instances(instances, 484, 411)


def exit_program():
    print("Retry limit reached. Exiting program.")
    log_out()
    exit()  # This stops the entire program.

def clean_number(text):
    text = text.strip()
    return int(text) if text.isdigit() else 0


def send_gold_update(webhook_url):

    boxes = [
        (108, 350, 193, 373),
        (748, 350, 850, 372),
        (1380, 350, 1470, 375),
        (1381, 728, 1470, 745),
        (210, 988, 355, 1020)
    ]

    # ---- Read current values ----
    current = []
    for box in boxes:
        text = extract_text(*box).strip()
        value = int(text) if text else 0
        current.append(value)

    now = time.time()

    # ---- First run → set baseline ----
    if not os.path.exists(STATE_FILE):
        state = {
            "previous": current,
            "lifetime_total": 0,
            "last_time": now
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        return

    # ---- Load previous ----
    with open(STATE_FILE, "r") as f:
        state = json.load(f)

    previous = state["previous"]
    last_time = state.get("last_time", now)

    # ---- Calculate per-bot gains ----
    deltas = []
    cycle_total = 0

    for i in range(5):
        earned = max(0, current[i] - previous[i])
        deltas.append(earned)
        cycle_total += earned

    # ---- Calculate average runtime ----
    elapsed = now - last_time
    avg_runtime = elapsed / 5

    # ---- Update lifetime totals ----
    state["lifetime_total"] += cycle_total
    state["previous"] = current
    state["last_time"] = now

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    # ---- Format time nicely ----
    mins = int(avg_runtime // 60)
    secs = int(avg_runtime % 60)

    if mins > 0:
        avg_string = f"{mins}m {secs}s"
    else:
        avg_string = f"{secs}s"

    # ---- Send to Discord ----
    message = (
        "💰 **Gold Earnings (Last 5 runs)**\n\n"
        f"1: +{deltas[0]}\n"
        f"2: +{deltas[1]}\n"
        f"3: +{deltas[2]}\n"
        f"4: +{deltas[3]}\n"
        f"5: +{deltas[4]}\n\n"
        #f"Cycle total: +{cycle_total}\n"
        #f"Lifetime total: {state['lifetime_total']}\n\n"
        f"⏱ Avg run time: {avg_string}"
    )

    requests.post(webhook_url, json={"content": message})


def main():
    # Main script
    connect_bluestacks_devices()
    check_adb_devices()
    wait_for_user_confirmation()


    retry_limit = 20  # Set retry limit
    inv_counter = 0  # Initialize inventory counter

    while True:  # This outer loop will make the entire process repeat
        # Initialize retry counters for each check
        enemy_retry_count = 0
        search_retry_count = 0
        stacked_retry_count = 0
        
        # Step 1: Wait for "World Map" to appear
        while search_retry_count < retry_limit:
            if search_words(["World", "Map"], 1573, 421, 1637, 438, 60):  # Check if "World Map" is found
                print("World Map found. Proceeding to host game.")
                break  # Break out of the loop if the word is found
            search_retry_count += 1  # Increment the retry counter
            time.sleep(3)  # Wait before retrying
        
        # If retry limit is reached without finding "World Map", exit the program
        if search_retry_count >= retry_limit:
            print("World Map not found within retry limit. Exiting program.")
            log_out()
            sys.exit()  # Graceful exit

        # Proceed to host the game if "World Map" is found
        host_game()  # Host the game
        # Step 2: Wait for enemies to reach 30
        while enemy_retry_count < retry_limit:
            if get_enemies_remaining():  # Check if the game is loaded
                print("Enemies remaining: 30. Proceeding.")
                break  # Exit this inner loop once the condition is met
            enemy_retry_count += 1  # Increment the retry counter
            time.sleep(0.5)  # Add a slight delay to avoid overwhelming checks

        invite()  # Send invites
        time.sleep(0.3)
        join_game()  # Join the game
        time.sleep(1)

        # If retry limit is reached without reaching 30 enemies, exit the program
        if enemy_retry_count >= retry_limit:
            print("Enemies not found within retry limit. Exiting program.")
            log_out()
            sys.exit()  # Graceful exit
        
        # Step 3: Wait for all players to be connected
        while stacked_retry_count < retry_limit:
            if search_words_stacked(["Minaamage", "Religeous", "Rafakillo", "Ragequiit"], 0, 467, 144, 629, 80):
                print("Everyone connected, starting run...")
                break  # Break out of the loop if all players are found
            stacked_retry_count += 1  # Increment the retry counter
            time.sleep(0.5)  # Wait before retrying
        
        # If retry limit is reached without all players connected, exit the program
        if stacked_retry_count >= retry_limit:
            print("Not all players connected within retry limit. Exiting program.")
            log_out()
            sys.exit()  # Graceful exit
        
        # If all tasks are done, proceed with the game logic
        hold_click_all_instances(instances, 85, 490, 4000)
        hold_click_all_instances(instances, 70, 389, 4000)
        battle(1)
        mob_clear()
        navigate_to_top()
        first_boss_battle()
        loot()
        hold_click_all_instances(instances, 81, 493, 6000)
        potspam(2)
        hold_click_all_instances(instances, 81, 493, 4000)
        time.sleep(4)
        second_boss_battle()
        potspam(2)
        hold_click_all_instances(instances, 81, 493, 3000)
        tap_all_instances(instances, 480, 300)
        final_boss_battle()
        loot()
        hold_click_all_instances(instances, 81, 493, 7000)
        loot()
        tap_all_instances(instances, 480, 300)
        tap_all_instances(instances, 480, 300)
        hold_click_all_instances(instances, 60, 398, 4500)
        potspam(3)
        hold_click_all_instances(instances, 60, 398, 4500)
        use_skills()
        hold_click_all_instances(instances, 60, 398, 1000)
        tap_all_instances(instances, 767, 350)
        time.sleep(0.5)
        loot()
        hold_click_all_instances(instances, 133, 446, 2000)
        tap_all_instances(instances, 925, 140)
        tap_all_instances(instances, 877, 482)
        time.sleep(0.5)
        tap_all_instances(instances, 160, 375)
        time.sleep(0.5)
        loot()
        hold_click_all_instances(instances, 140, 450, 800)
        loot()
        time.sleep(2)
        log_out()
        time.sleep(4)
        inv_counter += 1
        if inv_counter >= 5:
            clear_inv()
            tap_all_instances(instances, 215, 100)
            time.sleep(0.1)
            tap_all_instances(instances, 717, 211)
            time.sleep(0.1)
            tap_all_instances(instances, 930, 78)
            time.sleep(0.1)
            #send_gold_update(webhook_url)
            tap_all_instances(instances, 215, 100)
            time.sleep(0.1)
            tap_all_instances(instances, 725, 118)
            time.sleep(0.1)
            tap_all_instances(instances, 930, 78)
            time.sleep(0.1)
            tap_all_instances(instances, 31, 34)
            inv_counter = 0

search_words("aa", 503, 1000, 706, 1022, 60)




