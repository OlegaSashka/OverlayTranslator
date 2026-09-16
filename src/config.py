import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "capture_rect": {"x": 240, "y": 550, "w": 800, "h": 120},
    "overlay_rect": {"x": 240, "y": 380, "w": 800, "h": 140},
    "show_overlay": True,
    "show_capture_border": False,
    "styles": {
        "overlay_bg_color": "#0F1219",
        "overlay_opacity": 85,
        "border_color": "#00FF88",
        "text_color": "#FFFFFF",
        "font_size": 15,
        "custom_border_color": "#00FF88",
        "custom_overlay_bg_color": "#0F1219",
        "custom_text_color": "#FFFFFF",
        "border_color_is_custom": False,
        "overlay_bg_color_is_custom": False,
        "text_color_is_custom": False
    },
    "source_lang": "eng",
    "target_lang": "ru",
    "interval_sec": 1.2
}

def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
            if "styles" not in data:
                data["styles"] = DEFAULT_CONFIG["styles"].copy()
            else:
                for sk, sv in DEFAULT_CONFIG["styles"].items():
                    if sk not in data["styles"]:
                        data["styles"][sk] = sv
            return data
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
