import requests

FCM_SERVER_KEY = "YOUR_FCM_KEY"

def send_push(token: str, title: str, body: str):
    requests.post(
        "https://fcm.googleapis.com/fcm/send",
        headers={
            "Authorization": f"key={FCM_SERVER_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "to": token,
            "notification": {"title": title, "body": body}
        }
    )
