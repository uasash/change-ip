"""
Change IP — Kivy macOS app.
Shows the current public IP and lets you trigger a change via a configurable URL.
"""

import os
import subprocess
import threading
import time
import urllib.request

import httpx
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

IP_CHECK_URL = os.environ.get("IP_CHECK_URL", "https://ifconfig.me/ip")
CHANGE_IP_URL = os.environ.get("CHANGE_IP_URL", "")


def get_system_proxy() -> str | None:
    """Read the macOS system proxy settings.

    Tries urllib.request.getproxies() first, then falls back to
    ``scutil --proxy`` which reads directly from macOS system config.
    """
    # Try standard Python approach
    proxies = urllib.request.getproxies()
    proxy = proxies.get("https") or proxies.get("http")
    if proxy:
        return proxy

    # Fallback: read from macOS system configuration via scutil
    try:
        result = subprocess.run(
            ["scutil", "--proxy"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = result.stdout.splitlines()
        settings = {}
        for line in lines:
            if ": " in line:
                key, _, value = line.partition(": ")
                settings[key.strip()] = value.strip()

        if settings.get("HTTPSEnable") == "1":
            host = settings.get("HTTPSProxy", "")
            port = settings.get("HTTPSPort", "")
            if host:
                return f"http://{host}:{port}" if port else f"http://{host}"

        if settings.get("HTTPEnable") == "1":
            host = settings.get("HTTPProxy", "")
            port = settings.get("HTTPPort", "")
            if host:
                return f"http://{host}:{port}" if port else f"http://{host}"
    except Exception:
        pass

    return None


def make_client(**kwargs) -> httpx.Client:
    """Create an httpx client that respects the system proxy."""
    proxy = get_system_proxy()
    if proxy:
        kwargs["proxy"] = proxy
    return httpx.Client(**kwargs)


# ---------------------------------------------------------------------------
# KV layout — separate from Python to avoid text rendering issues
# ---------------------------------------------------------------------------

KV = """
#:set BG (0.08, 0.08, 0.10, 1)
#:set CARD (0.14, 0.14, 0.18, 1)
#:set WHITE (1, 1, 1, 1)
#:set GRAY (0.55, 0.55, 0.60, 1)
#:set BLUE (0.30, 0.55, 1.0, 1)
#:set GREEN (0.20, 0.80, 0.35, 1)
#:set RED (0.95, 0.30, 0.30, 1)
#:set YELLOW (0.95, 0.70, 0.20, 1)
#:set DIM (0.35, 0.35, 0.40, 1)
#:set DARK_BTN (0.18, 0.18, 0.24, 1)

<ChangeIPScreen@BoxLayout>:
    orientation: 'vertical'
    padding: 40
    spacing: 0

    canvas.before:
        Color:
            rgba: BG
        Rectangle:
            pos: self.pos
            size: self.size

    # ── Title ──
    Label:
        text: 'Change IP'
        font_size: 40
        bold: True
        color: WHITE
        size_hint_y: None
        height: 56
        halign: 'left'
        valign: 'middle'
        text_size: self.width, None

    Label:
        text: 'Your public IP address'
        font_size: 18
        color: GRAY
        size_hint_y: None
        height: 28
        halign: 'left'
        valign: 'middle'
        text_size: self.width, None

    Widget:
        size_hint_y: None
        height: 24

    # ── IP Card ──
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: 180
        padding: [24, 16, 24, 16]
        spacing: 4

        canvas.before:
            Color:
                rgba: CARD
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [16]

        Label:
            text: 'CURRENT IP'
            font_size: 14
            bold: True
            color: GRAY
            size_hint_y: None
            height: 22
            halign: 'left'
            valign: 'middle'
            text_size: self.width, None

        Label:
            id: ip_label
            text: root.ip_address
            font_size: 52
            bold: True
            color: root.ip_color
            size_hint_y: None
            height: 80

        Label:
            id: status_label
            text: root.status_text
            font_size: 22
            color: root.status_color
            size_hint_y: None
            height: 34
            halign: 'left'
            valign: 'middle'
            text_size: self.width, None

    Widget:
        size_hint_y: None
        height: 20

    # ── Buttons ──
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: 140
        padding: [12, 12, 12, 12]
        spacing: 12

        canvas.before:
            Color:
                rgba: CARD
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [16]

        Button:
            id: change_btn
            text: 'CHANGE IP'
            font_size: 20
            bold: True
            background_normal: ''
            background_color: BLUE
            color: WHITE
            size_hint_y: None
            height: 52
            on_release: root.change_ip()

        Button:
            text: 'REFRESH'
            font_size: 20
            bold: True
            background_normal: ''
            background_color: DARK_BTN
            color: WHITE
            size_hint_y: None
            height: 52
            on_release: root.refresh_ip()

    Widget:

    # ── Footer ──
    Label:
        text: 'Source: ifconfig.me'
        font_size: 12
        color: DIM
        size_hint_y: None
        height: 20
"""


class ChangeIPScreen(BoxLayout):
    ip_address = StringProperty("—")
    ip_color = ListProperty([0.30, 0.55, 1.0, 1])  # default BLUE
    status_text = StringProperty("")
    status_color = ListProperty([0.35, 0.35, 0.40, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._old_ip = None
        Clock.schedule_once(lambda dt: self.refresh_ip(), 0.5)

    def refresh_ip(self):
        self.status_text = "Fetching…"
        self.status_color = [0.55, 0.55, 0.60, 1]
        self.ip_address = "…"
        threading.Thread(target=self._fetch_ip, daemon=True).start()

    def _fetch_ip(self):
        try:
            with make_client(timeout=10, follow_redirects=True) as client:
                resp = client.get(IP_CHECK_URL)
                resp.raise_for_status()
                ip = resp.text.strip()
        except Exception as exc:
            ip = "—"
            msg = f"Error: {exc}"
            Clock.schedule_once(
                lambda dt, m=msg: (
                    setattr(self, "ip_address", ip),
                    setattr(self, "status_text", m),
                    setattr(self, "status_color", [0.95, 0.30, 0.30, 1]),
                ),
                0,
            )
            return
        Clock.schedule_once(lambda dt, v=ip: self._on_ip_fetched(v), 0)

    def _on_ip_fetched(self, ip):
        self.ip_address = ip
        if self._old_ip is None:
            self.status_text = "Ready"
            self.status_color = [0.35, 0.35, 0.40, 1]
            self.ip_color = [0.30, 0.55, 1.0, 1]  # BLUE
        elif ip == self._old_ip:
            self.status_text = "IP was not changed"
            self.status_color = [0.95, 0.30, 0.30, 1]  # RED
            self.ip_color = [0.95, 0.30, 0.30, 1]  # RED
        else:
            self.status_text = "IP changed successfully"
            self.status_color = [0.20, 0.80, 0.35, 1]  # GREEN
            self.ip_color = [0.20, 0.80, 0.35, 1]  # GREEN
        self._old_ip = ip

    def change_ip(self):
        if not CHANGE_IP_URL:
            self.status_text = "No CHANGE_IP_URL configured"
            self.status_color = [0.95, 0.70, 0.20, 1]
            return
        self.ids.change_btn.disabled = True
        self.ids.change_btn.text = "CHANGING…"
        self.status_text = "Requesting change…"
        self.status_color = [0.55, 0.55, 0.60, 1]
        threading.Thread(target=self._do_change_ip, daemon=True).start()

    def _do_change_ip(self):
        try:
            with make_client(timeout=30, follow_redirects=True) as client:
                resp = client.get(CHANGE_IP_URL)
                resp.raise_for_status()
        except Exception as exc:
            msg = f"Change failed: {exc}"
            Clock.schedule_once(
                lambda dt, m=msg: (
                    setattr(self, "status_text", m),
                    setattr(self, "status_color", [0.95, 0.30, 0.30, 1]),
                    self._re_enable_btn(),
                ),
                0,
            )
            return
        time.sleep(2)
        Clock.schedule_once(lambda dt: (self._re_enable_btn(), self.refresh_ip()), 0)

    def _re_enable_btn(self):
        self.ids.change_btn.disabled = False
        self.ids.change_btn.text = "CHANGE IP"


class ChangeIPApp(App):
    def build(self):
        Window.size = (480, 640)
        Window.clearcolor = (0.08, 0.08, 0.10, 1)
        from kivy.lang import Builder

        Builder.load_string(KV)
        return ChangeIPScreen()


if __name__ == "__main__":
    ChangeIPApp().run()
