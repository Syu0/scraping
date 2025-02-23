#!/usr/bin/env python3
"""
Script to download the detailed image from a specific Naver image search result.

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
    3. Finds and clicks the 3rd image container.
    4. Waits for the detailed view to load (div.sc_new.sp_viewer) and saves its screenshot (debug_detailed_page.png).
    5. Step-by-step, it navigates through:
         - div.sc_new.sp_viewer
         - div.viewer_image._fe_image_viewer_main_image_wrap
         - div.image
         - <img> tag
       and extracts the src attribute.
    6. Downloads the image with retries, validates its integrity, and logs the original image URL.
"""

import os
import time
import logging
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

def get_actual_image_url(driver):
    """
    Loads the Naver image search URL, clicks the 3rd image container,
    saves a screenshot of the detailed view, and then step-by-step navigates
    through the following elements to extract the detailed image URL:
        1. div.sc_new.sp_viewer
        2. div.viewer_image._fe_image_viewer_main_image_wrap (inside sc_new.sp_viewer)
        3. div.image (inside main image wrap)
        4. <img> tag (inside div.image)
    Each step logs success/failure.
    
    Args:
        driver (webdriver.Chrome): Selenium WebDriver instance.
    
    Returns:
        str or None: The detailed image URL if extraction succeeds; otherwise, None.
    """
    target_url = "https://search.naver.com/search.naver?ssc=tab.image.all&where=image&sm=tab_jum&query=나트랑+레스찹호텔"
    try:
        driver.get(target_url)
        logging.info(f"URL 로드 성공: {target_url}")
    except Exception as e:
        logging.error(f"URL {target_url} 로드 중 에러: {str(e)}")
        return None

    # 대기: 페이지의 동적 컨텐츠가 로드될 때까지
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
        if len(div_elements) < 3:
            logging.error("이미지 컨테이너가 3개 미만임.")
            return None
        target_div = div_elements[2]
        target_div.click()
        logging.info("3번째 이미지 컨테이너 클릭 완료.")
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

def main():
    """
    Main function to execute the process:
        1. Set up Selenium driver.
        2. Retrieve the detailed image URL via get_actual_image_url.
        3. Download the image.
        4. Log results.
    """
    driver = None
    try:
        driver = setup_driver()
        image_url = get_actual_image_url(driver)
        if not image_url:
            logging.error("상세 이미지 URL을 추출하지 못함.")
            print("상세 이미지 URL 추출 실패. 로그를 확인하세요.")
            return
        
        logging.info(f"다운로드할 상세 이미지 URL: {image_url}")
        
        downloaded_filepath = download_image(image_url, save_dir="downloaded_images")
        if downloaded_filepath:
            logging.info(f"이미지 저장 완료: {downloaded_filepath}")
            print(f"이미지가 성공적으로 다운로드됨: {downloaded_filepath}")
        else:
            logging.error("이미지 다운로드 실패 (최대 재시도 후)")
            print("이미지 다운로드 실패. 로그를 확인하세요.")
    except WebDriverException as wd_err:
        logging.error(f"Selenium WebDriver 에러: {str(wd_err)}")
        print("Selenium WebDriver 에러 발생. 로그를 확인하세요.")
    except Exception as e:
        logging.error(f"예상치 못한 에러: {str(e)}")
        print("예상치 못한 에러 발생. 로그를 확인하세요.")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
