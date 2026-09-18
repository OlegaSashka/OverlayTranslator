import os
import time
import cv2
import mss
import numpy as np
import pytesseract
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
from src.config import load_config
from src.translator import OfflineTranslator

# Ограничиваем аппетиты OpenMP, сохраняя ядра APU для игры
os.environ["OMP_THREAD_LIMIT"] = "2"

def clean_ocr_text(raw_text: str) -> str:
    if not raw_text.strip():
        return ""

    paragraphs = raw_text.split("\n\n")
    result_blocks = []

    for p in paragraphs:
        lines = [line.strip() for line in p.splitlines() if line.strip()]
        if not lines:
            continue

        current_block = []
        for line in lines:
            # Детекция начала нового пункта списка или блока после заголовка
            is_list_item = line.startswith(("-", "•", "*", "—", "–")) or (
                len(line) > 2 and line[0].isdigit() and line[1] in (".", ")")
            )
            prev_is_header = current_block and current_block[-1].endswith(":")

            if (is_list_item or prev_is_header) and current_block:
                result_blocks.append(" ".join(current_block))
                current_block = [line]
            else:
                current_block.append(line)

        if current_block:
            result_blocks.append(" ".join(current_block))

    return "\n".join(result_blocks)

def is_valid_english_text(text: str, min_latin_ratio: float = 0.75) -> bool:
    """
    Проверяет, является ли текст преимущественно английским.
    Отсекает галлюцинации Tesseract при чтении кириллицы через английский словарь.
    """
    alpha_chars = [c for c in text if c.isalpha()]
    if not alpha_chars:
        return False

    # Считаем строго базовую латиницу (ASCII)
    latin_chars = [c for c in alpha_chars if "a" <= c.lower() <= "z"]
    ratio = len(latin_chars) / len(alpha_chars)

    # Дополнительный эвристический фильтр на «цифробуквы» (3 вместо З, 0 вместо О)
    words = text.split()
    digit_word_leaks = sum(
        1 for w in words if any(c.isdigit() for c in w) and any(c.isalpha() for c in w)
    )
    has_heavy_leaks = (digit_word_leaks / len(words)) > 0.3 if words else False

    return ratio >= min_latin_ratio and not has_heavy_leaks

class OcrWorker(QThread):
    text_captured = pyqtSignal(str)
    status_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._paused = False
        self._mutex = QMutex()

        self._busy = False
        self._latest_frame = None
        self.fast_interval = 0.15

        self.diff_threshold = 2.5
        self.last_text = ""
        self.tess_config = r"--oem 1 --psm 6"

        self.translator = OfflineTranslator()

    def stop(self):
        with QMutexLocker(self._mutex):
            self._running = False
        self.wait(1500)

    def set_paused(self, paused: bool):
        with QMutexLocker(self._mutex):
            self._paused = paused

    def run(self):
        prev_gray = None

        with mss.MSS() as sct:
            while True:
                with QMutexLocker(self._mutex):
                    if not self._running:
                        break
                    is_paused = self._paused

                if is_paused:
                    time.sleep(0.2)
                    continue

                cfg = load_config()
                rect = cfg.get("capture_rect", {"x": 240, "y": 550, "w": 800, "h": 120})
                src_lang = cfg.get("source_lang", "eng")

                region = {
                    "left": int(rect["x"]),
                    "top": int(rect["y"]),
                    "width": int(rect["w"]),
                    "height": int(rect["h"]),
                }

                # 1. Сверхбыстрый захват кадра
                sct_img = sct.grab(region)
                raw_bgra = np.frombuffer(sct_img.raw, dtype=np.uint8).reshape(
                    (sct_img.height, sct_img.width, 4)
                )
                gray = cv2.cvtColor(raw_bgra, cv2.COLOR_BGRA2GRAY)

                # 2. Проверка изменений кадра (0.3 ms)
                has_changed = True
                if prev_gray is not None and prev_gray.shape == gray.shape:
                    diff = cv2.absdiff(gray, prev_gray)
                    if float(np.mean(diff)) < self.diff_threshold:
                        has_changed = False

                if has_changed:
                    prev_gray = gray.copy()

                    # 3. Предобработка кадра
                    prepared = cv2.bitwise_not(gray) if np.mean(gray) < 127 else gray
                    processed = cv2.convertScaleAbs(prepared, alpha=1.6, beta=-15)

                    # 4. Выполняем OCR только по актуальному изменению
                    try:
                        raw_text = pytesseract.image_to_string(
                            processed, lang=src_lang, config=self.tess_config
                        )
                        # cleaned_text = " ".join(raw_text.split())
                        cleaned_text = clean_ocr_text(raw_text)
                        if cleaned_text and cleaned_text != self.last_text:
                            self.last_text = cleaned_text
                            # Если выбран исходный английский язык и модель готова — переводим
                            if (
                                src_lang == "eng"
                                and self.translator
                                and self.translator.is_ready
                            ):
                                if is_valid_english_text(cleaned_text):
                                    display_text = self.translator.translate(
                                        cleaned_text
                                    )
                                else:
                                    # Отсекаем мусорный OCR, не дергая переводчик
                                    display_text = f"[OCR: не английский текст]\n{cleaned_text}"
                            else:
                                display_text = cleaned_text

                            self.text_captured.emit(display_text)
                    except Exception as e:
                        self.status_changed.emit(f"OCR Error: {e}")

                time.sleep(self.fast_interval)
