import os
import cv2
import json
import numpy as np
import tensorflow as tf
import requests

# =====================================================
# BASE DIRECTORY (CRITICAL FOR CLOUD)
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =====================================================
# CONFIGURATION (CLOUD-SAFE PATHS)
# =====================================================
DIGITS_MODEL_PATH = os.path.join(
    BASE_DIR, "models", "digits_model_experiment_1.keras"
)
LETTERS_MODEL_PATH = os.path.join(
    BASE_DIR, "models", "emnist_a_to_d_robust_classifier.keras"
)

DEBUG_SAVE_DIR = os.path.join(BASE_DIR, "debug_crops")
STATIC_DIR = os.path.join(BASE_DIR, "static")
ANSWER_KEY_DIR = os.path.join(BASE_DIR, "answer_keys")

os.makedirs(DEBUG_SAVE_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(ANSWER_KEY_DIR, exist_ok=True)

DIGIT_CLASS_NAMES = [str(i) for i in range(10)]
LETTER_CLASS_NAMES = ['A', 'B', 'C', 'D']

# =====================================================
# DOWNLOAD MODEL IF NOT PRESENT (GITHUB RELEASE SAFE)
# =====================================================
def ensure_model(path, url):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"Downloading model: {path}")
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"Model downloaded: {path}")

# =====================================================
# ENSURE MODELS EXIST (DOWNLOAD ON FIRST RUN)
# =====================================================
ensure_model(
    DIGITS_MODEL_PATH,
    "https://github.com/Yajnesh-code/-handwriting-recognition-grading-app/releases/download/v1.0/digits_model_experiment_1.keras"
)

ensure_model(
    LETTERS_MODEL_PATH,
    "https://github.com/Yajnesh-code/-handwriting-recognition-grading-app/releases/download/v1.0/emnist_a_to_d_robust_classifier.keras"
)

# =====================================================
# LAZY MODEL LOADING (RENDER-SAFE)
# =====================================================
digits_model = None
letters_model = None

def load_models():
    global digits_model, letters_model
    if digits_model is None:
        digits_model = tf.keras.models.load_model(DIGITS_MODEL_PATH)
    if letters_model is None:
        letters_model = tf.keras.models.load_model(LETTERS_MODEL_PATH)

# =====================================================
# LOAD ANSWER KEY
# =====================================================
def load_answer_key(exam_code):
    path = os.path.join(ANSWER_KEY_DIR, f"{exam_code}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)

# =====================================================
# HELPER FUNCTIONS (UNCHANGED LOGIC)
# =====================================================
def preprocess_char_for_model(char_gray):
    img = char_gray.copy()
    if len(img.shape) != 2:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, img_bin = cv2.threshold(
        img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    h, w = img_bin.shape
    if h > w:
        new_h, new_w = 20, max(1, int(round(w * 20.0 / h)))
    else:
        new_w, new_h = 20, max(1, int(round(h * 20.0 / w)))
    resized = cv2.resize(img_bin, (new_w, new_h), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((28, 28), dtype=np.uint8)
    x_offset, y_offset = (28 - new_w) // 2, (28 - new_h) // 2
    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
    final = canvas.astype(np.float32) / 255.0
    if final.mean() > 0.5:
        final = 1.0 - final
    return np.expand_dims(np.expand_dims(final, axis=0), axis=-1), canvas


def segment_digits(crop_gray):
    _, bin_img = cv2.threshold(
        crop_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    contours, _ = cv2.findContours(
        bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    boxes = sorted(
        [
            cv2.boundingRect(c)
            for c in contours
            if cv2.boundingRect(c)[3] > 6 and cv2.boundingRect(c)[2] > 2
        ],
        key=lambda b: b[0],
    )
    return [crop_gray[y:y + h, x:x + w] for (x, y, w, h) in boxes]


def two_cluster_x(centers_x, iters=8):
    xs = np.array(centers_x, dtype=np.float32)
    if len(xs) < 2:
        return np.ones(len(xs), dtype=bool)
    c1, c2 = xs.min(), xs.max()
    for _ in range(iters):
        assign = np.abs(xs - c1) < np.abs(xs - c2)
        if assign.sum() > 0:
            c1 = xs[assign].mean()
        if (~assign).sum() > 0:
            c2 = xs[~assign].mean()
    mean1 = xs[assign].mean() if assign.sum() > 0 else c1
    return assign if mean1 < (
        xs[~assign].mean() if (~assign).sum() > 0 else c2
    ) else ~assign

# =====================================================
# MAIN PROCESSING FUNCTION (UNCHANGED LOGIC)
# =====================================================
def process_mcq_image(PAGE_IMAGE_PATH, exam_code):
    load_models()

    answer_key = load_answer_key(exam_code)
    if answer_key is None:
        return {"error": f"No answer key found for exam_code '{exam_code}'"}

    image = cv2.imread(PAGE_IMAGE_PATH)
    if image is None:
        return {"error": f"Image not found at {PAGE_IMAGE_PATH}"}

    orig = image.copy()
    image_vis = orig.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape

    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    thresh_closed = cv2.morphologyEx(
        thresh, cv2.MORPH_CLOSE, kernel, iterations=1
    )
    contours, _ = cv2.findContours(
        thresh_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = []
    min_w, min_h = max(8, W // 150), max(12, H // 60)
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w >= min_w and h >= min_h:
            candidates.append({
                'bbox': (x, y, w, h),
                'cx': x + w / 2.0,
                'cy': y + h / 2.0
            })

    if not candidates:
        return {"error": "No character candidates found."}

    centers_x = [c['cx'] for c in candidates]
    mask = two_cluster_x(centers_x)
    left_candidates = sorted(
        [c for i, c in enumerate(candidates) if mask[i]],
        key=lambda c: c['cy']
    )
    right_candidates = sorted(
        [c for i, c in enumerate(candidates) if not mask[i]],
        key=lambda c: c['cy']
    )

    pairs = []
    right_pointer = 0
    all_heights = [c['bbox'][3] for c in candidates]
    median_h = np.median(all_heights) if all_heights else 30
    vertical_tolerance = max(25, int(0.9 * median_h))

    for left in left_candidates:
        found_pair = False
        for i in range(right_pointer, len(right_candidates)):
            right = right_candidates[i]
            if abs(left['cy'] - right['cy']) < vertical_tolerance:
                pairs.append((left, right))
                right_pointer = i + 1
                found_pair = True
                break
        if not found_pair:
            pairs.append((left, None))

    report_rows = []
    pad = max(3, W // 300)

    for left, right in pairs:
        lx, ly, lw, lh = left['bbox']
        left_crop = gray[
            max(0, ly - pad):min(H, ly + lh + pad),
            max(0, lx - pad):min(W, lx + lw + pad)
        ]

        digit_str = "".join([
            DIGIT_CLASS_NAMES[
                np.argmax(
                    digits_model.predict(
                        preprocess_char_for_model(ch)[0],
                        verbose=0
                    )[0]
                )
            ]
            for ch in segment_digits(left_crop)
        ])
        predicted_digit = digit_str if digit_str else "?"

        predicted_letter = ""
        if right:
            rx, ry, rw, rh = right['bbox']
            right_crop = gray[
                max(0, ry - pad):min(H, ry + rh + pad),
                max(0, rx - pad):min(W, rx + rw + pad)
            ]
            if right_crop.size > 0:
                prepared, _ = preprocess_char_for_model(right_crop)
                predicted_letter = LETTER_CLASS_NAMES[
                    np.argmax(
                        letters_model.predict(prepared, verbose=0)[0]
                    )
                ]

        result, color = "NoKey", (0, 165, 255)
        if predicted_digit in answer_key:
            correct_opt = answer_key[predicted_digit]
            if predicted_letter == "":
                result, color = "NotAttempted", (0, 255, 255)
            elif predicted_letter == correct_opt:
                result, color = "Correct", (0, 255, 0)
            else:
                result, color = "Wrong", (0, 0, 255)

        label_text = f"{predicted_digit}: {predicted_letter}"
        if predicted_digit in answer_key:
            label_text += f" / {answer_key[predicted_digit]}"

        cv2.putText(
            image_vis, label_text, (lx, ly - 12),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
        )
        cv2.rectangle(
            image_vis, (lx, ly), (lx + lw, ly + lh), color, 2
        )
        if right:
            rx, ry, rw, rh = right['bbox']
            cv2.rectangle(
                image_vis, (rx, ry), (rx + rw, ry + rh), color, 2
            )

        report_rows.append({
            "question_pred": predicted_digit,
            "option_pred": predicted_letter,
            "result": result
        })

    total_questions = len(answer_key)
    filtered = [
        r for r in report_rows if r["question_pred"] in answer_key
    ]
    score = sum(1 for r in filtered if r["result"] == "Correct")
    percentage = (
        round((score / total_questions) * 100, 2)
        if total_questions > 0 else 0
    )

    annotated_filename = f"annotated_{os.path.basename(PAGE_IMAGE_PATH)}"
    OUT_VIS_PATH = os.path.join(STATIC_DIR, annotated_filename)
    cv2.imwrite(OUT_VIS_PATH, image_vis)

    return {
        "score": score,
        "total": total_questions,
        "percentage": percentage,
        "results": filtered,
        "annotated_image_url": f"/static/{annotated_filename}"
    }
