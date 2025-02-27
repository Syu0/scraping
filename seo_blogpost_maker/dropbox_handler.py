import dropbox
from config import DROPBOX_ACCESS_TOKEN

def get_dropbox_client():
    try:
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        dbx.users_get_current_account()  # 인증 확인
        return dbx
    except dropbox.exceptions.AuthError as e:
        print("Dropbox 인증 오류:", e)
        return None

def get_existing_shared_link(dbx, file_path):
    """ 기존 공유 링크가 존재하면 가져오기 """
    try:
        shared_links = dbx.sharing_list_shared_links(file_path)
        if shared_links.links:
            return shared_links.links[0].url.replace("www.dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "")
    except dropbox.exceptions.ApiError as e:
        print(f"Dropbox 링크 가져오기 오류: {e}")
    return None

def get_dropbox_links(subfolder):
    dbx = get_dropbox_client()
    if not dbx:
        return []

    folder_path = f"/automation material/downloaded_images/{subfolder}"
    try:
        result = dbx.files_list_folder(folder_path)
        links = []
        for entry in result.entries:
            existing_link = get_existing_shared_link(dbx, entry.path_display)
            if existing_link:
                print(f"✅ 기존 공유 링크 사용: {existing_link}")
                links.append(existing_link)
            else:
                shared_link = dbx.sharing_create_shared_link_with_settings(entry.path_display).url
                shared_link = shared_link.replace("www.dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "")
                links.append(shared_link)
        print("[Dropbox 이미지 링크 확인]", links)
        return links
    except dropbox.exceptions.AuthError as e:
        print("Dropbox 링크 가져오기 오류: Access Token이 만료되었거나 잘못되었습니다.", e)
        return []
