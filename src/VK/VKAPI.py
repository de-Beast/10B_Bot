from json import dumps, loads

from requests import Session, session


class VKAPI:
    token = None
    v = 5.131
    user_agent = "KateMobileAndroid/56 lite-460 (Android 4.4.2; SDK 19; x86; unknown Android SDK built for x86; en)"

    def __init__(self) -> None:
        if self.token is None:
            from config import get_config
            
            self.token = get_config().get("VKADMIN_TOKEN")
        
        self.session: Session = session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def method(self, method: str, /, **kwargs) -> dict:
        """Send request to vk api method with given args and return answer or None if error"""

        try:
            resp = self.session.get(
                f"https://api.vk.com/method/{method}",
                params={"v": self.v, "access_token": self.token, **kwargs},
            ).text
            dict_resp = loads(resp)
            if "error" in dict_resp:
                raise Exception(dumps(dict_resp["error"]))
        except Exception as e:
            print("Ошибка:\n" + str(e))
            return {}
        return dict_resp["response"]
