"""WP-02b — BaselineClassifier: TF-IDF + Logistic Regression (plan_module_d.md § WP-02b).

Pipeline:
  FeatureUnion[
    TfidfVectorizer(word, ngram=(1,2), sublinear_tf=True),
    TfidfVectorizer(char_wb, ngram=(2,4), sublinear_tf=True),
  ]
  → LogisticRegression(C=1.0, class_weight='balanced', max_iter=200)

Lớp này chỉ dùng scikit-learn + stdlib — KHÔNG phụ thuộc LLM hay mạng.
Chạy được offline hoàn toàn.

Ánh xạ nhãn dataset → EmailLabel (plan § WP-02a):
  "coursework"  → EmailLabel.ASSIGNMENT
  "announcement"→ EmailLabel.ANNOUNCEMENT
  "phishing"    → EmailLabel.PHISHING
  "other"       → EmailLabel.OTHER
"""
from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any

from core.contracts import EmailLabel

logger = logging.getLogger(__name__)

# Ánh xạ nhãn chuỗi trong dataset → EmailLabel
_LABEL_MAP: dict[str, EmailLabel] = {
    "coursework": EmailLabel.ASSIGNMENT,
    "assignment": EmailLabel.ASSIGNMENT,
    "announcement": EmailLabel.ANNOUNCEMENT,
    "schedule": EmailLabel.SCHEDULE,
    "phishing": EmailLabel.PHISHING,
    "spam": EmailLabel.SPAM,
    "other": EmailLabel.OTHER,
}

# Ánh xạ ngược EmailLabel → chuỗi nội bộ để sklearn dùng
_LABEL_TO_STR: dict[EmailLabel, str] = {v: k for k, v in _LABEL_MAP.items()}

# Đảm bảo ánh xạ ngược nhất quán (ưu tiên key đầu tiên)
_LABEL_TO_STR = {
    EmailLabel.ASSIGNMENT: "coursework",
    EmailLabel.ANNOUNCEMENT: "announcement",
    EmailLabel.SCHEDULE: "schedule",
    EmailLabel.PHISHING: "phishing",
    EmailLabel.SPAM: "spam",
    EmailLabel.OTHER: "other",
}


def _load_jsonl(path: str | Path) -> tuple[list[str], list[str]]:
    """Đọc JSONL, trả (texts, labels_str).

    Hỗ trợ 2 format field:
    - {"text": "...", "label": "..."}
    - {"subject": "...", "body": "...", "label": "..."}
    """
    texts: list[str] = []
    labels: list[str] = []
    skipped = 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            label_raw = obj.get("label", "").strip().lower()
            if label_raw not in _LABEL_MAP:
                logger.warning("Nhãn không hợp lệ '%s' — bỏ qua dòng", label_raw)
                skipped += 1
                continue
            if "text" in obj:
                text = obj["text"].strip()
            else:
                text = (obj.get("subject", "") + " " + obj.get("body", "")).strip()
            if not text:
                skipped += 1
                continue
            texts.append(text)
            labels.append(label_raw)
        except json.JSONDecodeError as exc:
            logger.warning("JSON lỗi: %s — bỏ qua", exc)
            skipped += 1
    if skipped:
        logger.info("Bỏ qua %d dòng lỗi / nhãn không hợp lệ", skipped)
    return texts, labels


class BaselineClassifier:
    """TF-IDF (word + char_wb) + Logistic Regression, chạy offline hoàn toàn.

    Sử dụng:
        clf = BaselineClassifier()
        clf.train_from_file("data/emails_labeled.jsonl")
        label, conf = clf.predict("Nộp bài tập trước 23h59 Thứ Sáu")

    Hoặc tải model đã lưu:
        clf = BaselineClassifier.load("data/models/email_classifier.pkl")
    """

    def __init__(self) -> None:
        self._pipeline: Any = None  # sklearn Pipeline — lazy import
        self._classes: list[str] = []
        self._is_trained: bool = False

    # ------------------------------------------------------------------
    # Huấn luyện
    # ------------------------------------------------------------------

    def train_from_file(self, jsonl_path: str | Path) -> "BaselineClassifier":
        """Đọc JSONL, huấn luyện pipeline, trả self để chain.

        Raises:
            FileNotFoundError: nếu jsonl_path không tồn tại.
            ValueError: nếu dataset quá ít mẫu (< 4).
        """
        texts, labels = _load_jsonl(jsonl_path)
        if len(texts) < 4:
            raise ValueError(
                f"Dataset quá ít mẫu ({len(texts)}), cần ít nhất 4 để train."
            )
        return self.train(texts, labels)

    def train(self, texts: list[str], labels: list[str]) -> "BaselineClassifier":
        """Huấn luyện từ danh sách texts và labels (chuỗi, không phải EmailLabel)."""
        # Import sklearn ở đây để không lỗi khi chưa cài (Constitution V)
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import FeatureUnion, Pipeline

        word_tfidf = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
            max_features=10_000,
        )
        char_tfidf = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 4),
            sublinear_tf=True,
            min_df=1,
            max_features=10_000,
        )
        feature_union = FeatureUnion([
            ("word", word_tfidf),
            ("char", char_tfidf),
        ])
        lr = LogisticRegression(
            C=1.0,
            class_weight="balanced",
            max_iter=200,
            random_state=42,
            solver="lbfgs",
        )
        self._pipeline = Pipeline([
            ("features", feature_union),
            ("clf", lr),
        ])
        self._pipeline.fit(texts, labels)
        self._classes = list(self._pipeline.classes_)
        self._is_trained = True
        logger.info(
            "BaselineClassifier huấn luyện xong: %d mẫu, %d nhãn: %s",
            len(texts), len(self._classes), self._classes,
        )
        return self

    # ------------------------------------------------------------------
    # Dự đoán
    # ------------------------------------------------------------------

    def predict(self, text: str) -> tuple[EmailLabel, float]:
        """Dự đoán nhãn và confidence cho một đoạn văn bản.

        Args:
            text: Văn bản email (subject + body hoặc chỉ body).

        Returns:
            Tuple (EmailLabel, confidence) với confidence ∈ [0.0, 1.0].

        Raises:
            RuntimeError: nếu chưa huấn luyện.
        """
        if not self._is_trained or self._pipeline is None:
            raise RuntimeError(
                "BaselineClassifier chưa được huấn luyện. Gọi train_from_file() trước."
            )
        text = (text or "").strip()
        if not text:
            return EmailLabel.OTHER, 0.0

        proba = self._pipeline.predict_proba([text])[0]
        idx = int(proba.argmax())
        label_str = self._classes[idx]
        confidence = float(proba[idx])
        email_label = _LABEL_MAP.get(label_str, EmailLabel.OTHER)
        return email_label, confidence

    def predict_batch(self, texts: list[str]) -> list[tuple[EmailLabel, float]]:
        """Dự đoán cho nhiều văn bản cùng lúc (nhanh hơn gọi predict() lần lượt)."""
        if not self._is_trained or self._pipeline is None:
            raise RuntimeError("BaselineClassifier chưa được huấn luyện.")
        if not texts:
            return []
        # Tách text rỗng ra riêng để xử lý đúng
        results: list[tuple[EmailLabel, float]] = []
        non_empty_indices: list[int] = []
        non_empty_texts: list[str] = []
        for i, t in enumerate(texts):
            stripped = (t or "").strip()
            if stripped:
                non_empty_indices.append(i)
                non_empty_texts.append(stripped)

        # Predict batch cho text không rỗng
        batch_results: dict[int, tuple[EmailLabel, float]] = {}
        if non_empty_texts:
            probas = self._pipeline.predict_proba(non_empty_texts)
            for i, (idx, proba) in enumerate(zip(non_empty_indices, probas)):
                label_str = self._classes[int(proba.argmax())]
                confidence = float(proba.max())
                batch_results[idx] = (_LABEL_MAP.get(label_str, EmailLabel.OTHER), confidence)

        # Ghép lại theo thứ tự gốc
        for i in range(len(texts)):
            results.append(batch_results.get(i, (EmailLabel.OTHER, 0.0)))
        return results

    # ------------------------------------------------------------------
    # Lưu / tải
    # ------------------------------------------------------------------

    def save(self, path: str | Path) -> None:
        """Lưu pipeline đã huấn luyện bằng pickle/joblib."""
        if not self._is_trained:
            raise RuntimeError("Chưa huấn luyện, không có gì để lưu.")
        try:
            import joblib
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            joblib.dump({"pipeline": self._pipeline, "classes": self._classes}, path)
        except ImportError:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                pickle.dump({"pipeline": self._pipeline, "classes": self._classes}, f)
        logger.info("Đã lưu model → %s", path)

    @classmethod
    def load(cls, path: str | Path) -> "BaselineClassifier":
        """Tải model đã lưu. Raise FileNotFoundError nếu không tìm thấy."""
        try:
            import joblib
            data = joblib.load(path)
        except ImportError:
            with open(path, "rb") as f:
                data = pickle.load(f)
        obj = cls()
        obj._pipeline = data["pipeline"]
        obj._classes = data["classes"]
        obj._is_trained = True
        logger.info("Đã tải model từ %s", path)
        return obj

    @classmethod
    def load_or_train(
        cls,
        model_path: str | Path,
        jsonl_path: str | Path,
    ) -> "BaselineClassifier":
        """Tải model nếu có, nếu không thì train từ dataset và lưu lại."""
        model_path = Path(model_path)
        if model_path.exists():
            try:
                return cls.load(model_path)
            except Exception as exc:
                logger.warning("Tải model thất bại (%s) — train lại", exc)
        clf = cls().train_from_file(jsonl_path)
        try:
            clf.save(model_path)
        except Exception as exc:
            logger.warning("Lưu model thất bại: %s", exc)
        return clf

    # ------------------------------------------------------------------
    # Tiện ích
    # ------------------------------------------------------------------

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    @property
    def label_classes(self) -> list[str]:
        """Danh sách nhãn nội bộ mà model biết."""
        return list(self._classes)
