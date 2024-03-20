from json import dumps, loads

from requests import Session, session


class Api:
    token = ""
    v = 5.131
    user_agent = "KateMobileAndroid/56 lite-460 (Android 4.4.2; SDK 19; x86; unknown Android SDK built for x86; en)"

    def __init__(self, token: str, v: float = 5.131):
        self.token = token
        self.v = v
        self.session: Session = session()

        self.session.headers.update({"User-Agent": self.user_agent})

    def method(self, method: str, **args) -> dict:
        """Send request to vk api method with given args and return answer or None if error"""

        try:
            resp = self.session.get(
                f"https://api.vk.com/method/{method}",
                params={"v": self.v, "access_token": self.token, **args},
            ).text
            dict_resp = loads(resp)
            if "error" in dict_resp:
                raise Exception(dumps(dict_resp["error"]))
        except Exception as e:
            print("Ошибка:\n" + str(e))
            return {}
        return dict_resp["response"]


def get_api(token="") -> Api:
    if "vk_api" not in globals():
        globals()["vk_api"] = Api(token)
    return globals()["vk_api"]
