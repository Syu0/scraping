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

# 명시적OpenAI API 키 설정
openai.api_key = OPENAI_API_KEY

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

credentials_json, spreadsheet_id = get_gsheet_config()



# hotel_name 가져오기 (B열이 비어있는 경우만)
def get_hotel_name():
    sheet = get_google_sheet(credentials_json, spreadsheet_id,'베트남호텔')
    data = sheet.get_all_values()
    for row_idx, row in enumerate(data[1:], start=2):  # 첫 번째 행은 헤더이므로 건너뜀
        hotel_name = row[0].strip()
        if row[1].strip() == "":  # B열이 비어있는 경우
            return hotel_name, row_idx
    return None, None

# 구글 시트 연동 설정
def get_google_sheet(credentials_json, spreadsheet_id,tab_name):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_file(credentials_json, scopes=scopes)
    client = gspread.authorize(credentials)
    worksheet = client.open_by_key(spreadsheet_id).worksheet(tab_name)
 
    return worksheet



 #ChatGPT를 활용하여 최신 정보 가져오기
def fetch_hotel_details(hotel_name):
    prompt = f"""
    최신 정보를 반영하여 아래 호텔 정보를 제공해줘:
    호텔 이름: {hotel_name}
    필요한 정보:
    1. 대표적인 룸타입 (예: 디럭스 룸, 스탠다드 룸 등)
    2. 주소 (가급적 정확한 위치)
    3. 청결도 (사용자 후기를 반영, 예: 청결함, 벌레 없음, 수압 좋음 등)
    4. 편의시설 (조식 제공 여부, 수영장, 공항 픽업 등 포함)
    """
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    details = response.choices[0].message.content
    return details.split("\n")


# 구글 시트 업데이트
def update_google_sheet(row_idx, post_url):
    sheet = get_google_sheet(credentials_json, spreadsheet_id,"베트남호텔")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.update_acell(f"B{row_idx}", current_time)  # 포스팅 완료 시간 업데이트
    sheet.update_acell(f"D{row_idx}", post_url)  # 포스팅된 URL 업데이트


# 구글 스프레드시트에서 데이터 가져오기
def get_google_sheet_data(credentials_json, spreadsheet_id, tab_name, column_index):
 
    worksheet = get_google_sheet(credentials_json, spreadsheet_id,tab_name)
 
    return worksheet.col_values(column_index)


# 랜덤 후반 멘트 리스트를 구글 스프레드시트에서 가져오기

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

# Hashnode 포스팅 실행
def main():
    hotel_name, row_idx = get_hotel_name()
    if not hotel_name:
        print("포스팅할 호텔 데이터가 없습니다.")
        return
    
    hotel_details = fetch_hotel_details(hotel_name)
    room_type, address, cleanliness, amenities = hotel_details[:4]
    
    title = f"{hotel_name} ({room_type})"
    content = f"## {title}\n\n" + \
              f"**🏨 호텔 정보**\n\n- 📍 주소: {address}\n- 🛏️ 룸타입: {room_type}\n- 🧹 청결도: {cleanliness}\n- 🏊 편의시설: {amenities}\n\n"
    
    post_response = post_to_hashnode(title, content)
    if "errors" in post_response:
        print("포스팅 실패:", post_response)
        return
    
    post_url = post_response["data"]["publishDraft"]["post"]["url"]
    update_google_sheet(row_idx, post_url)
    print("포스팅 완료, URL:", post_url)


    ''' 
    content = generate_blog_content(hotel_name, location, room_type, address, map_link, cleanliness, amenities, image_paths)
    
    with open("blog_post.html", "w", encoding="utf-8") as file:
        file.write(content)
    
    print("HTML 파일로 블로그 글 생성 완료: blog_post.html")
    '''



if __name__ == "__main__":
    main()