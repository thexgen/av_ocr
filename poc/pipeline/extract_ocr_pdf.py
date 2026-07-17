from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import fitz
import numpy as np

from poc.config import cfg
from poc.exceptions import OCRFailureError
from poc.pipeline.extract_text_pdf import _extract_metadata_from_text
from poc.pipeline.models import ExtractionResult
from poc.pipeline.statement_parse import ensure_rows_from_text

logger = logging.getLogger("holding_engine")

_ocr_backend: str | None = None
_ocr_engine = None


def _get_ocr():
    """
    Prefer RapidOCR (stable on Windows). Fall back to PaddleOCR if configured.
    """
    global _ocr_engine, _ocr_backend
    if _ocr_engine is not None:
        return _ocr_engine, _ocr_backend

    preferred = str(cfg("processing", "ocr_engine", default="auto")).lower()
    errors: list[str] = []

    def try_rapid() -> bool:
        global _ocr_engine, _ocr_backend
        try:
            from rapidocr_onnxruntime import RapidOCR

            _ocr_engine = RapidOCR()
            _ocr_backend = "rapidocr"
            logger.info("OCR backend ready: RapidOCR (onnxruntime)")
            return True
        except Exception as exc:  # noqa: BLE001
            errors.append(f"RapidOCR: {exc}")
            return False

    def try_paddle() -> bool:
        global _ocr_engine, _ocr_backend
        # Mitigate known Windows oneDNN / PIR crashes on Paddle 3.x
        os.environ.setdefault("FLAGS_use_mkldnn", "0")
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        try:
            from paddleocr import PaddleOCR

            try:
                _ocr_engine = PaddleOCR(
                    lang="en",
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                )
            except TypeError:
                try:
                    _ocr_engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
                except TypeError:
                    _ocr_engine = PaddleOCR(lang="en")
            _ocr_backend = "paddleocr"
            logger.info("OCR backend ready: PaddleOCR")
            return True
        except Exception as exc:  # noqa: BLE001
            errors.append(f"PaddleOCR: {exc}")
            return False

    order = []
    if preferred == "paddleocr":
        order = [try_paddle, try_rapid]
    elif preferred == "rapidocr":
        order = [try_rapid, try_paddle]
    else:
        # auto: RapidOCR first on Windows (more reliable), else paddle then rapid
        if os.name == "nt":
            order = [try_rapid, try_paddle]
        else:
            order = [try_paddle, try_rapid]

    for attempt in order:
        if attempt():
            return _ocr_engine, _ocr_backend

    raise OCRFailureError(
        "No OCR backend available. Install with: "
        "pip install rapidocr-onnxruntime onnxruntime "
        "(or paddleocr paddlepaddle). Details: " + " | ".join(errors)
    )


def _ocr_page_image(pix: fitz.Pixmap) -> list[dict[str, Any]]:
    """Return list of {text, x0, y0, x1, y1} from OCR."""
    ocr, backend = _get_ocr()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    # OpenCV/RapidOCR expect contiguous BGR or RGB uint8
    img = np.ascontiguousarray(img)

    if backend == "rapidocr":
        result, _elapse = ocr(img)
        lines: list[dict[str, Any]] = []
        if not result:
            return lines
        for item in result:
            # item: [box(4 points), text, score]
            try:
                box, text, _score = item[0], item[1], item[2]
                xs = [float(p[0]) for p in box]
                ys = [float(p[1]) for p in box]
                lines.append(
                    {
                        "text": str(text).strip(),
                        "x0": min(xs),
                        "y0": min(ys),
                        "x1": max(xs),
                        "y1": max(ys),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("RapidOCR line skipped: %s", exc)
        return lines

    # PaddleOCR path (2.x ocr() or 3.x predict())
    lines = []
    try:
        if hasattr(ocr, "predict"):
            # Save temp image — some paddle builds are more stable with file input
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                pix.save(tmp_path)
                result = ocr.predict(tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
            lines = _parse_paddle_v3(result)
            if lines:
                return lines
        result = ocr.ocr(img, cls=True) if "cls" in (ocr.ocr.__code__.co_varnames) else ocr.ocr(img)
    except TypeError:
        result = ocr.ocr(img)
    except Exception as exc:  # noqa: BLE001
        raise OCRFailureError(f"PaddleOCR inference failed: {exc}") from exc

    return _parse_paddle_v2(result)


def _parse_paddle_v2(result: Any) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    if not result:
        return lines
    blocks = result[0] if result and isinstance(result[0], list) else result
    if not blocks:
        return lines
    for item in blocks:
        try:
            if isinstance(item, dict):
                text = item.get("transcription") or item.get("text") or ""
                box = item.get("points") or item.get("box") or []
            else:
                box, rec = item[0], item[1]
                text = rec[0] if isinstance(rec, (list, tuple)) else str(rec)
            if not text or not box:
                continue
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            lines.append(
                {
                    "text": str(text).strip(),
                    "x0": float(min(xs)),
                    "y0": float(min(ys)),
                    "x1": float(max(xs)),
                    "y1": float(max(ys)),
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("PaddleOCR v2 line skipped: %s", exc)
    return lines


def _parse_paddle_v3(result: Any) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    if not result:
        return lines
    for page in result:
        texts = None
        boxes = None
        if hasattr(page, "rec_texts") and hasattr(page, "rec_boxes"):
            texts = list(page.rec_texts or [])
            boxes = list(page.rec_boxes or [])
        elif isinstance(page, dict):
            texts = page.get("rec_texts") or page.get("texts")
            boxes = page.get("rec_boxes") or page.get("dt_polys") or page.get("boxes")
        if not texts:
            continue
        for i, text in enumerate(texts):
            box = boxes[i] if boxes and i < len(boxes) else None
            if box is None:
                lines.append({"text": str(text).strip(), "x0": 0, "y0": float(i), "x1": 1, "y1": float(i) + 1})
                continue
            arr = np.array(box, dtype=float).reshape(-1, 2)
            lines.append(
                {
                    "text": str(text).strip(),
                    "x0": float(arr[:, 0].min()),
                    "y0": float(arr[:, 1].min()),
                    "x1": float(arr[:, 0].max()),
                    "y1": float(arr[:, 1].max()),
                }
            )
    return lines


def _cluster_rows(lines: list[dict[str, Any]], y_tol: float = 12.0) -> list[list[dict[str, Any]]]:
    if not lines:
        return []
    ordered = sorted(lines, key=lambda L: (L["y0"], L["x0"]))
    rows: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = [ordered[0]]
    current_y = ordered[0]["y0"]

    for line in ordered[1:]:
        if abs(line["y0"] - current_y) <= y_tol:
            current.append(line)
        else:
            rows.append(sorted(current, key=lambda L: L["x0"]))
            current = [line]
            current_y = line["y0"]
    rows.append(sorted(current, key=lambda L: L["x0"]))
    return rows


HEADER_KEYWORDS = {
    "scheme",
    "security",
    "isin",
    "qty",
    "quantity",
    "units",
    "nav",
    "price",
    "value",
    "market",
    "holding",
    "symbol",
    "ticker",
    "cusip",
    "sedol",
    "instrument",
    "fund",
    "scrip",
    "company",
    "balance",
}


def _header_score(row: list[str]) -> int:
    score = 0
    for cell in row:
        tokens = re.findall(r"[a-z]+", cell.lower())
        for t in tokens:
            if t in HEADER_KEYWORDS:
                score += 3
            elif t in {"name", "date", "ccy", "currency", "type"}:
                score += 1
    return score


def _rows_to_table(row_clusters: list[list[dict[str, Any]]]) -> tuple[list[str], list[dict[str, Any]]]:
    # Prefer rows with 2+ cells; holdings tables often have 3+
    candidates = [[c["text"] for c in row] for row in row_clusters if len(row) >= 2]
    if not candidates:
        return [], []

    scored = [(i, _header_score(row), row) for i, row in enumerate(candidates)]
    scored.sort(key=lambda x: (x[1], len(x[2])), reverse=True)
    best_i, best_score, _ = scored[0]

    if best_score <= 0:
        # Fallback: first mostly-alpha multi-column row
        header_idx = 0
        for i, row in enumerate(candidates):
            alpha = sum(1 for c in row if re.search(r"[A-Za-z]", c))
            if alpha >= max(2, len(row) // 2) and len(row) >= 3:
                header_idx = i
                break
    else:
        header_idx = best_i

    headers = candidates[header_idx]
    seen: dict[str, int] = {}
    unique: list[str] = []
    for h in headers:
        key = h or "col"
        if key in seen:
            seen[key] += 1
            unique.append(f"{key}_{seen[key]}")
        else:
            seen[key] = 1
            unique.append(key)
    headers = unique

    data: list[dict[str, Any]] = []
    for row in candidates[header_idx + 1 :]:
        cells = list(row)
        if len(cells) < len(headers):
            cells += [""] * (len(headers) - len(cells))
        cells = cells[: len(headers)]
        if not any(cells):
            continue
        # Skip signature / address / footer noise rows
        joined = " ".join(cells).lower()
        if any(
            bad in joined
            for bad in (
                "digitally signed",
                "www.",
                "dp id",
                "regn",
                "reason:",
                "messages:",
                "system generated",
                "signature not required",
            )
        ):
            continue
        if cells and str(cells[0]).strip().lower().startswith("total"):
            continue
        data.append(dict(zip(headers, cells)))

    return headers, data


def extract_with_paddleocr(pdf_bytes: bytes, source_label: str = "input") -> ExtractionResult:
    """Extract holdings from a scanned/image PDF via OCR (RapidOCR or PaddleOCR)."""
    logger.info("Extracting with OCR (scanned PDF): %s", source_label)
    if not bool(cfg("processing", "ocr_enabled", default=True)):
        raise OCRFailureError("OCR is disabled in config (processing.ocr_enabled=false)")

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise OCRFailureError(f"Failed to open PDF for OCR: {exc}") from exc

    try:
        all_lines: list[dict[str, Any]] = []
        text_parts: list[str] = []
        backend_name = "ocr"

        for i, page in enumerate(doc):
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            logger.info("OCR page %s (%sx%s)...", i + 1, pix.width, pix.height)
            try:
                lines = _ocr_page_image(pix)
                _, backend_name = _get_ocr()
            except OCRFailureError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise OCRFailureError(f"OCR failed on page {i + 1}: {exc}") from exc
            logger.info("Page %s OCR lines: %s", i + 1, len(lines))
            all_lines.extend(lines)
            text_parts.append(" ".join(L["text"] for L in lines))

        full_text = "\n".join(text_parts)
        metadata = _extract_metadata_from_text(full_text)
        logger.info("Metadata extracted (OCR): %s", metadata)

        # Slightly looser clustering for OCR noise
        clusters = _cluster_rows(all_lines, y_tol=18.0)
        headers, rows = _rows_to_table(clusters)
        logger.info(
            "OCR table reconstruction | backend=%s headers=%s rows=%s",
            backend_name,
            headers,
            len(rows),
        )

        if not headers or not rows:
            logger.warning("OCR table weak — falling back to universal statement parser")
            headers, rows, parse_warnings = ensure_rows_from_text(full_text)
            if parse_warnings:
                metadata = {**metadata, "_extract_warnings": parse_warnings}

        if not full_text.strip():
            raise OCRFailureError("OCR produced no text from the scanned PDF")

        if not rows:
            headers, rows, parse_warnings = ensure_rows_from_text(full_text)
            metadata = {
                **metadata,
                "_extract_warnings": list(metadata.get("_extract_warnings") or [])
                + parse_warnings,
            }

        return ExtractionResult(
            pdf_type="scanned",
            extractor=backend_name or "ocr",
            metadata=metadata,
            headers=headers,
            rows=rows,
            raw_text=full_text,
            raw_text_preview=full_text[:500],
        )
    finally:
        doc.close()
