#!/usr/bin/env python3
"""
Script to download multiple detailed images from a specific Naver image search result.

Requirements:
    - BeautifulSoup4
    - requests
    - selenium
    - fake_useragent
    - pillow  (for image integrity validation)

Usage:
    python download_naver_image.py

The script:
    1. Loads the Naver image search page.
    2. Saves an initial screenshot (debug_page.png).
    3. Finds image containers ("div.tile_item._fe_image_tab_content_tile") on the page.
    4. Randomly selects one container (ensuring different indices if possible) and clicks it.
    5. Waits for the detailed view to load (div.sc_new.sp_viewer) and saves its screenshot (debug_detailed_page.png).
    6. Step-by-step, navigates through:
         - div.sc_new.sp_viewer
         - div.viewer_image._fe_image_viewer_main_image_wrap
         - div.image
         - <img> tag  
       and extracts the src attribute.
    7. Downloads the image with retries, validates its integrity, and logs the original image URL.
    8. Repeats the above process for a specified number of images.
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

# Configure logging to file
logging.basicConfig(
    filename='download.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

SEARCH_URL = "https://search.naver.com/search.naver?ssc=tab.image.all&where=image&sm=tab_jum&query=나트랑+레스찹호텔"

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

def get_actual_image_url(driver, image_index=2):
    """
    Loads the search URL, clicks the image container at the specified index,
    saves a screenshot of the detailed view, and then step-by-step navigates
    through the following elements to extract the detailed image URL:
        1. div.sc_new.sp_viewer
        2. div.viewer_image._fe_image_viewer_main_image_wrap (inside sc_new.sp_viewer)
        3. div.image (inside main image wrap)
        4. <img> tag (inside div.image)
    Each step logs success/failure.
    
    Args:
        driver (webdriver.Chrome): Selenium WebDriver instance.
        image_index (int): The index of the image container to click.
    
    Returns:
        str or None: The detailed image URL if extraction succeeds; otherwise, None.
    """
    try:
        driver.get(SEARCH_URL)
        logging.info(f"URL 로드 성공: {SEARCH_URL}")
    except Exception as e:
        logging.error(f"URL {SEARCH_URL} 로드 중 에러: {str(e)}")
        return None

    # 동적 컨텐츠 로드를 위해 대기
    time.sleep(5)
    
    # 초기 페이지 스크린샷 저장
    try:
        driver.save_screenshot("debug_page.png")
        logging.info("초기 페이지 스크린샷(debug_page.png) 저장됨.")
    except Exception as e:
        logging.error(f"초기 페이지 스크린샷 저장 실패: {str(e)}")

    # 이미지 컨테이너 로드 대기
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.tile_item._fe_image_tab_content_tile"))
        )
        logging.info("이미지 컨테이너 요소 로드됨.")
    except TimeoutException:
        logging.error("이미지 컨테이너 요소 로드 대기 시간 초과")
        return None

    try:
        div_elements = driver.find_elements(By.CSS_SELECTOR, "div.tile_item._fe_image_tab_content_tile")
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
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc_new.sp_viewer"))
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
    
    # 단계별 태그 탐색
    try:
        # 단계 1: div.sc_new.sp_viewer
        try:
            viewer_div = driver.find_element(By.CSS_SELECTOR, "div.sc_new.sp_viewer")
            logging.info("단계 1: div.sc_new.sp_viewer 요소 발견.")
        except Exception as e:
            logging.error("단계 1: div.sc_new.sp_viewer 요소 탐색 실패")
            return None

        # 단계 2: div.viewer_image._fe_image_viewer_main_image_wrap 내부 탐색
        try:
            main_image_wrap = viewer_div.find_element(By.CSS_SELECTOR, "div.viewer_image._fe_image_viewer_main_image_wrap")
            logging.info("단계 2: div.viewer_image._fe_image_viewer_main_image_wrap 요소 발견.")
        except Exception as e:
            logging.error("단계 2: div.viewer_image._fe_image_viewer_main_image_wrap 요소 탐색 실패")
            return None

        # 단계 3: main_image_wrap 내부에서 div.image 요소 탐색
        try:
            image_div = main_image_wrap.find_element(By.CSS_SELECTOR, "div.image")
            logging.info("단계 3: div.image 요소 발견.")
        except Exception as e:
            logging.error("단계 3: div.image 요소 탐색 실패")
            return None

        # 단계 4: image_div 내부의 <img> 태그 탐색
        try:
            img_element = image_div.find_element(By.TAG_NAME, "img")
            logging.info("단계 4: <img> 태그 발견.")
        except Exception as e:
            logging.error("단계 4: <img> 태그 탐색 실패")
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
            time.sleep(2)
    
    logging.error("최대 재시도 횟수 후에도 이미지 다운로드 실패")
    return None

def download_multiple_images(num_images=4):
    """
    Downloads multiple images by randomly selecting image containers from the search results.
    
    Args:
        num_images (int): Number of images to download.
    
    Returns:
        list: List of file paths for the successfully downloaded images.
    """
    driver = setup_driver()
    downloaded_filepaths = []
    used_indices = []
    
    for i in range(num_images):
        try:
            # 새로 검색 페이지 로드
            driver.get(SEARCH_URL)
            time.sleep(5)
            containers = driver.find_elements(By.CSS_SELECTOR, "div.tile_item._fe_image_tab_content_tile")
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
            
            detailed_url = get_actual_image_url(driver, image_index=chosen_index)
            if not detailed_url:
                logging.error("상세 이미지 URL 추출 실패")
                continue
            logging.info(f"다운로드할 상세 이미지 URL: {detailed_url}")
            
            saved_path = download_image(detailed_url, save_dir="downloaded_images")
            if saved_path:
                logging.info(f"이미지 저장 완료: {saved_path}")
                downloaded_filepaths.append(saved_path)
            else:
                logging.error("이미지 다운로드 실패.")
        except Exception as e:
            logging.error(f"이미지 다운로드 중 에러: {str(e)}")
    
    driver.quit()
    return downloaded_filepaths

def main():
    """
    Main function to execute the process:
        1. Download multiple images.
        2. Log results.
    """
    num_images = 4  # 원하는 다운로드 이미지 개수
    downloaded = download_multiple_images(num_images)
    if downloaded:
        logging.info(f"총 {len(downloaded)}장의 이미지 다운로드 완료.")
        print(f"다운로드 완료된 이미지 파일들: {downloaded}")
    else:
        logging.error("이미지 다운로드 실패.")
        print("이미지 다운로드 실패. 로그를 확인하세요.")

if __name__ == "__main__":
    main()
