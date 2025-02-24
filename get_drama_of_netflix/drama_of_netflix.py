import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time
import random
from datetime import datetime
import json
import logging

# 로깅 설정: 성공 및 실패 로그 기록
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_with_requests(url, max_retries=3):
    """
    기본 스크래핑 방식: requests와 BeautifulSoup를 사용하여 데이터를 수집합니다.
    - User-Agent 회전, 요청 간 지연, 최대 3회 재시도 적용
    - <span class="info_txt"> 태그 내 "한국" 텍스트를 찾고, 그 조상인 <li class="info_box"> 요소 내의
      <strong class="title"> 태그에서 영화 제목(<a> 태그의 텍스트)을 추출
    """
    ua = UserAgent()
    last_error = ""
    
    for attempt in range(1, max_retries + 1):
        try:
            headers = {'User-Agent': ua.random}
            logging.info(f"Request attempt {attempt} using User-Agent: {headers['User-Agent']}")
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                error_msg = f"HTTP Error {response.status_code}"
                logging.error(f"Attempt {attempt}: {error_msg}")
                last_error = error_msg
                time.sleep(random.uniform(1, 3))
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            span_elements = soup.find_all("span", class_="info_txt")
            if not span_elements:
                error_msg = "No span elements with class 'info_txt' found. Page structure may have changed."
                logging.error(error_msg)
                raise Exception(error_msg)
            
            for span in span_elements:
                if "한국" in span.get_text():
                    # "한국" 텍스트를 포함하는 가장 가까운 <li class="info_box"> 요소 찾기
                    container = span.find_parent("li", class_="info_box")
                    if not container:
                        error_msg = "Unable to find the parent <li class='info_box'> element."
                        logging.error(error_msg)
                        continue
                    movie_title = None
                    
                    # container 내의 <strong class="title"> 태그에서 영화 제목 추출
                    strong_title = container.find("strong", class_="title")
                    if strong_title:
                        a_tag = strong_title.find("a")
                        if a_tag and a_tag.get_text(strip=True):
                            movie_title = a_tag.get_text(strip=True)
                    
                    if movie_title:
                        logging.info("Successfully scraped movie title using requests.")
                        return {
                            "movie_title": movie_title,
                            "scraping_timestamp": datetime.now().isoformat(),
                            "success_status": True,
                            "error_message": ""
                        }
                    else:
                        error_msg = "Movie title element not found in the expected <strong class='title'> structure."
                        logging.error(error_msg)
                        raise Exception(error_msg)
            
            error_msg = "No span element containing '한국' found on the page."
            logging.error(error_msg)
            raise Exception(error_msg)
        
        except Exception as e:
            last_error = str(e)
            logging.error(f"Attempt {attempt} failed: {last_error}")
            time.sleep(random.uniform(1, 3))
    
    return {
        "movie_title": None,
        "scraping_timestamp": datetime.now().isoformat(),
        "success_status": False,
        "error_message": last_error
    }

def scrape_with_selenium(url):
    """
    백업 방식: Selenium을 사용하여 데이터를 수집합니다.
    - 최신 Selenium API(By 모듈 사용)를 적용하여 Headless Chrome으로 페이지를 로드하고,
      <span class="info_txt"> 태그 내 "한국" 텍스트를 포함하는 조상 <li class="info_box"> 요소 내의
      <strong class="title"> 태그에서 영화 제목을 추출
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException, WebDriverException

        # Chrome 옵션 설정 (헤드리스 모드 및 User-Agent 설정)
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument(f"user-agent={UserAgent().random}")
        
        driver = webdriver.Chrome(options=chrome_options)
        logging.info("Selenium driver started. Fetching the page...")
        driver.get(url)
        time.sleep(random.uniform(2, 4))  # 동적 컨텐츠 로드를 위해 대기
        
        # 최신 Selenium API를 사용하여 모든 span.info_txt 요소 검색
        span_elements = driver.find_elements(By.CSS_SELECTOR, "span.info_txt")
        if not span_elements:
            error_msg = "No span elements with class 'info_txt' found using Selenium. Page structure may have changed."
            logging.error(error_msg)
            raise Exception(error_msg)
        
        for span in span_elements:
            if "한국" in span.text:
                # "한국" 텍스트가 포함된 조상 <li class="info_box"> 요소를 XPath로 찾음
                try:
                    container = span.find_element(By.XPATH, "ancestor::li[contains(@class, 'info_box')]")
                except NoSuchElementException:
                    error_msg = "Unable to find the ancestor <li class='info_box'> element using Selenium."
                    logging.error(error_msg)
                    raise Exception(error_msg)
                
                movie_title = None
                try:
                    # container 내의 <strong class="title"> 태그에서 영화 제목 추출
                    strong_title = container.find_element(By.CSS_SELECTOR, "strong.title")
                    a_tag = strong_title.find_element(By.TAG_NAME, "a")
                    movie_title = a_tag.text.strip() if a_tag.text.strip() else None
                except NoSuchElementException:
                    error_msg = "Movie title element not found in the expected <strong class='title'> structure using Selenium."
                    logging.error(error_msg)
                    raise Exception(error_msg)
                
                if movie_title:
                    logging.info("Successfully scraped movie title using Selenium.")
                    driver.quit()
                    return {
                        "movie_title": movie_title,
                        "scraping_timestamp": datetime.now().isoformat(),
                        "success_status": True,
                        "error_message": ""
                    }
        
        error_msg = "No span element containing '한국' found using Selenium."
        logging.error(error_msg)
        raise Exception(error_msg)
    
    except Exception as e:
        logging.error("Selenium scraping failed: " + str(e))
        return {
            "movie_title": None,
            "scraping_timestamp": datetime.now().isoformat(),
            "success_status": False,
            "error_message": str(e)
        }
    
    finally:
        try:
            driver.quit()
        except Exception:
            pass

def main():
    # 대상 URL: 네이버 넷플릭스 주간 순위 검색 결과
    url = "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=bkdJ&qvt=0&query=넷플릭스%20주간%20순위"
    
    # 우선 기본 방식으로 스크래핑 시도
    result = scrape_with_requests(url)
    
    # 기본 방식이 실패하면 Selenium 백업 방식으로 전환
    if not result["success_status"]:
        logging.info("Primary scraping method failed. Switching to Selenium backup method.")
        result = scrape_with_selenium(url)
    
    # JSON 형식으로 결과 출력
    output_json = json.dumps(result, ensure_ascii=False, indent=4)
    print(output_json)

if __name__ == "__main__":
    main()
