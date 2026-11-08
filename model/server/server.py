from concurrent import futures
import os
import queue
import time
import uuid

import cv2
import grpc
import numpy as np
import requests
import torch
from torchvision.transforms import functional as F
from ultralytics import YOLO

# Import generated modules from both original proto files
import result_pb2
import result_pb2_grpc
import video_pb2
import video_pb2_grpc

from model import IMG_SIZE, MEAN, STD, load_pothole_model


# Thread-safe queue of ProcessingResult messages awaiting delivery.
RESULT_QUEUE = queue.Queue()

# Detection model. Loaded once at import; reloading it per frame reads the
# weights off disk for every single frame.
#
# NOTE / known limitation: this is the stock COCO-trained yolov8n, so it detects
# people, cars and so on -- not potholes. The detection gate below is therefore
# a liveness check, not a pothole check, until a pothole-trained checkpoint
# replaces it.
model = YOLO("yolov8n.pt")

# Severity model. Also loaded once; it is a ~95 MB checkpoint.
SEVERITY_MODEL_PATH = os.environ.get("SEVERITY_MODEL_PATH", "length_of_pothole.pt")
try:
    SEVERITY_MODEL = load_pothole_model(SEVERITY_MODEL_PATH)
    print(f"Loaded pothole severity model from {SEVERITY_MODEL_PATH}")
except Exception as error:  # missing file, bad weights, torch not installed
    SEVERITY_MODEL = None
    print(f"WARNING: severity model unavailable ({error}); severity will report 0")

# Pinhole-camera constants for turning a predicted box height in pixels into a
# physical length. CAMERA_DISTANCE_CM is the camera-to-road distance.
#
# ASSUMPTION: FOCAL_PX is NOT calibrated for any specific camera. Severity is
# therefore a consistent *relative* ranking across frames from the same camera,
# not a true physical measurement. Calibrate FOCAL_PX per camera to make the
# centimetre values meaningful.
CAMERA_DISTANCE_CM = float(os.environ.get("CAMERA_DISTANCE_CM", 90))
FOCAL_PX = float(os.environ.get("FOCAL_PX", 800))

# A pothole this long (cm) or longer scores the maximum severity of 100.
MAX_LEN_CM = float(os.environ.get("MAX_LEN_CM", 100))

# Normalization bounds for the census-derived scores. result.proto documents
# every score field as 0-100, and the API casts them straight into an INTEGER
# column, so raw dollars and raw population counts cannot be sent as-is.
MAX_INCOME = 150000.0
MAX_POPULATION = 10000.0


def clamp_score(value) -> int:
    """Clamp any numeric score into the proto's documented 0-100 uint32 range."""
    if value is None:
        return 0
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def get_uuidv7() -> str:
    """UUIDv7 generator with a spec-correct fallback for Python < 3.14."""
    if hasattr(uuid, "uuid7"):
        return str(uuid.uuid7())

    # 48-bit big-endian millisecond timestamp + 74 random bits, with the
    # version (7) and RFC 4122 variant bits set in place.
    ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF
    raw = bytearray(ms.to_bytes(6, "big") + os.urandom(10))
    raw[6] = (raw[6] & 0x0F) | 0x70  # version 7
    raw[8] = (raw[8] & 0x3F) | 0x80  # variant 10xx
    return str(uuid.UUID(bytes=bytes(raw)))


def score_income(median_income) -> int:
    """Map a tract's median household income onto 0-100."""
    if not median_income:
        return 0
    return clamp_score(float(median_income) / MAX_INCOME * 100)


def score_density(population) -> int:
    """Map a tract's population onto 0-100 as a traffic-density proxy."""
    if not population:
        return 0
    return clamp_score(float(population) / MAX_POPULATION * 100)


def compute_overall(severity: int, density: int, income_score: int) -> int:
    """Combine the populated signals into a 0-100 repair-priority score.

    ASSUMPTION: income is inverted (100 - income_score) so that lower-income
    tracts rank *higher* on the repair-priority list. area_transit_ridership,
    area_gdp and area_commercial are always 0 today, so they are left out of the
    weights rather than diluting every score toward zero.
    """
    overall = 0.5 * severity + 0.3 * density + 0.2 * (100 - income_score)
    return clamp_score(overall)


def estimate_pothole_severity(image, camera_distance: float = CAMERA_DISTANCE_CM) -> dict:
    """Estimate pothole severity (0-100) from a BGR OpenCV frame.

    Returns {"severity_level", "length_cm", "length_px", "bbox"}.
    """
    empty = {"severity_level": 0, "length_cm": 0.0, "length_px": 0.0, "bbox": None}

    if SEVERITY_MODEL is None or image is None:
        return empty

    height, width = image.shape[:2]
    if height == 0 or width == 0:
        return empty

    # cv2.imdecode hands back BGR; the model was trained on RGB.
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (IMG_SIZE, IMG_SIZE))
    tensor_img = F.normalize(F.to_tensor(resized), MEAN, STD).unsqueeze(0)

    with torch.no_grad():
        prediction = SEVERITY_MODEL(tensor_img)

    bbox = prediction[0].detach().cpu().float()
    xmin, ymin, xmax, ymax = (float(v) for v in bbox)

    # The head may emit either normalized coords or pixel coords at IMG_SIZE.
    # Scale both cases back onto the original frame.
    if float(bbox.abs().max()) <= 1.5:
        scale_x, scale_y = width, height
    else:
        scale_x, scale_y = width / IMG_SIZE, height / IMG_SIZE

    xmin, xmax = xmin * scale_x, xmax * scale_x
    ymin, ymax = ymin * scale_y, ymax * scale_y

    length_px = max(ymax - ymin, 0.0)
    if length_px <= 0.0:
        return empty

    length_cm = (length_px * camera_distance) / FOCAL_PX
    severity = clamp_score(length_cm / MAX_LEN_CM * 100)

    return {
        "severity_level": severity,
        "length_cm": length_cm,
        "length_px": length_px,
        "bbox": [xmin, ymin, xmax, ymax],
    }


class VideoServiceServicer(video_pb2_grpc.VideoServiceServicer):

    def StreamFrames(self, request_iterator, context):
        frames_processed = 0

        for frame in request_iterator:
            frames_processed += 1

            # 1. Decode image bytes to OpenCV format
            np_arr = np.frombuffer(frame.data, dtype=np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if img is None:
                continue

            # 2. Run YOLO inference
            results = model(img, verbose=False)[0]
            boxes = results.boxes

            # 3. Only frames with a detection are worth enriching and queueing.
            if len(boxes) == 0:
                continue

            # 4. Enrich with census data and severity, normalized to 0-100.
            census_data = get_data_by_lat_lon(frame.latitude, frame.longitude)
            if "error" in census_data:
                print("Census lookup failed: " + str(census_data["error"]))
                census_data = {}

            income_score = score_income(census_data.get("median_household_income"))
            density_score = score_density(census_data.get("population"))
            severity = estimate_pothole_severity(img)["severity_level"]

            result_msg = result_pb2.ProcessingResult(
                uuidv7=get_uuidv7(),
                timestamp=int(frame.timestamp) & 0xFFFFFFFF,  # Clamp to uint32 max
                data=frame.data,
                latitude=frame.latitude,
                longitude=frame.longitude,
                overall_score=compute_overall(severity, density_score, income_score),
                area_transit_ridership=0,  # no data source yet
                area_gdp=0,  # no data source yet
                area_income=income_score,
                area_commercial=0,  # no data source yet
                traffic_density=density_score,
                pothole_severity=severity,
            )

            # 5. Push result to queue for downstream consumption
            RESULT_QUEUE.put(result_msg)

        return video_pb2.StreamResponse(frames_received=frames_processed)


class ProcessingServiceServicer(result_pb2_grpc.ProcessingServiceServicer):

    def StreamResults(self, request, context):
        while context.is_active():
            try:
                item = RESULT_QUEUE.get(timeout=1.0)

                # End of Stream signal (Sentinel check)
                if item is None:
                    break

                yield item

            except queue.Empty:
                continue
            except (grpc.RpcError, GeneratorExit):
                # Handle client disconnection during yield cleanly
                break


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Bind both original services to the server
    video_pb2_grpc.add_VideoServiceServicer_to_server(
        VideoServiceServicer(), server
    )
    result_pb2_grpc.add_ProcessingServiceServicer_to_server(
        ProcessingServiceServicer(), server
    )

    server.add_insecure_port("[::]:8000")
    print("gRPC Video Processing Server listening on port 8000...")
    server.start()
    server.wait_for_termination()


def get_data_by_lat_lon(lat, lon, api_key="a9bf4bb4a132bfcfb283de32039ffaf8065ef7da"):
    # Step A: Reverse Geocode Lat/Lon to Census Tract
    geo_url = (
        f"https://geocoding.geo.census.gov/geocoder/geographies/coordinates?"
        f"x={lon}&y={lat}&benchmark=Public_AR_Current&vintage=Current_Current&format=json"
    )

    try:
        geo_resp = requests.get(geo_url).json()
    except Exception as e:
        return {"error": f"Geocoder request failed: {e}"}

    # Check if any tract was returned
    tracts = geo_resp.get("result", {}).get("geographies", {}).get("Census Tracts", [])
    if not tracts:
        return {"error": "Coordinates did not resolve to a US Census Tract."}

    tract_info = tracts[0]

    # Extract FIPS components with fallbacks to GEOID parsing (SSCCCTTTTTT)
    geoid = tract_info.get("GEOID", "")
    state = str(tract_info.get("STATE") or (geoid[:2] if len(geoid) >= 2 else "")).zfill(2)
    county = str(tract_info.get("COUNTY") or (geoid[2:5] if len(geoid) >= 5 else "")).zfill(3)
    tract = str(tract_info.get("TRACT") or (geoid[5:11] if len(geoid) >= 11 else "")).zfill(6)

    if not (state and county and tract):
        return {"error": "Could not parse valid State, County, or Tract FIPS codes."}

    # Step B: Fetch ACS Data for the Tract
    acs_url = (
        f"https://api.census.gov/data/2022/acs/acs5?"
        f"get=NAME,B01003_001E,B19113_001E&for=tract:{tract}&in=state:{state}&in=county:{county}"
    )
    if api_key:
        acs_url += f"&key={api_key}"

    try:
        acs_resp = requests.get(acs_url)
    except Exception as e:
        return {"error": f"ACS request failed: {e}"}

    if acs_resp.status_code != 200:
        return {"error": f"ACS API Error ({acs_resp.status_code}): {acs_resp.text}"}

    acs_data = acs_resp.json()
    if len(acs_data) < 2:
        return {"error": "No ACS data found for this tract."}

    values = acs_data[1]

    return {
        "tract_name": values[0],
        "population": int(values[1]) if values[1] else None,
        "median_household_income": int(values[2]) if values[2] else None
    }


if __name__ == "__main__":
    serve()
