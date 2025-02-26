#!/usr/bin/env python3
"""
Script to download multiple detailed images from a specific Naver image search result,
with enhanced stability and dynamic search query input from a Google Spreadsheet.

Requirements:
    - BeautifulSoup4
    - requests
    - selenium
    - fake_useragent
    - pillow  (for image integrity validation)
    - gspread
    - google-auth

Usage:
    python download_naver_image.py

Process:
    1. Prompt user for Google Sheets integration info.
    2. Read the index (cell A1) and query string (cell A2) from the sheet named '베트남호텔'.
    3. Build the search URL using the query string (e.g., "나트랑 버고호텔" => "&query=나트랑+버고호텔").
    4. Download a specified number of images (default 4) by randomly selecting containers.
       The images are saved in a folder named with the index (e.g., "../../Dropbox/down/1").
    5. Log all steps, errors, and downloaded file paths.
"""

import os
import time
import logging
import random
import requests
from datetime import datetime
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from PIL import Image
from requests.exceptions import ConnectionError as ReqConnectionError

# For Google Sheets integration
import gspread
from google.oauth2.service_account import Credentials

# Configure logging to file
logging.basicConfig(
    filename='./download.log',
    encoding='utf-8',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# 기본 네이버 이미지 검색 URL (QUERY 파라미터 제외)
BASE_SEARCH_URL = "https://search.naver.com/search.naver?ssc=tab.image.all&where=image&sm=tab_jum"

def get_gsheet_config():
    """
    Prompts the user for Google Sheets integration information.
    
    Returns:
        tuple: (credentials_json, spreadsheet_id)
    """
    print("구글 스프레드시트 연동정보가 포함되어있습니다. 별도의 파일로 분리요망:")
    credentials_json = r"C:\Users\skfka\OneDrive\문서\GitHub\scraping\get_hotel_image\secret\intense-reason-451806-j0-5160a24584f2.json"
    # 백슬래시 문제 방지를 위해 raw string 또는 이스케이프 문자를 사용하세요.
    spreadsheet_id = r"1gQ3Ac1_2sUd4EiTRwi_VCLyxNeBbsf-_z47k4JONPmc"
    return credentials_json, spreadsheet_id


def get_query_from_gsheet(credentials_json, spreadsheet_id):
    """
    Reads the title (A열) from the Google Spreadsheet.
    Finds the first row in sheet '베트남호텔' where:
        - Column A has data
        - Column C is empty

    Returns:
        tuple: (title, index_value, worksheet) if a valid row is found;
               otherwise (None, None, worksheet).

    Explanation:
        - title: A열의 문자열 (예: "나트랑 레스참호텔")
        - index_value: 해당 행 번호 (int). 예: 2 -> 스프레드시트의 2행
        - worksheet: gspread Worksheet 객체
    """
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_file(credentials_json, scopes=scopes)
    client = gspread.authorize(credentials)
    worksheet = client.open_by_key(spreadsheet_id).worksheet('베트남호텔')

    all_values = worksheet.get_all_values()  # 전체 데이터를 2차원 리스트로 가져옴

    # enumerate(all_values, start=2)는 실제 시트에서 2번째 행부터 데이터라고 가정 (1행은 헤더 등)
    for r_idx, row in enumerate(all_values, start=2):
        for c_idx, val in enumerate(row):
        # A열: row[0], C열: row[2] 
            query = row[0].strip() if row[0] else ""
            col_c = row[2].strip() if row[2] else ""
            if len(row) >= 3:
                # A열(query)에 값이 있고, C열(col_c)이 비어있는 경우
                if query and not col_c:
                    index_value = r_idx-1  # i는 스프레드시트에서의 실제 행 번호
                    logging.info(f"구글 스프레드시트 {index_value}행 발견: TITLE={query}")
                    return query, index_value, worksheet

    logging.info("A열에 데이터가 있고 C열이 비어있는 행을 찾지 못함.")
    return None, None, worksheet



def build_search_url(query):
    """
    Builds the complete search URL by appending the query parameter.
    
    Args:
        query (str): The query string (e.g., "나트랑 버고호텔").
        
    Returns:
        str: Complete search URL.
    """
    formatted_query = query.replace(" ", "+")
    return f"{BASE_SEARCH_URL}&query={formatted_query}"

def safe_driver_get(driver, url, retries=3, delay=60):
    """
    Attempts to load the URL with Selenium driver.
    On failure (e.g. network issues), waits for 'delay' seconds and retries up to 'retries' times.
    
    Args:
        driver (webdriver.Chrome): Selenium WebDriver instance.
        url (str): URL to load.
        retries (int): Maximum retry attempts.
        delay (int): Delay in seconds between attempts.
        
    Returns:
        bool: True if URL loaded successfully, False otherwise.
    """
    attempts = 0
    while attempts < retries:
        try:
            driver.get(url)
            logging.info(f"URL 로드 성공: {url}")
            return True
        except Exception as e:
            attempts += 1
            logging.error(f"네트워크 연결 실패, {delay}초 대기 후 재시도 ({attempts}/{retries}): {str(e)}")
            time.sleep(delay)
    return False

def setup_driver():
    """
    Sets up a headless ChromeDriver with a randomized User-Agent.
    
    Returns:
        webdriver.Chrome: Configured Selenium WebDriver.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    ua = UserAgent()
    user_agent = ua.random
    chrome_options.add_argument(f'user-agent={user_agent}')
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except WebDriverException as e:
        logging.error(f"ChromeDriver 초기화 에러: {str(e)}")
        raise
    return driver

def get_actual_image_url(driver, search_url, image_index=2):
    if not safe_driver_get(driver, search_url):
        logging.error("검색 페이지 로드 실패")
        return None

    # 동적 컨텐츠 로드를 위해 대기
    time.sleep(5)
    
    # 초기 페이지 스크린샷 저장
    try:
        driver.save_screenshot("debug_page.png")
        logging.info("초기 페이지 스크린샷(debug_page.png) 저장됨.")
    except Exception as e:
        logging.error(f"초기 페이지 스크린샷 저장 실패: {str(e)}")

    # 클릭할 이미지 컨테이너 로드 대기 및 검색
    try:
        logging.info("search section 1")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class*="mod_image_tile"] img'))
        )
        logging.info("이미지 컨테이너 요소 로드됨.")
    except TimeoutException:
        logging.error("이미지 컨테이너 요소 로드 대기 시간 초과")
        return None

    try:
        logging.info("search section 2")
        div_elements = driver.find_elements(By.CSS_SELECTOR, 'div[class*="mod_image_tile"] img')
        logging.info(f"페이지에서 {len(div_elements)}개의 이미지 컨테이너 발견됨.")
        if len(div_elements) <= image_index:
            logging.error(f"요청한 인덱스({image_index})가 컨테이너 개수보다 큼.")
            return None
        target_div = div_elements[image_index]
        target_div.click()
        logging.info(f"{image_index+1}번째 이미지 컨테이너 클릭 완료.")
    except Exception as e:
        logging.error(f"이미지 컨테이너 클릭 중 에러: {str(e)}")
        return None

    # 상세보기 페이지 로드 대기: div.sc_new.sp_viewer
    try:
        logging.info("search section 3")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class="image _viewerImageBox"] img'))
        )
        logging.info("상세보기 컨테이너(div.sc_new.sp_viewer) 로드됨.")
    except TimeoutException:
        logging.error("상세보기 컨테이너(div.sc_new.sp_viewer) 로드 대기 시간 초과")
        return None

    # 상세보기 페이지 스크린샷 저장
    try:
        driver.save_screenshot("debug_detailed_page.png")
        logging.info("상세보기 페이지 스크린샷(debug_detailed_page.png) 저장됨.")
    except Exception as e:
        logging.error(f"상세보기 페이지 스크린샷 저장 실패: {str(e)}")
    
    # 단계별 태그 탐색: 상세보기 컨테이너 내에서 이미지 태그 찾기
    try:
        # 단계 1: div.sc_new.sp_viewer
        try:
            viewer_div = driver.find_element(By.CSS_SELECTOR, 'div[class="image _viewerImageBox"]')
            logging.info("단계 1: div.sc_new.sp_viewer 요소 발견.")
        except Exception as e:
            logging.error("단계 1: div.sc_new.sp_viewer 요소 탐색 실패")
            return None
 
        # 단계 4: div.image 내부의 <img> 태그 찾기
        try:
            img_element = viewer_div.find_element(By.TAG_NAME, "img")
            logging.info("단계 2: <img> 태그 발견.")
        except Exception as e:
            logging.error("단계 2: <img> 태그 탐색 실패")
            return None

        # 단계 5: <img> 태그의 src 속성 추출
        detailed_image_url = img_element.get_attribute('src')
        if not detailed_image_url:
            logging.error("단계 5: <img> 태그에서 src 속성 추출 실패")
            return None
        logging.info(f"추출한 상세 이미지 URL: {detailed_image_url}")
        return detailed_image_url

    except Exception as e:
        logging.error(f"상세 이미지 URL 추출 중 전반적 에러: {str(e)}")
        return None



def download_image(url, save_dir, max_retries=3):
    """
    Downloads an image from the given URL with multiple retries and validates its integrity.
    
    Args:
        url (str): URL of the image.
        save_dir (str): Directory to save the image.
        max_retries (int): Number of retry attempts.
    
    Returns:
        str or None: File path of the downloaded image if successful; otherwise, None.
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"naver_image_{timestamp}.jpg"
    filepath = os.path.join(save_dir, filename)
    
    ua = UserAgent()
    headers = {"User-Agent": ua.random}
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                if os.path.getsize(filepath) == 0:
                    raise Exception("다운로드한 파일이 비어 있음")
                try:
                    with Image.open(filepath) as img:
                        img.verify()
                except Exception as img_err:
                    raise Exception(f"이미지 무결성 검사 실패: {str(img_err)}")
                logging.info(f"이미지 다운로드 성공: {url}")
                return filepath
            else:
                raise Exception(f"HTTP 상태 코드 {response.status_code}")
        except Exception as e:
            logging.error(f"다운로드 시도 {attempt}회 실패: {str(e)}")
            # 연결 오류일 경우 60초 대기, 그 외는 2초 대기
            if isinstance(e, ReqConnectionError):
                time.sleep(60)
            else:
                time.sleep(2)
    
    logging.error("최대 재시도 횟수 후에도 이미지 다운로드 실패")
    return None

def download_multiple_images(search_url, num_images=4, folder_index="default"):
    """
    Downloads multiple images by randomly selecting image containers from the search results.
    Saves the images in a folder named with the given folder_index.
    
    Args:
        search_url (str): The complete search URL.
        num_images (int): Number of images to download.
        folder_index (str): Folder name (based on the index from Google Sheet) to save images.
    
    Returns:
        list: List of file paths for the successfully downloaded images.
    """
    driver = setup_driver()
    downloaded_filepaths = []
    used_indices = []
    
    # 기본 저장 폴더를 folder_index 하위로 지정
    base_save_dir = os.path.join("../../Dropbox/automation material/downloaded_images", folder_index)
    
    for i in range(num_images):
        try:
            # 새로 검색 페이지 로드 (네트워크 재시도 포함)
            if not safe_driver_get(driver, search_url):
                logging.error("검색 페이지 로드 실패로 인해 해당 이미지 스킵")
                continue
            time.sleep(5)
            containers = driver.find_elements(By.CSS_SELECTOR, 'div[class*="mod_image_tile"] img')
            total = len(containers)
            if total == 0:
                logging.error("검색 결과에서 이미지 컨테이너를 찾지 못함.")
                break
            # 아직 사용하지 않은 인덱스에서 랜덤 선택 (모두 사용했으면 전체에서 선택)
            available = [idx for idx in range(total) if idx not in used_indices]
            if not available:
                chosen_index = random.choice(range(total))
            else:
                chosen_index = random.choice(available)
            used_indices.append(chosen_index)
            logging.info(f"선택된 이미지 인덱스: {chosen_index} (총 {total}개 중)")
            
            detailed_url = get_actual_image_url(driver, search_url, image_index=chosen_index)
            if not detailed_url:
                logging.error("상세 이미지 URL 추출 실패")
                continue
            logging.info(f"다운로드할 상세 이미지 URL: {detailed_url}")
            
            saved_path = download_image(detailed_url, save_dir=base_save_dir)
            if saved_path:
                logging.info(f"이미지 저장 완료: {saved_path}")
                downloaded_filepaths.append(saved_path)
            else:
                logging.error("이미지 다운로드 실패.")
        except Exception as e:
            logging.error(f"이미지 다운로드 중 에러: {str(e)}")
    
    driver.quit()
    return downloaded_filepaths

def update_google_sheet(sheet, index_value):
    """구글 스프레드시트 C 셀에 다운로드 완료 시각 업데이트"""
 
    # ✅ 현재 시간 기록
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cell_address = f"C{index_value}"  # index_value가 행 번호라고 가정
    sheet.update_acell(cell_address, current_time)
    
    print(f"구글 스프레드시트 {cell_address} 업데이트 완료: {current_time}")

def main():
    """
    Main function to execute the process:
        1. Read the index and QUERY string from Google Sheets.
        2. Build the search URL.
        3. Download multiple images and save them in a folder named with the index.
        4. Log results.
    """
    credentials_json, spreadsheet_id = get_gsheet_config()
    query, index_value , sheet = get_query_from_gsheet(credentials_json, spreadsheet_id)
    if not query:
        logging.error("구글 스프레드시트로부터 QUERY 문자열을 읽어오지 못함.")
        print("QUERY 문자열을 읽어오지 못했습니다. 정보를 확인하세요.")
        return
    search_url = build_search_url(query)
    logging.info(f"생성된 검색 URL: {search_url}")
    print(f"검색 URL: {search_url}")        
    
    num_images = 4  # 원하는 다운로드 이미지 개수
    downloaded = download_multiple_images(search_url, num_images, folder_index=str(index_value))
    if downloaded:
        logging.info(f"총 {len(downloaded)}장의 이미지 다운로드 완료.")
        print(f"다운로드 완료된 이미지 파일들: {downloaded}")
        update_google_sheet(sheet, index_value)
    else:
        logging.error("이미지 다운로드 실패.")
        print("이미지 다운로드 실패. 로그를 확인하세요.")

if __name__ == "__main__":
    main()
