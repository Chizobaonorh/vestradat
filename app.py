import mediapipe as mp
import cv2
import numpy as np
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello Render!"


mp_pose = mp.solutions.pose
mp_segmentation = mp.solutions.selfie_segmentation

pose_detector = mp_pose.Pose(
    static_image_mode=True,
    model_complexity=2,
    enable_segmentation=True,
    min_detection_confidence=0.5
)
segmenter = mp_segmentation.SelfieSegmentation(model_selection=1)

POSE_LANDMARKS = {
    'nose': 0, 'left_shoulder': 11, 'right_shoulder': 12,
    'left_elbow': 13, 'right_elbow': 14, 'left_wrist': 15, 'right_wrist': 16,
    'left_hip': 23, 'right_hip': 24, 'left_knee': 25, 'right_knee': 26,
    'left_ankle': 27, 'right_ankle': 28
}

CM_TO_INCH = 1 / 2.54


def load_image_from_url(url: str):
    resp = requests.get(url)
    if resp.status_code != 200:
        raise ValueError(f"Failed to fetch image from {url}")
    nparr = np.frombuffer(resp.content, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image from URL")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def get_segmentation_mask(img):
    pose_results = pose_detector.process(img)
    seg_results = segmenter.process(img)

    pose_mask = None
    if pose_results.segmentation_mask is not None:
        pose_mask = (pose_results.segmentation_mask > 0.5).astype(np.uint8) * 255

    selfie_mask = (seg_results.segmentation_mask > 0.5).astype(np.uint8) * 255

    mask = cv2.bitwise_or(pose_mask, selfie_mask) if pose_mask is not None else selfie_mask

    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.dilate(mask, kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        filled = np.zeros_like(mask)
        cv2.drawContours(filled, [largest], -1, 255, -1)
        mask = filled

    return mask, pose_results


def get_lm_xy(lm, shape, name):
    idx = POSE_LANDMARKS[name]
    h, w = shape[:2]
    return np.array([lm[idx].x * w, lm[idx].y * h])


def get_width_at_y(mask, y, search_range=10):
    if y < 0 or y >= mask.shape[0]:
        return 0
    widths = []
    for offset in range(-search_range, search_range + 1):
        cy = y + offset
        if 0 <= cy < mask.shape[0]:
            row = mask[cy, :]
            px = np.where(row > 0)[0]
            if len(px) > 1:
                widths.append(px[-1] - px[0])
    return np.median(widths) if widths else 0


def ellipse_circumference(width, depth):
    a, b = width / 2, depth / 2
    h = ((a - b) ** 2) / ((a + b) ** 2)
    return np.pi * (a + b) * (1 + (3 * h) / (10 + np.sqrt(4 - 3 * h)))


def calculate_scale_from_height(pose_results, img_shape, actual_height_cm):
    if not pose_results.pose_landmarks:
        return None
    lm = pose_results.pose_landmarks.landmark
    nose = get_lm_xy(lm, img_shape, 'nose')
    left_ank = get_lm_xy(lm, img_shape, 'left_ankle')
    right_ank = get_lm_xy(lm, img_shape, 'right_ankle')
    ankle = (left_ank + right_ank) / 2
    height_px = abs(ankle[1] - nose[1])
    return actual_height_cm / height_px if height_px > 0 else None



def calc_front_measurements(img, mask, pose_results):
    if not pose_results.pose_landmarks:
        return None
    lm = pose_results.pose_landmarks.landmark
    left_sh = get_lm_xy(lm, img.shape, 'left_shoulder')
    right_sh = get_lm_xy(lm, img.shape, 'right_shoulder')
    left_hip = get_lm_xy(lm, img.shape, 'left_hip')
    right_hip = get_lm_xy(lm, img.shape, 'right_hip')

    shoulder_y = int((left_sh[1] + right_sh[1]) / 2)
    hip_y = int((left_hip[1] + right_hip[1]) / 2)
    torso_h = hip_y - shoulder_y

    chest_y = int(shoulder_y + torso_h * 0.2)
    bust_y = int(shoulder_y + torso_h * 0.4)
    waist_y = int(shoulder_y + torso_h * 0.65)
    hip_y = int(shoulder_y + torso_h * 0.85)
    butt_y = int(hip_y + torso_h * 0.1)

    return {
        'shoulder': get_width_at_y(mask, shoulder_y),
        'chest': get_width_at_y(mask, chest_y),
        'bust': get_width_at_y(mask, bust_y),
        'waist': get_width_at_y(mask, waist_y),
        'hip': get_width_at_y(mask, hip_y),
        'butt': get_width_at_y(mask, butt_y)
    }


def calc_side_measurements(img, mask, pose_results):
    if not pose_results.pose_landmarks:
        return None

    lm = pose_results.pose_landmarks.landmark
    left_sh = get_lm_xy(lm, img.shape, 'left_shoulder')
    right_sh = get_lm_xy(lm, img.shape, 'right_shoulder')
    left_hip = get_lm_xy(lm, img.shape, 'left_hip')
    right_hip = get_lm_xy(lm, img.shape, 'right_hip')

    shoulder_y = int((left_sh[1] + right_sh[1]) / 2)
    hip_y = int((left_hip[1] + right_hip[1]) / 2)
    torso_h = hip_y - shoulder_y

    chest_y = int(shoulder_y + torso_h * 0.2)
    bust_y = int(shoulder_y + torso_h * 0.4)
    waist_y = int(shoulder_y + torso_h * 0.65)
    hip_y = int(shoulder_y + torso_h * 0.85)
    butt_y = int(hip_y + torso_h * 0.1)

    return {
        'chest_depth': get_width_at_y(mask, chest_y),
        'bust_depth': get_width_at_y(mask, bust_y),
        'waist_depth': get_width_at_y(mask, waist_y),
        'hip_depth': get_width_at_y(mask, hip_y),
        'butt_depth': get_width_at_y(mask, butt_y)
    }


def calc_linear_measurements(img, pose_results):
    if not pose_results.pose_landmarks:
        return None

    lm = pose_results.pose_landmarks.landmark

    if lm[POSE_LANDMARKS['left_shoulder']].visibility > lm[POSE_LANDMARKS['right_shoulder']].visibility:
        sh = get_lm_xy(lm, img, 'left_shoulder')
        el = get_lm_xy(lm, img, 'left_elbow')
        wr = get_lm_xy(lm, img, 'left_wrist')
        hip = get_lm_xy(lm, img, 'left_hip')
        knee = get_lm_xy(lm, img, 'left_knee')
        ank = get_lm_xy(lm, img, 'left_ankle')
    else:
        sh = get_lm_xy(lm, img, 'right_shoulder')
        el = get_lm_xy(lm, img, 'right_elbow')
        wr = get_lm_xy(lm, img, 'right_wrist')
        hip = get_lm_xy(lm, img, 'right_hip')
        knee = get_lm_xy(lm, img, 'right_knee')
        ank = get_lm_xy(lm, img, 'right_ankle')

    arm_length = np.linalg.norm(sh - el) + np.linalg.norm(el - wr)
    inseam = np.linalg.norm(hip - knee) + np.linalg.norm(knee - ank)

    return {'arm_length': arm_length, 'inseam': inseam}


def run_measurement_tool_from_images(img_front, img_side, height_cm):
    mask_front, pose_front = get_segmentation_mask(img_front)
    mask_side, pose_side = get_segmentation_mask(img_side)

    scale_cm = calculate_scale_from_height(pose_front, img_front.shape, height_cm) if height_cm else 0.2
    scale_inch = scale_cm * CM_TO_INCH

    front_meas = calc_front_measurements(img_front, mask_front, pose_front)
    side_meas = calc_side_measurements(img_side, mask_side, pose_side)
    linear_meas = calc_linear_measurements(img_side, pose_side)

    results = {}
    for part in ['chest', 'bust', 'waist', 'hip', 'butt']:
        width = front_meas.get(part, 0) * scale_inch
        depth = side_meas.get(f'{part}_depth', 0) * scale_inch
        results[part] = ellipse_circumference(width, depth)

    results['shoulder_width'] = front_meas.get('shoulder', 0) * scale_inch
    for k, v in linear_meas.items():
        results[k] = v * scale_inch

    return results


@app.route("/measure", methods=["POST"])
def measure():
    data = request.json

    height_cm = data.get("height_cm")
    front_url = data.get("front_image_url")
    side_url = data.get("side_image_url")

    img_front = load_image_from_url(front_url)
    img_side = load_image_from_url(side_url)

    results = run_measurement_tool_from_images(img_front, img_side, height_cm)
    return jsonify(results)
