from google_sheets import fetch_hotel_details, update_google_sheet, get_hotel_name
from blog_generator import generate_blog_content
from hashnode_poster import post_to_hashnode

def main():
    hotel_name, row_idx = get_hotel_name()
    if not hotel_name:
        print("포스팅할 호텔 데이터가 없습니다.")
        return

    hotel_info = fetch_hotel_details(row_idx)
    content = generate_blog_content(hotel_info, row_idx)
    post_response = post_to_hashnode(hotel_info["hotel_name"], content)

    if "errors" in post_response:
        print("포스팅 실패:", post_response)
        return

    post_url = post_response["data"]["publishPost"]["post"]["url"]
    update_google_sheet(row_idx, post_url)
    print("포스팅 완료, URL:", post_url)

if __name__ == "__main__":
    main()
