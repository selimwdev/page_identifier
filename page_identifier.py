import os
import json
import sys
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from colorama import Fore, Style, init

init(autoreset=True)

DETECTORS_DIR = "detectors"

# ===============================================
# Disable Selenium / Chrome noise
# ===============================================
def silent_chrome_options():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-software-rasterizer")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return options

# ===============================================
# Load detectors
# ===============================================
def load_detectors():
    detectors = []
    for file in os.listdir(DETECTORS_DIR):
        if file.endswith(".json"):
            with open(os.path.join(DETECTORS_DIR, file), "r", encoding="utf-8") as f:
                detectors.append(json.load(f))
    return detectors

# ===============================================
# HTML scoring
# ===============================================
def check_html_signals(soup, detector):
    html = detector["html"]
    score = 0
    for sel in html["required"]:
        if soup.select(sel):
            score += detector["scoring"]["html_required"]
    for sel in html["optional"]:
        if soup.select(sel):
            score += detector["scoring"]["html_optional"]
    for sel in html["forbidden"]:
        if soup.select(sel):
            score += detector["scoring"]["forbidden_penalty"]
    return score

# ===============================================
# Text scoring
# ===============================================
def check_text_signals(text, detector):
    t = detector["text"]
    score = 0
    for word in t["required"]:
        if word in text:
            score += detector["scoring"]["text_required"]
    for word in t["optional"]:
        if word in text:
            score += detector["scoring"]["text_optional"]
    for word in t["forbidden"]:
        if word in text:
            score += detector["scoring"]["forbidden_penalty"]
    return score

# ===============================================
# Analyze page
# ===============================================
def analyze_page(html, detector):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ").lower()

    score = check_html_signals(soup, detector) + check_text_signals(text, detector)

    if score >= detector["logic"]["min_total_score"]:
        return detector["name"]
    return None

# ===============================================
# Identify single URL
# ===============================================
def identify_page(url):
    options = silent_chrome_options()

    # suppress selenium logs fully
    devnull = open(os.devnull, "w")
    sys.stderr = devnull

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    html = driver.page_source
    driver.quit()

    sys.stderr = sys.__stderr__

    detectors = load_detectors()
    matches = []

    for d in detectors:
        res = analyze_page(html, d)
        if res:
            matches.append(res)

    return matches

# ===============================================
# CLI with file input
# ===============================================
if __name__ == "__main__":
    file_path = input("Enter path to URL file: ").strip()

    if not os.path.isfile(file_path):
        print(Fore.RED + f"[ERROR] File not found: {file_path}")
        exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        urls = [u.strip() for u in f if u.strip()]

    print(Fore.CYAN + "\n==== DoomScope Page Identifier ====\n")

    for url in urls:
        print(Fore.YELLOW + f"[+] Scanning: {url}")

        try:
            results = identify_page(url)

            if results:
                colored = ", ".join([Fore.GREEN + r + Style.RESET_ALL for r in results])
                print(Fore.WHITE + f"    → Detected: {colored}\n")
            else:
                print(Fore.RED + "    → No page type detected\n")

        except Exception as e:
            print(Fore.RED + f"    → Error: {e}\n")
