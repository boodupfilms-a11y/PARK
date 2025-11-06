# -*- coding: utf-8 -*-
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import StringProperty, DictProperty
from kivymd.app import MDApp
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
import json, os, time, webbrowser, datetime
from plyer import gps, camera

KV = r"""
<RoundActionButton@MDFillRoundFlatIconButton>:
    icon_color: 1,1,1,1
    text_color: 1,1,1,1
    md_bg_color: 0.027, 0.941, 0.773, 1
    font_style: "Button"
    size_hint: None, None
    height: dp(56)
    width: min(root.width*0.9, dp(320))
    radius: [dp(28), dp(28), dp(28), dp(28)]
    pos_hint: {"center_x": 0.5}

MDScreen:
    md_bg_color: 0,0,0,1
    BoxLayout:
        orientation: "vertical"
        padding: dp(20), dp(20)
        spacing: dp(16)
        MDLabel:
            text: "BOODUP PARK"
            halign: "center"
            theme_text_color: "Custom"
            text_color: 1,1,1,1
            font_style: "H5"
            size_hint_y: None
            height: self.texture_size[1]
        MDLabel:
            text: "שמור חניה, מצא את הרכב, וזכור לבדוק את הילד \u2764"
            halign: "center"
            theme_text_color: "Custom"
            text_color: 1,1,1,0.7
            size_hint_y: None
            height: self.texture_size[1]
        Widget:
            size_hint_y: None
            height: dp(8)
        RoundActionButton:
            icon: "car"
            text: "   \u200f\u200f\u200f\u200f\u200f\u200f\u200f\u200f   שמירת חניה   "
            on_release: app.on_save_parking()
        Widget:
            size_hint_y: None
            height: dp(10)
        RoundActionButton:
            icon: "map-marker"
            text: "   \u200f\u200f\u200f\u200f\u200f\u200f\u200f\u200f   מציאת הרכב   "
            md_bg_color: 1, 0.839, 0.420, 1
            on_release: app.on_find_my_car()
        Widget:
            size_hint_y: None
            height: dp(10)
        RoundActionButton:
            icon: "heart"
            text: "   \u200f\u200f\u200f\u200f\u200f\u200f\u200f\u200f   בדיקת ילד   "
            md_bg_color: 0.027, 0.941, 0.773, 1
            on_release: app.on_child_check()
        Widget:
        MDLabel:
            text: app.status_text
            halign: "right"
            theme_text_color: "Custom"
            text_color: 1,1,1,0.6
            size_hint_y: None
            height: self.texture_size[1]
"""

class BoodupParkApp(MDApp):
    status_text = StringProperty("מוכן")
    data_path = StringProperty("")
    last_location = DictProperty({})
    dialog = None

    def build(self):
        self.title = "BOODUP PARK"
        self.theme_cls.material_style = "M3"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style = "Dark"
        self.data_path = self.user_data_dir
        os.makedirs(self.data_path, exist_ok=True)
        return Builder.load_string(KV)

    def on_save_parking(self):
        self.status("מבקש מיקום GPS...")
        try:
            gps.configure(on_location=self._on_gps_location, on_status=self._on_gps_status)
            gps.start(minTime=1000, minDistance=1)
            Clock.schedule_once(lambda *_: self._gps_timeout(), 8)
        except Exception as e:
            self.status("GPS לא זמין, פותח צילום בלבד")
            self._save_with_mock_location()

    def _on_gps_status(self, stype, status):
        pass

    def _on_gps_location(self, **kwargs):
        try:
            gps.stop()
        except Exception:
            pass
        lat = kwargs.get("lat") or kwargs.get("latitude")
        lon = kwargs.get("lon") or kwargs.get("longitude")
        if lat and lon:
            self.last_location = {"lat": float(lat), "lon": float(lon)}
            self.status(f"מיקום התקבל: {lat:.5f}, {lon:.5f}")
            Clock.schedule_once(lambda *_: self._take_parking_photo(), 0.4)
        else:
            self.status("לא התקבל מיקום – שמירה ללא מיקום")
            self._save_record(None, None, photo_path=None)

    def _gps_timeout(self):
        if not self.last_location:
            self.status("לא התקבל GPS בזמן, ממשיך לצילום...")
            self._take_parking_photo()

    def _take_parking_photo(self):
        ts = int(time.time())
        photo_name = f"parking_{ts}.jpg"
        full_path = os.path.join(self.data_path, photo_name)
        try:
            camera.take_picture(filename=full_path, on_complete=lambda p: self._after_photo(p, ts))
        except Exception as e:
            self.status("מצלמה לא זמינה – שומר ללא צילום")
            self._save_record(self.last_location.get("lat"), self.last_location.get("lon"), photo_path=None)

    def _after_photo(self, path, ts):
        lat = self.last_location.get("lat")
        lon = self.last_location.get("lon")
        if path and os.path.exists(path):
            self._save_record(lat, lon, photo_path=path)
        else:
            self._save_record(lat, lon, photo_path=None)

    def _save_with_mock_location(self):
        self.last_location = {"lat": None, "lon": None}
        self._take_parking_photo()

    def _save_record(self, lat, lon, photo_path):
        record = {
            "timestamp": int(time.time()),
            "when": datetime.datetime.now().isoformat(),
            "lat": lat,
            "lon": lon,
            "photo": photo_path,
            "note": ""
        }
        json_path = os.path.join(self.data_path, "parking_records.json")
        records = []
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    records = json.load(f)
            except Exception:
                records = []
        records.insert(0, record)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        self.status("המיקום נשמר בהצלחה \u2714")
        Snackbar(text="✅ המיקום נשמר!").open()
        Clock.schedule_once(lambda *_: self._show_child_dialog(), 0.4)

    def on_find_my_car(self):
        json_path = os.path.join(self.data_path, "parking_records.json")
        if not os.path.exists(json_path):
            Snackbar(text="לא נמצאה חניה שמורה.").open()
            return
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            Snackbar(text="שגיאה בקריאת הנתונים").open()
            return
        if not records:
            Snackbar(text="אין רשומות חניה").open()
            return
        last = records[0]
        lat, lon = last.get("lat"), last.get("lon")
        if lat is not None and lon is not None:
            url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            webbrowser.open(url)
            self.status("פותח את מיקום החניה במפות")
        else:
            Snackbar(text="אין מיקום שמור.").open()

    def on_child_check(self):
        self._show_child_dialog()

    def _show_child_dialog(self):
        if hasattr(self, "dialog") and self.dialog:
            self.dialog.dismiss()
        self.dialog = MDDialog(
            title="רגע לפני שיוצאים",
            text="בדקת שהילד יצא מהרכב?",
            buttons=[
                MDFlatButton(text="תזכיר בעוד דקה", on_release=lambda *_: self._remind_child(60)),
                MDFlatButton(text="בדקתי ✅", on_release=lambda *_: self._child_ok())
            ],
        )
        self.dialog.open()

    def _child_ok(self, *a):
        if self.dialog:
            self.dialog.dismiss()
        Snackbar(text="כל הכבוד! 👏").open()

    def _remind_child(self, delay_sec=60):
        if self.dialog:
            self.dialog.dismiss()
        Snackbar(text=f"תזכורת תופיע בעוד {delay_sec} שניות").open()
        Clock.schedule_once(lambda *_: Snackbar(text="תזכורת: בדוק את הילד ברכב ❤️").open(), delay_sec)

    def status(self, txt):
        self.status_text = txt

if __name__ == "__main__":
    BoodupParkApp().run()
