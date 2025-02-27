import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_AUTH, SHEET_NAME, TAB_NAME
from datetime import datetime
import os

print("현재 GOOGLE_AUTH 경로:", GOOGLE_AUTH)
print("파일 존재 여부:", os.path.exists(GOOGLE_AUTH))

def get_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_file(GOOGLE_AUTH, scopes=scopes)
    client = gspread.authorize(credentials)

    return client.open("자동화_글감").worksheet("베트남호텔")

# ✅ Google 시트에서 포스팅할 호텔명 가져오기
def get_hotel_name():
    sheet = get_google_sheet()
    data = sheet.get_all_values()
    for row_idx, row in enumerate(data[1:], start=2):  # 첫 번째 행은 헤더이므로 건너뜀
        hotel_name = row[6].strip()  # G열 (hotel_name)
        if hotel_name == "":  # 호텔명이 비어있는 경우
            print("포스팅할 호텔 데이터가 없습니다. empty G열")
            continue
        elif row[1].strip() == "":  # B열이 비어있는 경우 (포스팅되지 않은 호텔 찾기)
            return hotel_name, str(row_idx)  # row_idx를 문자열로 변환하여 사용
    return None, None

# ✅ Google 시트에서 호텔 정보 가져오기 (누락된 함수 추가)
def fetch_hotel_details(row_idx):
    sheet = get_google_sheet()
    data = sheet.get_all_values()
    row = data[int(row_idx) - 1]  # 행 번호를 기반으로 데이터 가져오기
    hotel_info = {
        "hotel_name": row[6],
        "price": row[7],
        "address": row[8],
        "star": row[9],
        "reviews": row[10],
        "extra_info": row[11]
    }
    return hotel_info

# ✅ Google 시트 업데이트 함수
def update_google_sheet(row_idx, post_url):
    sheet = get_google_sheet()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.update_acell(f"B{row_idx}", current_time)  # 포스팅 완료 시간 업데이트
    sheet.update_acell(f"D{row_idx}", post_url)  # 포스팅된 URL 업데이트
