from concurrent import futures
from functools import lru_cache
import os
import queue
import threading
import time
import uuid
from typing import Optional

import cv2
import grpc
import numpy as np
import requests
import torch
from dotenv import load_dotenv
from torchvision.transforms import functional as F
from ultralytics import YOLO

# Import generated modules from both original proto files
import result_pb2
import result_pb2_grpc
import video_pb2
import video_pb2_grpc

from model import IMG_SIZE, MEAN, STD, load_pothole_model

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY")


# Every active StreamResults call registers its own queue here, and each result
# is copied into all of them.
#
# A single shared queue does NOT work: queue.Queue is competing-consumer, so two
# subscribers split the stream between them instead of each receiving every
# result. The API reconnects every 3s (api/src/utils/grpc.rs subscribe()), and a
# stale generator still parked in get() would win items from the live one and
# drop them -- results the server believed it had sent.
#
# NOTE: request.stream_id is deliberately ignored, i.e. this is a broadcast.
# websocket/app.ts sends `streamId: socket.id` (random per connection) while
# api/src/main.rs subscribes with a fixed STREAM_ID env var, so those two ids can
# never match and routing by stream_id would deliver nothing.
SUBSCRIBERS = set()
SUBSCRIBERS_LOCK = threading.Lock()

# Per-subscriber queue bound. A slow or dead subscriber must never grow memory
# without limit -- each queued message holds a full JPEG frame (~330 KB).
RESULT_QUEUE_MAX = int(os.environ.get("RESULT_QUEUE_MAX", 256))

# Baseline: 10,000+ establishments = 100 score
MAX_ESTABLISHMENTS = 10000.0

# Results dropped because no subscriber was attached, or because a subscriber's
# queue overflowed. Printed on drop so the condition is visible in the logs.
DROPPED_RESULTS = 0

# Detection model. Loaded once at import; reloading it per frame reads the
# weights off disk for every single frame.
#
# POTHOLE_MODEL_PATH should point at a pothole-trained YOLO checkpoint. The
# stock COCO yolov8n is only a fallback so the server still starts -- it has no
# pothole class, so with it loaded the gate below emits nothing (see
# DETECTOR_HAS_POTHOLE_CLASS).
POTHOLE_MODEL_PATH = os.environ.get("POTHOLE_MODEL_PATH", "pothole.pt")
if not os.path.exists(POTHOLE_MODEL_PATH):
    print(
        f"WARNING: no pothole detector at {POTHOLE_MODEL_PATH}; "
        "falling back to stock COCO yolov8n.pt"
    )
    POTHOLE_MODEL_PATH = "yolov8n.pt"
model = YOLO(POTHOLE_MODEL_PATH)

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

# Only frames that actually contain a pothole are streamed downstream.
#
# Three gates, all of which a frame must pass:
#   1. POTHOLE_CLASSES -- the detector must report a box whose class name is one
#      of these. This is an allowlist with NO permissive fallback: a frame
#      containing only a person or a car is not a pothole frame and is dropped.
#   2. MIN_CONFIDENCE -- that box's confidence must reach this threshold, so a
#      marginal guess does not become a reported pothole.
#   3. MIN_SEVERITY -- the severity model must report at least this score, which
#      drops frames where the regressor finds no meaningful pothole extent.
POTHOLE_CLASSES = [
    name.strip().lower()
    for name in os.environ.get("POTHOLE_CLASSES", "pothole,potholes,pot-hole").split(",")
    if name.strip()
]
MIN_CONFIDENCE = float(os.environ.get("MIN_CONFIDENCE", 0.35))
MIN_SEVERITY = int(os.environ.get("MIN_SEVERITY", 1))

# Does the loaded detector actually know any of the pothole classes? Checked
# once at import so the operator sees the problem at startup rather than
# wondering why the stream is silent.
DETECTOR_CLASS_NAMES = {
    str(name).lower() for name in (getattr(model, "names", None) or {}).values()
}
DETECTOR_HAS_POTHOLE_CLASS = bool(DETECTOR_CLASS_NAMES & set(POTHOLE_CLASSES))
if not DETECTOR_HAS_POTHOLE_CLASS:
    print(
        f"WARNING: detector {POTHOLE_MODEL_PATH} has no class in {POTHOLE_CLASSES} "
        f"(it knows {sorted(DETECTOR_CLASS_NAMES)[:8]}...). NO results will be "
        "emitted. Load a pothole-trained checkpoint via POTHOLE_MODEL_PATH, or "
        "set POTHOLE_CLASSES to the class names it does use."
    )

# Duplicate suppression. Without this, a camera sitting at one pothole at 30fps
# emits ~30 results per second for the same hole, each with a fresh uuidv7 -- so
# the `uuid UNIQUE` constraint in the API's schema cannot collapse them either.
#
# Frames are bucketed into a grid cell by rounding their coordinates, and a cell
# may emit at most once per DEDUP_WINDOW_S. DEDUP_PRECISION=4 is ~11m at NYC
# latitudes. Set DEDUP_WINDOW_S=0 to disable suppression entirely.
DEDUP_PRECISION = int(os.environ.get("DEDUP_PRECISION", 4))
DEDUP_WINDOW_S = float(os.environ.get("DEDUP_WINDOW_S", 10))
RECENT_EMISSIONS = {}
RECENT_EMISSIONS_LOCK = threading.Lock()

# The Census API returns large negative sentinels (e.g. -666666666) instead of
# null when a tract has no estimate for a variable.
CENSUS_NULL_THRESHOLD = 0

# The census lookup makes two blocking HTTP calls. Without a timeout a hung
# request pins a gRPC worker forever.
CENSUS_TIMEOUT_S = float(os.environ.get("CENSUS_TIMEOUT_S", 5))

# Each live stream (camera or subscriber) holds one worker for its entire
# lifetime, so this must exceed cameras + subscribers -- it is not a request
# rate. The old value of 10 starved once a few streams were connected.
GRPC_MAX_WORKERS = int(os.environ.get("GRPC_MAX_WORKERS", 32))

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


def subscribe_queue() -> queue.Queue:
    """Register a queue to receive every subsequent result."""
    q = queue.Queue(maxsize=RESULT_QUEUE_MAX)
    with SUBSCRIBERS_LOCK:
        SUBSCRIBERS.add(q)
        count = len(SUBSCRIBERS)
    print(f"Subscriber attached ({count} active)")
    return q


def unsubscribe_queue(q: queue.Queue) -> None:
    """Deregister a queue so a finished stream stops consuming results."""
    with SUBSCRIBERS_LOCK:
        SUBSCRIBERS.discard(q)
        count = len(SUBSCRIBERS)
    print(f"Subscriber detached ({count} active)")


def publish(result_msg) -> None:
    """Copy one result into every subscriber's queue.

    With no subscribers the message is dropped rather than buffered: holding
    frames for a consumer that may never arrive is what let memory grow without
    bound and flooded the API with stale data when it finally connected.
    """
    global DROPPED_RESULTS

    with SUBSCRIBERS_LOCK:
        targets = list(SUBSCRIBERS)

    if not targets:
        DROPPED_RESULTS += 1
        print(f"No subscribers; dropped result (total dropped: {DROPPED_RESULTS})")
        return

    for q in targets:
        try:
            q.put_nowait(result_msg)
        except queue.Full:
            # Drop this subscriber's oldest result to make room, so a slow
            # consumer falls behind instead of blocking the frame loop.
            try:
                q.get_nowait()
            except queue.Empty:
                pass
            DROPPED_RESULTS += 1
            print(f"Subscriber queue full; dropped oldest (total dropped: {DROPPED_RESULTS})")
            try:
                q.put_nowait(result_msg)
            except queue.Full:
                pass


def should_emit(latitude: float, longitude: float) -> bool:
    """True if this location has not already been reported recently.

    Buckets coordinates into a grid cell and allows one emission per cell per
    DEDUP_WINDOW_S. Expired cells are pruned on each call so the map cannot grow
    without bound over a long run.
    """
    if DEDUP_WINDOW_S <= 0:
        return True

    cell = (round(latitude, DEDUP_PRECISION), round(longitude, DEDUP_PRECISION))
    now = time.monotonic()

    with RECENT_EMISSIONS_LOCK:
        for key, seen_at in list(RECENT_EMISSIONS.items()):
            if now - seen_at > DEDUP_WINDOW_S:
                del RECENT_EMISSIONS[key]

        last_seen = RECENT_EMISSIONS.get(cell)
        if last_seen is not None and now - last_seen <= DEDUP_WINDOW_S:
            return False

        RECENT_EMISSIONS[cell] = now
        return True


def census_value(value):
    """Return a usable census number, or None for a missing/sentinel value.

    The ACS API encodes "no estimate" as a large negative number rather than
    null, and those must not be read as "this tract earns nothing" -- doing so
    would push unmeasured tracts to the top of the repair-priority list.
    """
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > CENSUS_NULL_THRESHOLD else None


def score_income(median_income) -> int:
    """Map a tract's median household income onto 0-100."""
    income = census_value(median_income)
    if income is None:
        return 0
    return clamp_score(income / MAX_INCOME * 100)


def score_density(population) -> int:
    """Map a tract's population onto 0-100 as a traffic-density proxy."""
    people = census_value(population)
    if people is None:
        return 0
    return clamp_score(people / MAX_POPULATION * 100)


def compute_overall(severity: int, density: int, income_score: int, commercial: int) -> int:
    """Combine the populated signals into a 0-100 repair-priority score.

    ASSUMPTION: income is inverted (100 - income_score) so that lower-income
    tracts rank *higher* on the repair-priority list. area_transit_ridership,
    area_gdp and area_commercial are always 0 today, so they are left out of the
    weights rather than diluting every score toward zero.
    """
    overall = 0.5 * severity + 0.3 * density + 0.2 * (100 - income_score) + 0.1 * commercial
    return clamp_score(overall)


def has_pothole(results) -> bool:
    """True only when the detector found a pothole box in this frame.

    Strict allowlist: the box's class name must be in POTHOLE_CLASSES and its
    confidence must reach MIN_CONFIDENCE. There is deliberately no "any
    detection counts" fallback -- that let frames of people and cars through as
    if they were potholes.
    """
    boxes = results.boxes
    if boxes is None or len(boxes) == 0:
        return False

    names = results.names or {}
    class_ids = boxes.cls.tolist()
    confidences = boxes.conf.tolist() if boxes.conf is not None else [1.0] * len(class_ids)

    for class_id, confidence in zip(class_ids, confidences):
        label = str(names.get(int(class_id), class_id)).lower()
        if label in POTHOLE_CLASSES and confidence >= MIN_CONFIDENCE:
            return True
    return False


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

            # 3. Gate: nothing leaves this server unless a pothole was found.
            if not has_pothole(results):
                continue

            # 4. Second gate: the severity model must agree there is a pothole
            #    of meaningful extent. Computed before the census lookup so a
            #    rejected frame costs no network round trip.
            severity = estimate_pothole_severity(img)["severity_level"]
            if severity < MIN_SEVERITY:
                continue

            # 5. Suppress repeats of a pothole already reported from this spot.
            #    Checked before the census lookup so a suppressed frame costs no
            #    network round trip.
            if not should_emit(frame.latitude, frame.longitude):
                continue

            # 6. Enrich with census data, normalized to 0-100.
            census_data = census_for_location(frame.latitude, frame.longitude)
            if "error" in census_data:
                print("Census lookup failed: " + str(census_data["error"]))
                census_data = {}

            income_score = score_income(census_data.get("median_household_income"))
            density_score = score_density(census_data.get("population"))
            commercial_data = get_area_commercial_by_lat_lon(frame.latitude, frame.longitude)["area_commercial_score"]
            result_msg = result_pb2.ProcessingResult(
                uuidv7=get_uuidv7(),
                timestamp=int(frame.timestamp) & 0xFFFFFFFF,  # Clamp to uint32 max
                data=frame.data,
                latitude=frame.latitude,
                longitude=frame.longitude,
                overall_score=compute_overall(severity, density_score, income_score, commercial_data),
                area_transit_ridership=0,  # no data source yet
                area_gdp=0,  # no data source yet
                area_income=income_score,
                area_commercial=commercial_data,
                traffic_density=density_score,
                pothole_severity=severity,
            )

            # 7. Hand the result to every attached subscriber
            publish(result_msg)

        return video_pb2.StreamResponse(frames_received=frames_processed)


class ProcessingServiceServicer(result_pb2_grpc.ProcessingServiceServicer):

    def StreamResults(self, request, context):
        # This stream's own queue. Registered for the life of the call and
        # always removed in the finally, so a client that disconnects (the API
        # reconnects every 3s) cannot leave a generator behind that keeps
        # consuming results nobody will read.
        q = subscribe_queue()

        try:
            while context.is_active():
                try:
                    item = q.get(timeout=1.0)
                except queue.Empty:
                    continue

                # End of Stream signal (Sentinel check)
                if item is None:
                    break

                try:
                    print(item)
                    yield item
                except (grpc.RpcError, GeneratorExit):
                    # The item is already off the queue at this point. Put it
                    # back so a disconnect mid-send does not destroy a result.
                    try:
                        q.put_nowait(item)
                    except queue.Full:
                        pass
                    raise
        except (grpc.RpcError, GeneratorExit):
            # Client disconnected; nothing more to do.
            pass
        finally:
            unsubscribe_queue(q)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=GRPC_MAX_WORKERS))

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


def census_for_location(lat, lon) -> dict:
    """Census lookup for a frame, cached by grid cell.

    Consecutive frames come from nearly the same spot and resolve to the same
    tract, so calling the API per frame made two blocking HTTP round trips for
    an answer that had not changed. Rounding to the dedup grid before caching
    collapses those to one call per cell.
    """
    return _census_for_cell(
        round(float(lat), DEDUP_PRECISION),
        round(float(lon), DEDUP_PRECISION),
    )


@lru_cache(maxsize=1024)
def _census_for_cell(lat: float, lon: float) -> dict:
    # NOTE: lru_cache stores failures too. That is deliberate -- it stops a dead
    # or rate-limited census API from being hammered once per frame. Restart the
    # server (or clear the cache) to retry a cell that errored.
    return get_data_by_lat_lon(lat, lon)


def get_data_by_lat_lon(lat, lon, api_key=None):
    if api_key is None:
        api_key = CENSUS_API_KEY

    # Step A: Reverse Geocode Lat/Lon to Census Tract
    geo_url = (
        f"https://geocoding.geo.census.gov/geocoder/geographies/coordinates?"
        f"x={lon}&y={lat}&benchmark=Public_AR_Current&vintage=Current_Current&format=json"
    )

    try:
        geo_resp = requests.get(geo_url, timeout=CENSUS_TIMEOUT_S).json()
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
        acs_resp = requests.get(acs_url, timeout=CENSUS_TIMEOUT_S)
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

def get_area_commercial_by_lat_lon(lat: float, lon: float, api_key: Optional[str] = None) -> dict:
    if api_key is None:
        api_key = CENSUS_API_KEY

    # -------------------------------------------------------------------------
    # Step 1: Reverse Geocode (lat, lon) -> State (2-digit) & County (3-digit)
    # Note: Census Geocoder expects x=longitude, y=latitude
    # -------------------------------------------------------------------------
    geo_url = (
        f"https://geocoding.geo.census.gov/geocoder/geographies/coordinates?"
        f"x={lon}&y={lat}&benchmark=Public_AR_Current&vintage=Current_Current&format=json"
    )

    try:
        geo_resp = requests.get(geo_url, timeout=3.0).json()
        tracts = geo_resp.get("result", {}).get("geographies", {}).get("Census Tracts", [])
        if not tracts:
            return {"total_establishments": 0, "area_commercial_score": 0, "error": "Location outside US or unmapped area"}

        tract_info = tracts[0]
        geoid = tract_info.get("GEOID", "")
        state = str(tract_info.get("STATE") or (geoid[:2] if len(geoid) >= 2 else "")).zfill(2)
        county = str(tract_info.get("COUNTY") or (geoid[2:5] if len(geoid) >= 5 else "")).zfill(3)
    except Exception as error:
        return {"total_establishments": 0, "area_commercial_score": 0, "error": f"Geocoder failed: {error}"}

    # -------------------------------------------------------------------------
    # Step 2: Query County Business Patterns API using extracted FIPS
    # -------------------------------------------------------------------------
    cbp_url = f"https://api.census.gov/data/2023/cbp?get=ESTAB,NAME&for=county:{county}&in=state:{state}"
    if api_key:
        cbp_url += f"&key={api_key}"

    try:
        cbp_resp = requests.get(cbp_url, timeout=3.0)
        if cbp_resp.status_code == 200:
            data = cbp_resp.json()
            if len(data) >= 2:
                total_estab = int(data[1][0])
                score = max(0, min(100, int(round((total_estab / MAX_ESTABLISHMENTS) * 100))))
                
                return {
                    "state": state,
                    "county": county,
                    "total_establishments": total_estab,
                    "area_commercial_score": score
                }
    except Exception as error:
        return {"total_establishments": 0, "area_commercial_score": 0, "error": f"CBP lookup failed: {error}"}

    return {"total_establishments": 0, "area_commercial_score": 0}

if __name__ == "__main__":
    serve()
