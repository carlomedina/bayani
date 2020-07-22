import requests
import logging

log = logging.getLogger("kartero")


class AuthenticationError(Exception):
    def __init__(self, error="", message="Authentication failed"):
        self.message = f"{ message }\n{ error }"
        super().__init__(self.message)


def get_page_token_user(user_access_token, user_id=""):
    if user_id == "" and page_id == "":
        raise ValueError("If method == user, user_id cannot be empty")
    payload = {
        "fields": "name,access_token",
        "access_token": f"{user_access_token}",
    }
    res = requests.get(f"https://graph.facebook.com/{user_id}/accounts", params=payload)

    if res.status_code == 200:
        response = res.json()
        tokens = response["data"]
        filtered_tokens = list(filter(lambda d: d["id"], tokens))
        if len(filtered_tokens) > 0:
            log.info("Received a page token")
            return filtered_tokens[0]["access_token"]
    else:
        log.error("Failed to get long term token")
        error_response = res.json()
        raise_error_message(error_response)


def get_page_token_page(user_access_token, page_id=""):
    if page_id == "":
        raise ValueError("If method == page, page_id cannot be empty")
    payload = {"fields": "access_token", "access_token": f"{user_access_token}"}
    res = requests.get(f"https://graph.facebook.com/{page_id}", params=payload)
    payload = {"fields": "access_token", "access_token": f"{user_access_token}"}

    if res.status_code == 200:
        log.info("Received a page token")
        response = res.json()
        return response["access_token"]

    else:
        log.error("Failed to get page token")
        error_response = res.json()
        raise_error_message(error_response)


def get_page_token(user_access_token, page_id="", user_id="", method="page"):
    if method == "user":
        return get_page_token_user(user_access_token, user_id=user_id)
    else:
        return get_page_token_page(user_access_token, page_id=page_id)


def publish_post(page_id, page_token, message, title=""):
    payload = {"message": message, "access_token": page_token}
    res = requests.post(f"https://graph.facebook.com/{page_id}/feed", data=payload)

    if res.status_code == 200:
        response = res.json()
        id = response["id"]
        post_id = id.split("_")[1]
        log.info(
            f"Posted content to facebook: https://www.facebook.com/{ post_id } { title }"
        )
        return response["id"]
    else:
        log.error("Failed to post")
        error_response = res.json()
        raise_error_message(error_response)


def update_post(page_post_id, page_token, message, title=""):
    payload = {"message": message, "access_token": page_token}
    res = requests.post(f"https://graph.facebook.com/{page_post_id}", data=payload)

    if res.status_code == 200:
        response = res.json()
        if response["success"]:
            log.info(f"Updated content { page_post_id }")
            return response["success"]
        else:
            log.error(
                f"Failed updating the content at https://www.facebook.com/{ page_post_id }"
            )
    else:
        log.error("Failed to update post")
        error_response = res.json()
        raise_error_message(error_response)


def get_long_term_token(user_access_token, page_id="", app_id="", app_secret=""):
    if app_id == "" or app_secret == "":
        raise ValueError("If method == oauth, app_id and app_secret cannot be empty")
    payload = {
        "grant_type": "fb_exchange_token",
        "client_id": f"{app_id}",
        "client_secret": f"{app_secret}",
        "fb_exchange_token": f"{user_access_token}",
    }
    res = requests.get("https://graph.facebook.com/oauth/access_token", params=payload)

    if res.status_code == 200:
        log.info("Received a long-term token")
        response = res.json()
        return response["access_token"]
    else:
        log.error("Failed to get long term token")
        error_response = res.json()
        raise_error_message(error_response)


def raise_error_message(response):
    err = response["error"]
    message = f"{ err.get('type', '') }, { err.get('code', '') }"
    raise AuthenticationError(message)


def get_notion_id(filename):
    id = filename.split(" ")[-1].replace(".md", "")
    return canonical_uuid(id)


def extract_notion_text(file, do_append_notion_id=True, is_debug=False):
    notion_id = get_notion_id(file)
    text = open(os.path.join(cleaned_dir, file), "r")
    message = "".join(text.readlines())
    if do_append_notion_id:
        message += f"\n\n{notion_id}"
    if is_debug:
        # todo: temporary append 'noise' during testing
        message += f"\n{str(random.randint(0,10))}"
    return notion_id, message


def batch_send_posts(cleaned_dir, mapping_csv):
    map = dict()
    if os.path.exists(mapping_csv):
        with open(mapping_csv, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                map[row["notion_id"]] = row["fb_id"]

    for file in os.listdir(cleaned_dir):
        notion_id, message = extract_notion_text(file)

        if notion_id in map:
            page_post_id = map[notion_id]
            try:
                fb_id = update_post(page_post_id, page_token, message=message)
            except AuthenticationError:
                log.warning(
                    f"Cannot find {page_post_id} on fb anymore, trying to publish on a new page"
                )
                fb_id = publish_post(page_id, page_token=page_token, message=message)
                map[notion_id] = fb_id
                update_csv(map, mapping_csv)
        else:
            fb_id = publish_post(page_id, page_token=page_token, message=message)
            map[notion_id] = fb_id
            update_csv(map, mapping_csv)
            log.info(f"Added {notion_id} to {fb_id}")


def update_csv(map, mapping_csv):
    with open(mapping_csv, newline="") as csvfile:
        fieldnames = ["notion_id", "fb_id"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for notion_id, fb_id in map.items():
            writer.writerow({"notion_id": notion_id, "fb_id": fb_id})

    return None
