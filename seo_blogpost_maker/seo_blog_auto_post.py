import openai
import requests
import random
from datetime import datetime
import os
# For Google Sheets integration
import gspread
from google.oauth2.service_account import Credentials


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.txt")
GOOGLE_AUTH = os.path.join(BASE_DIR, "google_credentials.json")
# API 키 및 블로그 ID를 별도 파일에서 로드
def load_api_keys():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        keys = {}
        for line in f:
            key, value = line.strip().split("=")
            keys[key] = value
    return keys 

keys = load_api_keys()
OPENAI_API_KEY = keys["OPENAI_API_KEY"]
HASHNODE_API_KEY = keys["HASHNODE_API_KEY"]
HASHNODE_BLOG_ID = keys["HASHNODE_BLOG_ID"]
CREDENTIALS_JSON = keys["CREDENTIALS_JSON"]
SHEET_NAME = keys["SHEET_NAME"]


def get_gsheet_config():
    """
    Prompts the user for Google Sheets integration information.
    
    Returns:
        tuple: (credentials_json, spreadsheet_id)
    """

    credentials_json = r"C:\Users\skfka\OneDrive\문서\GitHub\scraping\get_hotel_image\secret\intense-reason-451806-j0-5160a24584f2.json"
    # 백슬래시 문제 방지를 위해 raw string 또는 이스케이프 문자를 사용하세요.
    spreadsheet_id = r"1gQ3Ac1_2sUd4EiTRwi_VCLyxNeBbsf-_z47k4JONPmc"
    return credentials_json, spreadsheet_id

# 구글 스프레드시트에서 데이터 가져오기
def get_google_sheet_data(credentials_json, spreadsheet_id, tab_name, column_index):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_file(credentials_json, scopes=scopes)
    client = gspread.authorize(credentials)
    worksheet = client.open_by_key(spreadsheet_id).worksheet(tab_name)
 
    return worksheet.col_values(column_index)

# 랜덤 후반 멘트 리스트를 구글 스프레드시트에서 가져오기
credentials_json, spreadsheet_id = get_gsheet_config()
RANDOM_CLOSING_REMARKS = get_google_sheet_data(credentials_json, spreadsheet_id, "후반멘트", 1)
# HTML 형식으로 글 생성 함수
def generate_blog_content(hotel_name, location, room_type, address, map_link, cleanliness, amenities, image_paths):
    html_content = f"""
    <html>
    <head>
        <title>{location} {hotel_name} {room_type}</title>
        <style>
            body {{ text-align: center; }}
            table {{ margin: auto; border-collapse: collapse; width: 60%; }}
            th, td {{ border: 1px solid black; padding: 8px; }}
            img {{ max-width: 80%; height: auto; display: block; margin: auto; }}
        </style>
    </head>
    <body>
    <h1>{location} {hotel_name} {room_type}</h1>
    <p><img src='{image_paths[0]}' alt='호텔 위치'></p>
    
    <h2>🏨 호텔 위치</h2>
    <p>📍 주소: {address}</p>
    <p>🗺 지도 링크: <a href='{map_link}'>구글 지도 보기</a></p>
    
    <h2>🛏️ 호텔 기본 정보</h2>
    <table>
        <tr><th>항목</th><th>내용</th></tr>
        <tr><td>위치 특징</td><td>{location}</td></tr>
        <tr><td>룸타입</td><td>{room_type}</td></tr>
        <tr><td>청결도</td><td>{cleanliness}</td></tr>
        <tr><td>편의시설</td><td>{amenities}</td></tr>
    </table>
    
    <p><img src='{image_paths[1]}' alt='호텔 편의시설'></p>
    
    <h2>🏖️ 호텔 편의시설</h2>
    <ul style='display: inline-block; text-align: left;'>
        <li>🏊‍♂️ 수영장: 있음 / 없음</li>
        <li>🍽 조식: 제공 / 불포함</li>
        <li>🚕 공항 픽업: 가능 / 불가능</li>
    </ul>
    
    <p><img src='{image_paths[2]}' alt='호텔 주변'></p>
    
    <p>{random.choice(RANDOM_CLOSING_REMARKS)}</p>
    
    <h3>📌 다음 포스팅은 <strong>{hotel_name} 근처 맛집 추천</strong>으로 만나요! 🎉</h3>
    
    <p>#나트랑자유여행 #나트랑숙소추천 #가성비호텔 #나트랑호텔</p>
    </body>
    </html>
    """
    return html_content

# Hashnode에 포스팅하는 함수
def post_to_hashnode(title, content):
    url = "https://gql.hashnode.com"
    headers = {
        "Authorization": HASHNODE_API_KEY,
        "Content-Type": "application/json"
    }
    
    # 1️⃣ 초안 생성 요청
    draft_payload = {
        "query": """
        mutation CreateDraft($input: CreateDraftInput!) {
            createDraft(input: $input) {
                draft {
                    id
                }
            }
        }
        """,
        "variables": {
            "input": {
                "publicationId": HASHNODE_BLOG_ID,
                "title": title,
                "contentMarkdown": content
            }
        }
    }
    
    draft_response = requests.post(url, json=draft_payload, headers=headers).json()
    
    if "errors" in draft_response:
        print("초안 생성 실패:", draft_response)
        return draft_response
    
    draft_id = draft_response["data"]["createDraft"]["draft"]["id"]
    
    # 2️⃣ 초안 게시 요청 (draftId 사용)
    publish_payload = {
        "query": """
        mutation PublishDraft($input: PublishDraftInput!) {
            publishDraft(input: $input) {
                post {
                    id
                    title
                    url
                }
            }
        }
        """,
        "variables": {
            "input": {
                "draftId": draft_id  # ✅ draftId로 변경
            }
        }
    }
    
    publish_response = requests.post(url, json=publish_payload, headers=headers).json()
    
    return publish_response


# 테스트 실행
def main():
    hotel_name = "나트랑 버고 호텔"
    location = "나트랑 시내 가성비 숙소"
    room_type = "디럭스 룸"
    address = "123 Beach St, Nha Trang, Vietnam"
    map_link = "https://goo.gl/maps"
    cleanliness = "청결함, 수압 좋음, 벌레 없음"
    amenities = "조식 제공, 수영장 있음, 공항 픽업 가능"
    
    # 이미지 파일 경로 지정 (사용자가 제공하는 경로 기반)
    image_folder = "your_image_folder_path"  # 실제 경로로 변경해야 함
    image_paths = [os.path.join(image_folder, f"image{i+1}.jpg") for i in range(3)]
    
    title = f"{location} {hotel_name} {room_type}"
    content = f"## {title}\n\n" + \
              f"![호텔 위치]({image_paths[0]})\n\n" + \
              f"**🏨 호텔 위치**\n\n📍 주소: {address}\n\n[🗺 구글 지도 보기]({map_link})\n\n" + \
              f"**🛏️ 호텔 기본 정보**\n\n| 항목 | 내용 |\n|------|------|\n| 위치 특징 | {location} |\n| 룸타입 | {room_type} |\n| 청결도 | {cleanliness} |\n| 편의시설 | {amenities} |\n\n" + \
              f"![호텔 편의시설]({image_paths[1]})\n\n" + \
              f"**🏖️ 호텔 편의시설**\n\n- 🏊‍♂️ 수영장: 있음 / 없음\n- 🍽 조식: 제공 / 불포함\n- 🚕 공항 픽업: 가능 / 불가능\n\n" + \
              f"![호텔 주변]({image_paths[2]})\n\n" + \
              f"{random.choice(RANDOM_CLOSING_REMARKS)}\n\n" + \
              f"**📌 다음 포스팅은 {hotel_name} 근처 맛집 추천으로 만나요! 🎉**\n\n" + \
              f"#나트랑자유여행 #나트랑숙소추천 #가성비호텔 #나트랑호텔"
    
    post_response = post_to_hashnode(title, content)
    print("포스팅 완료:", post_response)


    ''' 
    content = generate_blog_content(hotel_name, location, room_type, address, map_link, cleanliness, amenities, image_paths)
    
    with open("blog_post.html", "w", encoding="utf-8") as file:
        file.write(content)
    
    print("HTML 파일로 블로그 글 생성 완료: blog_post.html")
    '''



if __name__ == "__main__":
    main()