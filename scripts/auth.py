# adapted from
# https://github.com/zedeus/nitter/issues/983#issuecomment-1914616663
import requests
import base64
import json
import sys
import os
import logging
from typing import Optional
import requests
from bs4 import BeautifulSoup

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG if os.getenv("DEBUG") == "1" else logging.INFO)

TW_CONSUMER_KEY = '3nVuSoBZnx6U4vzUxf5w'
TW_CONSUMER_SECRET = 'Bcs59EFbbsdF6Sl9Ng71smgStWEGwXXKSjYvPVt7qys'
TW_ANDROID_BASIC_TOKEN = 'Basic {token}'.format(token=base64.b64encode(
    (TW_CONSUMER_KEY + ":" + TW_CONSUMER_SECRET).encode()
).decode())
logging.debug("TW_ANDROID_BASIC_TOKEN=" + TW_ANDROID_BASIC_TOKEN)


def auth(username: str, password: str, email:Optional[str], mfa_code: Optional[str]) -> Optional[dict]:
    logging.debug("start auth")

    bearer_token_req = requests.post("https://api.twitter.com/oauth2/token",
                                     headers={
                                         'Authorization': TW_ANDROID_BASIC_TOKEN,
                                         "Content-Type": "application/x-www-form-urlencoded",
                                     },
                                     data='grant_type=client_credentials'
                                     ).json()
    bearer_token = ' '.join(str(x) for x in bearer_token_req.values())
    logging.debug("bearer_token=" + bearer_token)

    guest_token = requests.post("https://api.twitter.com/1.1/guest/activate.json", headers={
        'Authorization': bearer_token,
    }).json()['guest_token']
    logging.debug("guest_token=" + guest_token)

    twitter_header = {
        'Authorization': bearer_token,
        "Content-Type": "application/json",
        "User-Agent":
            "Mozilla/5.0 (Linux; Android 11; S19 Max Pro Build/RP1A.201005.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/128.0.6613.146 Mobile Safari/537.36 TwitterAndroid",
        "X-Twitter-API-Version": '5',
        "X-Twitter-Client": "TwitterAndroid",
        "X-Twitter-Client-Version": "9.95.0-release.0",
        "OS-Version": "28",
        "System-User-Agent":
            "Dalvik/2.1.0 (Linux; U; Android 9; ONEPLUS A3010 Build/PKQ1.181203.001)",
        "X-Twitter-Active-User": "yes",
        "X-Guest-Token": guest_token,
    }

    session = requests.Session()

    task1 = session.post('https://api.twitter.com/1.1/onboarding/task.json',
                         params={
                             'flow_name': 'login',
                             'api_version': '1',
                             'known_device_token': '',
                             'sim_country_code': 'us'
                         },
                         json={
                             "flow_token": None,
                             "input_flow_data": {
                                 "country_code": None,
                                 "flow_context": {
                                     "referrer_context": {
                                         "referral_details": "utm_source=google-play&utm_medium=organic",
                                         "referrer_url": ""
                                     },
                                     "start_location": {
                                         "location": "deeplink"
                                     }
                                 },
                                 "requested_variant": None,
                                 "target_user_id": 0
                             }
                         },
                         headers=twitter_header
                         )
    logging.info(f"task1: {task1.json()}")

    session.headers['att'] = task1.headers.get('att')
    task2 = session.post('https://api.twitter.com/1.1/onboarding/task.json',
                         json={
                             "flow_token": task1.json().get('flow_token'),
                             "subtask_inputs": [{
                                 "enter_text": {
                                     "suggestion_id": None,
                                     "text": username,
                                     "link": "next_link"
                                 },
                                 "subtask_id": "LoginEnterUserIdentifier"
                             }
                             ]
                         },
                         headers=twitter_header
                         )
    logging.info(f"task2: {task2.json()}")
    flow_token = task2.json().get('flow_token')
    for t2_subtask in task2.json().get('subtasks', []):
        if t2_subtask['subtask_id'] == 'LoginEnterAlternateIdentifierSubtask':
            task2_1 = session.post('https://api.twitter.com/1.1/onboarding/task.json',
                         json={
                             "flow_token": task2.json().get('flow_token'),
                             "subtask_inputs": [{
                                 "enter_text": {
                                     "text": email,
                                     "link": "next_link"
                                 },
                                 "subtask_id": "LoginEnterAlternateIdentifierSubtask"
                             }
                             ]
                         },
                         headers=twitter_header
                         )
            flow_token = task2_1.json().get('flow_token')
            logging.info(f"task2_1: {task2_1.json()}")

            break

    task3 = session.post('https://api.twitter.com/1.1/onboarding/task.json',
                         json={
                             "flow_token": flow_token,
                             "subtask_inputs": [{
                                 "enter_password": {
                                     "password": password,
                                     "link": "next_link"
                                 },
                                 "subtask_id": "LoginEnterPassword"
                             }
                             ],
                         },
                         headers=twitter_header
                         )
    logging.info(f"task3: {task3.json()}")

    task5 = session.post(
        "https://api.twitter.com/1.1/onboarding/task.json",
        json={
            "flow_token": task3.json().get("flow_token"),
            "subtask_inputs": [
                {
                    "enter_text": {
                        "suggestion_id": None,
                        "text": mfa_code,
                        "link": "next_link",
                    },
                    # was previously LoginAcid
                    "subtask_id": "LoginTwoFactorAuthChallenge",
                }
            ],
        },
        headers=twitter_header,
    ).json()
    logging.info(f"task5: {task5}")
    for t5_subtask in task5.get("subtasks", []):
        if "open_account" in t5_subtask:
            return t5_subtask["open_account"]

    task4 = session.post('https://api.twitter.com/1.1/onboarding/task.json',
                         json={
                             "flow_token": task3.json().get('flow_token'),
                             "subtask_inputs": [{
                                 "check_logged_in_account": {
                                     "link": "AccountDuplicationCheck_false"
                                 },
                                 "subtask_id": "AccountDuplicationCheck"
                             }
                             ]
                         },
                         headers=twitter_header
                         ).json()
    logging.info(f"task4: {task4}")

    for t4_subtask in task4.get('subtasks', []):
        if "open_account" in t4_subtask:
            return t4_subtask["open_account"]
        elif "enter_text" in t4_subtask:
            response_text = t4_subtask["enter_text"]["hint_text"]
            print(f"Requested '{response_text}'")
            task5 = session.post(
                "https://api.twitter.com/1.1/onboarding/task.json",
                json={
                    "flow_token": task4.get("flow_token"),
                    "subtask_inputs": [
                        {
                            "enter_text": {
                                "suggestion_id": None,
                                "text": mfa_code,
                                "link": "next_link",
                            },
                            # was previously LoginAcid
                            "subtask_id": "LoginTwoFactorAuthChallenge",
                        }
                    ],
                },
                headers=twitter_header,
            ).json()
            for t5_subtask in task5.get("subtasks", []):
                if "open_account" in t5_subtask:
                    return t5_subtask["open_account"]

    return None


def parse_auth_file(auth_file: str) -> bool:
    try:
        with open(auth_file, "r") as f:
            res = json.loads(f.read())
    except json.JSONDecodeError:
        logging.error(f"Auth file is not a valid json file")
        return False
    if isinstance(res, dict):
        logging.error(f"Expecting auth file to be a json list")
        return False
    if len(res) == 0:
        logging.error(f"Expecting auth file to be non-empty")
        return False
    for i, r in enumerate(res):
        if "oauth_token" not in r:
            logging.error(f"Expecting 'oauth_token' in auth item #{i}")
            return False
        if "oauth_token_secret" not in r:
            logging.error(f"Expecting 'oauth_token_secret' in auth item #{i}")
            return False
    return True


def get_2fa_code(url):
    html = get_html(url)
    soup = BeautifulSoup(html, 'html.parser')
    code = soup.find(class_='codetxt')
    if not code or not code.text:
        raise ValueError("无法找到codetxt值")
    return code.text


def get_html(url):
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Priority": "u=0, i",
        "Referer": "https://2fa.run/2fa/RKIKYKVBSTMI5IJC",
        "Sec-CH-UA": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    return response.text


if __name__ == "__main__":
    username = "DeniseReye7897"
    password = "EDtZTBvHOVN7x8c"
    email = "rogers2mmurphy@hotmail.com"
    mfa_code_url = "https://2fa.run/2fa/BDFDHML54ZVRGKJJ"
    output_file = "guest_token_" + username + ".json"

    # if len(sys.argv) != 2:
    #     print("Usage: python3 auth.py <output_file>")
    #     sys.exit(1)
    #
    # output_file = sys.argv[1]
    # if os.path.exists(output_file):
    #     print(f"Validating auth file {output_file}")
    #     if parse_auth_file(output_file):
    #         print(f"Auth file {output_file} is valid")
    #         sys.exit(0)
    #     else:
    #         print(f"Auth file {output_file} is invalid. Please remove and rerun.")
    #         sys.exit(1)
    #
    # username = os.getenv("TWITTER_USERNAME")
    # if not username:
    #     print("Please set environment variable TWITTER_USERNAME")
    #     sys.exit(1)
    # logging.info(f"username: {username}")
    # password = os.getenv("TWITTER_PASSWORD")
    # if not password:
    #     print("Please set environment variable TWITTER_PASSWORD")
    #     sys.exit(1)
    # logging.info(f"password: {password}")
    # email = os.getenv("TWITTER_EMAIL", None)
    # if not email:
    #     print("Please set environment variable TWITTER_EMAIL")
    # logging.info(f"email: {email}")
    #
    # mfa_code_url = os.getenv("MFA_CODE_URL", None)
    if mfa_code_url is not None:
        mfa_code = get_2fa_code(mfa_code_url)
    else:
        mfa_code = None
    logging.info(f"mfa_code: {mfa_code}")
    
    auth_res = auth(username, password, email, mfa_code)

    if auth_res is None:
        print(
            "Failed authentication. You might have entered the wrong username/password. Please rerun with environment variable DEBUG=1 for debugging.")
        sys.exit(1)
    with open(output_file, "w") as f:
        f.write(json.dumps([auth_res]))
    print(f"Auth file {output_file} created successfully")
