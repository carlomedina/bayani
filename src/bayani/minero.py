import requests
import logging
import urllib.parse
from datetime import datetime
import re

from .utils import canonical_uuid

log = logging.getLogger("minero")




def can_connect_to_notion(
    token, endpoint="https://www.notion.so/api/v3/getUserAnalyticsSettings"
):
    payload = {"platform": "web"}
    cookies = {"token_v2": f"{ token }"}
    res = requests.post(endpoint, json=payload, cookies=cookies)
    if res.status_code == 200:
        log.info("Received response from notion. Checking if token is valid...")
        response = res.json()
        if "user_id" in response:
            log.info(f"Validated token. Logged in as { response['user_id'] }")
            return True
        else:
            log.warning("Likely invalidated token")
    else:
        log.error("Cannot connect to notion")
    return False


def trigger_export(
    token,
    block_id,
    is_recursive=True,
    endpoint="https://www.notion.so/api/v3/enqueueTask",
):
    payload = {
        "task": {
            "eventName": "exportBlock",
            "request": {
                "blockId": f"{ canonical_uuid(block_id) }",
                "recursive": is_recursive,
                "exportOptions": {
                    "exportType": "markdown",
                    "timeZone": "America/New_York",
                    "locale": "en",
                },
            },
        }
    }
    cookies = {"token_v2": f"{ token }"}

    res = requests.post(endpoint, json=payload, cookies=cookies)

    if res.status_code == 200:
        response = res.json()
        task_id = response["taskId"]
        log.info(f"Succeeded in triggering export. Task Id is { task_id }")
        return task_id
    else:
        log.error(f"Failed to trigger. Server returned this response: \n{ res.text }")
        return None


def get_export_status(token, task_id, endpoint="https://www.notion.so/api/v3/getTasks"):
    payload = {"taskIds": [f"{ task_id }"]}
    cookies = {"token_v2": f"{ token }"}
    res = requests.post(endpoint, json=payload, cookies=cookies)
    if res.status_code == 200:
        response = res.json()
        status = response["results"][0]
    else:
        log.error(f"Failed to get status. Server returned this response: \n{ res.text }")
    return status


def get_filename(link):
    parsed_link = urllib.parse.urlparse(link)
    query_string = urllib.parse.parse_qs(parsed_link.query)
    try:
        filename = re.search(
            '"(.+)"$', query_string["response-content-disposition"][0]
        ).group(1)
    except AttributeError:
        log.warning("Cannot determine filename. Creating a timestamp filename...")
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"Export-no-name-{ now }.zip"
    return filename


def download_export(link, save_to=".", save_as=None, chunk_size=128):
    res = requests.get(link, stream=True)

    if save_as is None:
        save_as = get_filename(link)
    output_path = f"{ save_to }/{ save_as }"
    with open(output_path, "wb") as fd:
        for chunk in res.iter_content(chunk_size=chunk_size):
            fd.write(chunk)
    log.info(f"Downloaded export from S3. Saved at { output_path }")

    return None
