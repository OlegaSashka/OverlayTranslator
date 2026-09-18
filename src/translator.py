import os
import time
from functools import lru_cache
from pathlib import Path
import ctranslate2
import sentencepiece as spm

# Лимит на 2 потока Zen 2 во избежание просадок кадров в играх
os.environ["OMP_THREAD_LIMIT"] = "2"


class OfflineTranslator:

    def __init__(self, model_dir: Path | str = "models/opus-mt-en-ru"):
        self.model_dir = Path(model_dir)
        self.translator = None
        self.sp = None
        self._is_ready = False
        self._load_engine()

    def _resolve_paths(self) -> tuple[Path, Path]:
        # 1. Каталог весов CTranslate2
        if (self.model_dir / "model" / "model.bin").exists():
            model_path = self.model_dir / "model"
        elif (self.model_dir / "model.bin").exists():
            model_path = self.model_dir
        else:
            raise FileNotFoundError(f"model.bin не найден в {self.model_dir}")

        # 2. Файл токенизатора SentencePiece
        candidates = [
            self.model_dir / "sentencepiece.model",
            self.model_dir / "source.spm",
        ]
        spm_path = next((p for p in candidates if p.exists()), None)
        if not spm_path:
            raise FileNotFoundError(
                f"Токенизатор .model/.spm не найден в {self.model_dir}"
            )

        return model_path, spm_path

    def _load_engine(self):
        try:
            model_path, spm_path = self._resolve_paths()
            self.sp = spm.SentencePieceProcessor()
            self.sp.load(str(spm_path))

            self.translator = ctranslate2.Translator(
                str(model_path),
                device="cpu",
                compute_type="int8",
                intra_threads=2,
                inter_threads=1,
            )
            # Прогревочный холостой вызов графа вычислений
            _ = self.translator.translate_batch([self.sp.encode("", out_type=str)])
            self._is_ready = True
        except Exception as e:
            self._is_ready = False
            self.last_error = str(e)

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    @lru_cache(maxsize=1024)
    def _translate_cached(self, text: str) -> str:
        tokens = self.sp.encode(text, out_type=str)
        results = self.translator.translate_batch([tokens])
        return self.sp.decode(results[0].hypotheses[0])

    def translate(self, text: str) -> str:
        if not self._is_ready or not text.strip():
            return text

        # Обработка многострочного форматирования (сохраняем пункты списков и переносы)
        lines = text.split("\n")
        translated_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                translated_lines.append("")
                continue
            translated_lines.append(self._translate_cached(stripped))

        return "\n".join(translated_lines)
