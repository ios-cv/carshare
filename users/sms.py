import requests

from django.conf import settings


def send_sms_verification_code(code, number):
    payload = {
        "sender": "GoEV",
        "destination": number,
        "content": "Your Isles of Scilly GoEV verification code is {}".format(code),
        "tag": "validation",
    }

    print(payload)

    key = settings.SMS_API_KEY
    if key is None:
        print("Not sending an SMS as no SMS API key present.")
        return

    r = requests.post(
        url="https://api.thesmsworks.co.uk/v1/message/send",
        json=payload,
        headers={
            "Authorization": key,
        },
    )
