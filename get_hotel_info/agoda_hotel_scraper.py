import time
import os
import requests
import gspread
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from google.oauth2.service_account import Credentials
import schedule

# Load configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.txt")
GOOGLE_AUTH = os.path.join(BASE_DIR, "google_credentials.json")

def load_api_keys():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        keys = {}
        for line in f:
            key, value = line.strip().split("=", 1)  # '=' 이후 값을 읽도록 수정
            keys[key] = value.strip().replace('r"', '').replace('"', '')  # 불필요한 문자 제거
    return keys 

keys = load_api_keys()
CREDENTIALS_JSON = os.path.abspath(keys["CREDENTIALS_JSON"])  # 절대 경로 변환
SPREADSHEET_ID = keys["SPREADSHEET_ID"]  # Google Sheets ID 추가
TAB_NAME = keys["TAB_NAME"]

def should_execute(idx):
    """
    Google Sheets에서 A열이 존재하고 F열이 비어있는 경우에만 실행 여부를 확인합니다.
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_file(CREDENTIALS_JSON, scopes=scopes)
    client = gspread.authorize(credentials)
    worksheet = client.open_by_key(SPREADSHEET_ID).worksheet(TAB_NAME)
    
    a_column_values = worksheet.col_values(1)  # A열 데이터
    f_column_values = worksheet.col_values(6)  # F열 데이터
    
    if idx <= len(a_column_values) and (idx > len(f_column_values) or f_column_values[idx-1] == ""):
        return True
    return False

    
def get_next_available_row():
    """
    Google Sheets에서 A열과 E열이 존재하고 F열이 비어있는 첫 번째 행 번호와 URL을 반환합니다.
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_file(CREDENTIALS_JSON, scopes=scopes)
    client = gspread.authorize(credentials)
    worksheet = client.open_by_key(SPREADSHEET_ID).worksheet(TAB_NAME)
    
    a_column_values = worksheet.col_values(1)  # A열 데이터
    e_column_values = worksheet.col_values(5)  # E열 데이터 (호텔 URL)
    f_column_values = worksheet.col_values(6)  # F열 데이터
    
    for idx in range(1, len(a_column_values) + 1):
        if (idx <= len(e_column_values) and e_column_values[idx - 1] != "") and \
           (idx > len(f_column_values) or f_column_values[idx - 1] == ""):
            return idx, e_column_values[idx - 1]  # idx와 URL 반환
    return None, None  # 저장할 행이 없음


def scrape_agoda_hotel_info(url):
    """
    Selenium을 사용하여 Agoda 호텔 페이지에서 호텔명, 가격, 위치, 별점, 주요특징, 이용후기 요약을 크롤링합니다.
    """
    options = Options()
    options.add_argument("--headless")  # GUI 없이 실행
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())  # ChromeDriver 자동 다운로드 및 경로 설정
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    
    wait = WebDriverWait(driver, 15)
    time.sleep(5)  # 추가 로딩 대기
    
    # 페이지 스크롤 다운 (일부 정보가 로딩되지 않을 경우 대비)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)
    
    # 호텔명 추출
    try:
        hotel_name_tag = wait.until(EC.presence_of_element_located((By.XPATH, "//h1[@data-selenium='hotel-header-name']")))
        hotel_name = hotel_name_tag.text.strip()
    except:
        hotel_name = "N/A"
    
    # 가격 추출
    try:
        price_tag = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'Price')]//span[contains(text(), '₩')]")))
        price = price_tag.text.strip()
    except:
        price = "N/A"
    
    # 위치 추출
    try:
        location_tag = wait.until(EC.presence_of_element_located((By.XPATH, "//span[@data-selenium='hotel-address-map']")))
        location = location_tag.text.strip()
    except:
        location = "N/A"
    
    # 별점 추출 (별 개수)
    try:
        rating_tag = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-selenium='mosaic-hotel-rating']")))
        stars = len(rating_tag.find_elements(By.TAG_NAME, "svg"))
    except:
        stars = "N/A"
    
    # 주요 특징 추출
    try:
        features_tags = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[@data-element-name='property-top-feature']//p")))
        features = ", ".join([tag.text.strip() for tag in features_tags[:5]])
    except:
        features = "N/A"
    
    # 이용 후기 요약 추출
    try:
        reviews_tags = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[@data-element-name='atf-review-snippet-sidebar']//span")))
        reviews_summary = ", ".join([tag.text.strip() for tag in reviews_tags[:4]])
    except:
        reviews_summary = "N/A"
    
    driver.quit()
    
    return {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "Hotel Name": hotel_name,
        "Price": price,
        "Location": location,
        "Review Score": f"{stars}성급",
        "Features": features,
        "Reviews Summary": reviews_summary
    }

def save_to_google_sheets(hotel_data, idx):
    """
    Google Sheets에 크롤링한 호텔 정보를 저장하되, F열(idx 번째 행)에 저장합니다.
    """
    print("[LOG] 수집된 데이터:", hotel_data)
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_file(CREDENTIALS_JSON, scopes=scopes)
    client = gspread.authorize(credentials)
    
    worksheet = client.open_by_key(SPREADSHEET_ID).worksheet(TAB_NAME)
    
    col = 6  # F열 (1-based index)
    row = idx  # 지정된 행 위치
    
    for i, value in enumerate(hotel_data.values(), start=0):
        worksheet.update_cell(row, col + i, value)

def job():
    idx, hotel_url = get_next_available_row()
    if idx and hotel_url:
        hotel_info = scrape_agoda_hotel_info(hotel_url)
        save_to_google_sheets(hotel_info, idx)


#한 시간마다 실행하도록 설정
schedule.every(1).hours.do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
