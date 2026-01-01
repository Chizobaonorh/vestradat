import mediapipe as mp
import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

# Initialize MediaPipe
mp_pose = mp.solutions.pose
mp_segmentation = mp.solutions.selfie_segmentation
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

pose_detector = mp_pose.Pose(
    static_image_mode=True,
    model_complexity=2,
    enable_segmentation=True,
    min_detection_confidence=0.5
)

segmenter = mp_segmentation.SelfieSegmentation(model_selection=1)

def load_image_from_path(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Could not find image at: {path}")
    
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Failed to decode image at: {path}")
        
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img_rgb

def get_segmentation_mask(image):
    pose_results = pose_detector.process(image)
    pose_mask = None

    if pose_results.segmentation_mask is not None:
        pose_mask = (pose_results.segmentation_mask > 0.5).astype(np.uint8) * 255

    seg_results = segmenter.process(image)
    selfie_mask = (seg_results.segmentation_mask > 0.5).astype(np.uint8) * 255

    if pose_mask is not None:
        combined_mask = cv2.bitwise_or(pose_mask, selfie_mask)
    else:
        combined_mask = selfie_mask

    kernel = np.ones((5,5), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        mask_filled = np.zeros_like(combined_mask)
        cv2.drawContours(mask_filled, [largest_contour], -1, 255, -1)
        combined_mask = mask_filled

    return combined_mask, pose_results

POSE_LANDMARKS = {
    'nose': 0, 'left_shoulder': 11, 'right_shoulder': 12,
    'left_elbow': 13, 'right_elbow': 14, 'left_wrist': 15, 'right_wrist': 16,
    'left_hip': 23, 'right_hip': 24, 'left_knee': 25, 'right_knee': 26,
    'left_ankle': 27, 'right_ankle': 28,
}

def get_landmark_coords(landmarks, image_shape, landmark_name):
    idx = POSE_LANDMARKS[landmark_name]
    landmark = landmarks[idx]
    h, w = image_shape[:2]
    return (int(landmark.x * w), int(landmark.y * h), landmark.visibility)

def calculate_distance(point1, point2):
    return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def get_body_width_at_height(mask, y_position, search_range=5):
    widths = []
    for offset in range(-search_range, search_range + 1):
        row_idx = y_position + offset
        if 0 <= row_idx < mask.shape[0]:
            row = mask[row_idx, :]
            pixels = np.where(row > 0)[0]
            if len(pixels) > 1:
                widths.append(pixels[-1] - pixels[0])
    return np.median(widths) if widths else 0

def find_narrowest_width(mask, start_y, end_y):
    min_width, narrowest_y = float('inf'), start_y
    for y in range(start_y, end_y):
        if 0 <= y < mask.shape[0]:
            row = mask[y, :]
            pixels = np.where(row > 0)[0]
            if len(pixels) > 1:
                width = pixels[-1] - pixels[0]
                if 10 < width < min_width:
                    min_width, narrowest_y = width, y
    return (min_width if min_width != float('inf') else 0), narrowest_y

def find_widest_width(mask, start_y, end_y):
    max_width, widest_y = 0, start_y
    for y in range(start_y, end_y):
        if 0 <= y < mask.shape[0]:
            row = mask[y, :]
            pixels = np.where(row > 0)[0]
            if len(pixels) > 1:
                width = pixels[-1] - pixels[0]
                if width > max_width:
                    max_width, widest_y = width, y
    return max_width, widest_y


def calibrate_with_height(pose_results, image_shape, user_height_cm):
    if not pose_results.pose_landmarks: return 1.0
    landmarks = pose_results.pose_landmarks.landmark
    nose = get_landmark_coords(landmarks, image_shape, 'nose')
    l_ankle = get_landmark_coords(landmarks, image_shape, 'left_ankle')
    r_ankle = get_landmark_coords(landmarks, image_shape, 'right_ankle')
    bottom_y = max(l_ankle[1], r_ankle[1])
    height_pixels = bottom_y - nose[1]
    return height_pixels / (user_height_cm / 2.54)

def calculate_front_measurements(image, mask, pose_results, ppi):
    m = {}
    if not pose_results.pose_landmarks: return m
    landmarks = pose_results.pose_landmarks.landmark
    px_to_in = lambda px: px / ppi

    sh_l = get_landmark_coords(landmarks, image.shape, 'left_shoulder')
    sh_r = get_landmark_coords(landmarks, image.shape, 'right_shoulder')
    hip_l = get_landmark_coords(landmarks, image.shape, 'left_hip')
    hip_r = get_landmark_coords(landmarks, image.shape, 'right_hip')
    
    # Simple Widths
    m['shoulder_width'] = px_to_in(abs(sh_r[0] - sh_l[0]))
    
    # Chest
    torso_h = hip_l[1] - sh_l[1]
    chest_y = int(sh_l[1] + torso_h * 0.25)
    m['chest_width'] = px_to_in(get_body_width_at_height(mask, chest_y))
    m['_chest_y'] = chest_y

    # Waist
    w_width, w_y = find_narrowest_width(mask, int(sh_l[1] + torso_h * 0.4), int(sh_l[1] + torso_h * 0.7))
    m['waist_width'], m['_waist_y'] = px_to_in(w_width), w_y

    # Hip
    h_width, h_y = find_widest_width(mask, hip_l[1] - 20, hip_l[1] + 60)
    m['hip_width'], m['_hip_y'] = px_to_in(h_width), h_y

    return m

def calculate_side_measurements(image, mask, pose_results, ppi):
    m = {}
    if not pose_results.pose_landmarks: return m
    landmarks = pose_results.pose_landmarks.landmark
    px_to_in = lambda px: px / ppi
    sh_l = get_landmark_coords(landmarks, image.shape, 'left_shoulder')
    hip_l = get_landmark_coords(landmarks, image.shape, 'left_hip')
    torso_h = hip_l[1] - sh_l[1]

    m['chest_depth'] = px_to_in(get_body_width_at_height(mask, int(sh_l[1] + torso_h * 0.25)))
    w_depth, w_y = find_narrowest_width(mask, int(sh_l[1] + torso_h * 0.4), int(sh_l[1] + torso_h * 0.7))
    m['waist_depth'] = px_to_in(w_depth)
    h_depth, h_y = find_widest_width(mask, hip_l[1] - 20, hip_l[1] + 60)
    m['hip_depth'] = px_to_in(h_depth)
    return m

def calculate_circumferences(front, side):
    circs = {}
    def ellipse(w, d):
        a, b = w/2, d/2
        h = ((a-b)**2) / ((a+b)**2)
        return np.pi * (a+b) * (1 + (3*h)/(10 + np.sqrt(4-3*h)))
    
    if 'chest_width' in front and 'chest_depth' in side:
        circs['chest'] = ellipse(front['chest_width'], side['chest_depth'])
    if 'waist_width' in front and 'waist_depth' in side:
        circs['waist'] = ellipse(front['waist_width'], side['waist_depth'])
    if 'hip_width' in front and 'hip_depth' in side:
        circs['hips'] = ellipse(front['hip_width'], side['hip_depth'])
    return circs


def visualize_results(image, mask, pose, measurements, view_name):
    plt.figure(figsize=(10, 5))
    annotated = image.copy()
    if pose.pose_landmarks:
        mp_drawing.draw_landmarks(annotated, pose.pose_landmarks, mp_pose.POSE_CONNECTIONS)
    
    plt.imshow(annotated)
    plt.title(f"{view_name.capitalize()} View Analysis")
    plt.axis('off')
    plt.show()


def run_measurement_tool(front_path, side_path, height_cm):
    print(f"\n--- Processing Body Measurements ---")
    
    # 1. Load and Segment
    img_f = load_image_from_path(front_path)
    mask_f, pose_f = get_segmentation_mask(img_f)
    
    img_s = load_image_from_path(side_path)
    mask_s, pose_s = get_segmentation_mask(img_s)
    
    # 2. Calibrate
    ppi_f = calibrate_with_height(pose_f, img_f.shape, height_cm)
    ppi_s = calibrate_with_height(pose_s, img_s.shape, height_cm)
    
    # 3. Calculate
    m_front = calculate_front_measurements(img_f, mask_f, pose_f, ppi_f)
    m_side = calculate_side_measurements(img_s, mask_s, pose_s, ppi_s)
    circs = calculate_circumferences(m_front, m_side)
    
    # 4. Report
    print(f"\nRESULTS (inches):")
    for key, val in circs.items():
        print(f"  - {key.capitalize()} Circumference: {val:.2f}\"")
    
    # 5. Visualize
    visualize_results(img_f, mask_f, pose_f, m_front, "front")
    visualize_results(img_s, mask_s, pose_s, m_side, "side")

if __name__ == "__main__":
    USER_HEIGHT = 175.0  # cm
    FRONT_IMAGE_PATH = "front_photo.jpg" 
    SIDE_IMAGE_PATH = "side_photo.jpg"
    
    try:
        run_measurement_tool(FRONT_IMAGE_PATH, SIDE_IMAGE_PATH, USER_HEIGHT)
    except Exception as e:
        print(f"Error: {e}")