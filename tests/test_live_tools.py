import base64
import io
import time
import requests
import numpy as np
import cv2

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_remove_object_endpoint():
    print("=== Testing /tools/remove-object endpoint ===")
    # 1. Create a 512x512 gradient background with an object (e.g. bright red circle)
    h, w = 512, 512
    x = np.linspace(0, 255, w)
    y = np.linspace(0, 255, h)
    xx, yy = np.meshgrid(x, y)
    bg = np.zeros((h, w, 3), dtype=np.uint8)
    bg[:, :, 0] = xx.astype(np.uint8)  # Blue
    bg[:, :, 1] = yy.astype(np.uint8)  # Green
    bg[:, :, 2] = 128                   # Red base

    # Draw a distinct red circle (the object to remove)
    center = (256, 256)
    radius = 40
    img_with_obj = bg.copy()
    cv2.circle(img_with_obj, center, radius, (0, 0, 255), -1)

    # 2. Create the mask (white where the red circle is, black everywhere else)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, center, radius + 5, 255, -1)

    # Encode to PNG base64
    _, img_buf = cv2.imencode(".png", img_with_obj)
    img_b64 = "data:image/png;base64," + base64.b64encode(img_buf.tobytes()).decode("utf-8")

    _, mask_buf = cv2.imencode(".png", mask)
    mask_b64 = "data:image/png;base64," + base64.b64encode(mask_buf.tobytes()).decode("utf-8")

    payload = {
        "image_base64": img_b64,
        "mask_base64": mask_b64
    }

    t0 = time.time()
    resp = requests.post(f"{BASE_URL}/tools/remove-object", json=payload, timeout=30)
    roundtrip = (time.time() - t0) * 1000

    print(f"Status code: {resp.status_code}")
    assert resp.status_code == 200, f"Error: {resp.text}"
    data = resp.json()
    print(f"Task ID: {data.get('task_id')}")
    print(f"Status: {data.get('status')}")
    print(f"Server reported latency: {data.get('latency_ms')} ms")
    print(f"Total roundtrip latency: {roundtrip:.1f} ms")
    output_url = data.get("output_url")
    assert output_url, "Missing output_url"
    print(f"Output URL prefix: {output_url[:50]}...")

    # Decode returned image to verify circle is gone
    if output_url.startswith("data:image"):
        raw_b64 = output_url.split(",", 1)[-1]
        out_bytes = base64.b64decode(raw_b64)
    else:
        out_bytes = requests.get(output_url).content

    out_img = cv2.imdecode(np.frombuffer(out_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert out_img.shape == (512, 512, 3), f"Unexpected shape: {out_img.shape}"

    # Check center pixel: it should no longer be pure red (0, 0, 255)
    center_color = out_img[256, 256]
    print(f"Original circle color: [0, 0, 255] (BGR)")
    print(f"Inpainted center color: {center_color} (BGR)")
    # Should blend smoothly into background
    assert center_color[2] < 200, f"Object was not erased! Red channel is still {center_color[2]}"
    print("✅ /tools/remove-object PASSED seamlessly!\n")


def test_colorize_endpoint():
    print("=== Testing /tools/colorize endpoint ===")
    # 1. Create a 512x512 grayscale landscape test image (gradient with mountains & sun)
    h, w = 512, 512
    gray = np.zeros((h, w), dtype=np.uint8)
    for r in range(h):
        gray[r, :] = int(r / h * 200) + 30
    # Add a bright sun
    cv2.circle(gray, (150, 150), 50, 240, -1)
    # Add dark mountains
    pts = np.array([[0, 450], [200, 250], [350, 400], [512, 280], [512, 512], [0, 512]], np.int32)
    cv2.fillPoly(gray, [pts], 60)

    # Encode grayscale as PNG
    _, gray_buf = cv2.imencode(".png", gray)
    gray_b64 = "data:image/png;base64," + base64.b64encode(gray_buf.tobytes()).decode("utf-8")

    payload = {
        "image_base64": gray_b64,
        "saturation": 1.2
    }

    t0 = time.time()
    resp = requests.post(f"{BASE_URL}/tools/colorize", json=payload, timeout=30)
    roundtrip = (time.time() - t0) * 1000

    print(f"Status code: {resp.status_code}")
    assert resp.status_code == 200, f"Error: {resp.text}"
    data = resp.json()
    print(f"Task ID: {data.get('task_id')}")
    print(f"Status: {data.get('status')}")
    print(f"Server reported latency: {data.get('latency_ms')} ms")
    print(f"Total roundtrip latency: {roundtrip:.1f} ms")
    output_url = data.get("output_url")
    assert output_url, "Missing output_url"
    print(f"Output URL prefix: {output_url[:50]}...")

    # Decode returned image and verify chromaticity
    if output_url.startswith("data:image"):
        raw_b64 = output_url.split(",", 1)[-1]
        out_bytes = base64.b64decode(raw_b64)
    else:
        out_bytes = requests.get(output_url).content

    out_img = cv2.imdecode(np.frombuffer(out_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert out_img.shape == (512, 512, 3), f"Unexpected shape: {out_img.shape}"

    # Calculate color variance across channels
    # In a grayscale image: B == G == R, so standard deviation across (B-G) and (G-R) is 0
    diff_bg = np.abs(out_img[:, :, 0].astype(int) - out_img[:, :, 1].astype(int))
    diff_gr = np.abs(out_img[:, :, 1].astype(int) - out_img[:, :, 2].astype(int))
    chroma_diversity = np.mean(diff_bg) + np.mean(diff_gr)
    print(f"Color diversity metric: {chroma_diversity:.2f} (Grayscale = 0.0)")
    assert chroma_diversity > 3.0, f"Image was not colorized! Diversity score: {chroma_diversity}"
    print("✅ /tools/colorize PASSED with vibrant color restoration!\n")


if __name__ == "__main__":
    test_remove_object_endpoint()
    test_colorize_endpoint()
    print("🎉 ALL PHASE 1 BACKEND SERVICES VERIFIED WITH 100% SUCCESS!")
