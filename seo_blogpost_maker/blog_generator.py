import openai
from config import OPENAI_API_KEY, PROMPT_PATH
from dropbox_handler import get_dropbox_links

openai.api_key = OPENAI_API_KEY

def load_prompt():
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read().strip()

def generate_blog_content(hotel_info, row_idx):
    dropbox_links = get_dropbox_links(row_idx)

    if not dropbox_links:
        return f"## {hotel_info['hotel_name']}\n\n(이미지를 불러오지 못했습니다.)\n\n"

    prompt = load_prompt()

    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a professional travel blogger."},
            {"role": "user", "content": f"{prompt}\n\n{hotel_info}"}
        ]
    )
    generated_content = response.choices[0].message.content

    for link in dropbox_links:
        generated_content = generated_content.replace("(image)", f"![이미지]({link})", 1)

    return generated_content
