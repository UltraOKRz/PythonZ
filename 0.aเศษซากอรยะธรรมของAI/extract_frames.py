import cv2, os

video_path = r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\1.Python Code\Video\บันทึก_2026_10_01_09_46_11_802.mp4"
out_dir = r"C:\Users\PythonX\.gemini\antigravity-ide\brain\dc3b2554-7403-4718-be5d-b5f2d78749b3\scratch\frames_ocr"
os.makedirs(out_dir, exist_ok=True)

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total / fps if fps > 0 else 0
print(f"FPS: {fps:.1f}, Total Frames: {total}, Duration: {duration:.1f}s")

# Extract 1 frame every 3 seconds
interval = max(1, int(fps * 3))
saved = 0
frame_idx = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    if frame_idx % interval == 0:
        ts = frame_idx / fps if fps > 0 else 0
        fname = os.path.join(out_dir, f"frame_{ts:06.1f}s.jpg")
        cv2.imwrite(fname, frame)
        saved += 1
    frame_idx += 1

cap.release()
print(f"Saved {saved} frames to {out_dir}")
files = sorted(os.listdir(out_dir))
for f in files:
    print(" ", f)
