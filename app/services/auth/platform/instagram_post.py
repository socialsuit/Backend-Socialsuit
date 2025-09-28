import requests

def call_instagram_post(user_token: dict, post_payload: dict):
    ig_user_id = user_token.get("ig_user_id")
    access_token = user_token.get("access_token")

    image_url = post_payload.get("image_url")
    caption = post_payload.get("caption")

    # 1) Create Container
    create_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"
    create_payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": access_token
    }
    create_res = requests.post(create_url, data=create_payload).json()
    container_id = create_res.get("id")

    # 2) Publish Container
    publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"
    publish_payload = {
        "creation_id": container_id,
        "access_token": access_token
    }
    publish_res = requests.post(publish_url, data=publish_payload).json()

    return publish_res