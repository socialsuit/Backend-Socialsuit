import requests

def call_linkedin_post(user_token: dict, post_payload: dict):
    access_token = user_token.get("access_token")
    message = post_payload.get("message")
    author_urn = user_token.get("author_urn")  # e.g. "urn:li:person:xxxx"

    url = "https://api.linkedin.com/v2/ugcPosts"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }

    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": message
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    res = requests.post(url, headers=headers, json=payload)
    return res.json()