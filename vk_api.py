from json import dumps, loads

from requests import Session, session


def get_api(token=""):
    if "vk_api" not in globals():
        globals()["vk_api"] = Api(token)
    return globals()["vk_api"]


class Api:
    token = ""
    v = 5.131
    session: Session

    def __init__(self, token: str, v: float = 5.131):
        self.token = token
        self.v = v
        self.session = session()

    #
    def method(self, method: str, **args) -> dict:
        """Send request to vk api method with given args and return answer or None if error"""
        try:
            resp = self.session.get(
                "https://api.vk.com/method/" + method,
                params={"v": self.v, "access_token": self.token, **args},
            ).text
            resp = loads(resp)
            if "error" in resp:
                raise Exception(dumps(resp["error"]))
        except Exception as e:
            print("Ошибка:\n" + str(e))
            return {}
        return resp["response"]
