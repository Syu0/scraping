import requests
import logging
from fake_useragent import UserAgent

# 로깅 설정: INFO 레벨 메시지를 콘솔에 출력
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def save_response_html_to_file(url, filename="response.html"):
    """
    주어진 URL에 HTTP GET 요청을 보내 응답받은 HTML 전체를 파일로 저장하는 함수입니다.
    - fake_useragent를 사용해 User-Agent를 회전합니다.
    - HTTP 오류 발생 시 예외를 처리합니다.
    - 응답 HTML을 filename에 저장합니다.
    """
    ua = UserAgent()
    headers = {'User-Agent': ua.random}
    logging.info(f"Using User-Agent: {headers['User-Agent']}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
    except Exception as e:
        logging.error(f"Failed to fetch page: {e}")
        return
    
    # 응답 HTML 전체를 파일로 저장 (UTF-8 인코딩)
    try:
        with open(filename, "w", encoding="utf-8") as file:
            file.write(response.text)
        logging.info(f"HTML content saved to file: {filename}")
    except Exception as e:
        logging.error(f"Failed to save HTML to file: {e}")

if __name__ == "__main__":
    # 테스트용 URL (필요한 URL로 변경 가능)
    url = "https://m.search.naver.com/search.naver?ssc=tab.m_image.all&where=m_image&sm=tab_jum&query=%EB%82%98%ED%8A%B8%EB%9E%91+%EB%A0%88%EC%8A%A4%EC%B0%B8%ED%98%B8%ED%85%94"
    save_response_html_to_file(url)
