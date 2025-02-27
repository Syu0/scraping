import requests
from config import HASHNODE_API_KEY, HASHNODE_BLOG_ID

def post_to_hashnode(title, content):
    url = "https://gql.hashnode.com"
    headers = {
        "Authorization": HASHNODE_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "query": """
        mutation PublishPost($input: PublishPostInput!) {
            publishPost(input: $input) {
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
                "title": title,
                "contentMarkdown": content,
                "publicationId": HASHNODE_BLOG_ID
            }
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()
