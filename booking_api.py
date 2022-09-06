import requests


class BookingApi(object):
    def __init__(self, url, token):
        self.url = url
        self.headers = {"X-RapidAPI-Key": token,
                        "X-RapidAPI-Host": self.url}

    def get(self, name, params=None):
        url = f"https://{self.url}/v1/{name}"
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
