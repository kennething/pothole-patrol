from concurrent import futures
from functools import lru_cache
import queue
import time
import uuid
from typing import List, Optional, Tuple, Dict, Any
import cv2
import grpc
import numpy as np
import requests
from ultralytics import YOLO
import torch
from PIL import Image
from torchvision.transforms import functional as F
from pathlib import Path

# Import generated modules from both original proto files
import result_pb2
import result_pb2_grpc
import video_pb2
import video_pb2_grpc


# Thread-safe queue mapping stream_id -> queue of ProcessingResult messages
STREAM_QUEUES = {}


# Initialize YOLO model
model = YOLO("yolov8n.pt")




def get_uuidv7() -> str:
  """Safe UUIDv7 generator supporting Python < 3.13."""
  if hasattr(uuid, "uuid7"):
    return str(uuid.uuid7())
  # Fallback implementation if running Python < 3.13
  ms = int(time.time() * 1000)
  rand = uuid.uuid4().hex
  return f"{ms:012x}-{rand[12:16]}-7{rand[17:20]}-{rand[20:]}"




class VideoServiceServicer(video_pb2_grpc.VideoServiceServicer):


  def StreamFrames(self, request_iterator, context):
    frames_processed = 0


    for frame in request_iterator:
      frames_processed += 1
      stream_id = frame.stream_id


      # 1. Decode image bytes to OpenCV format
      np_arr = np.frombuffer(frame.data, dtype=np.uint8)
      img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)


      if img is None:
        continue


      # 2. Run YOLO inference
      results = model(img, verbose=False)[0]
      boxes = results.boxes


      # 3. Target check: 0 if objects detected, 1 if none found (uint32 compatible)
      has_detections = len(boxes) > 0
      status_flag = 0 if has_detections else 1


      census_data = get_data_by_lat_lon(frame.latitude, frame.longitude)
      pothole_severity = estimate_pothole_severity(img)["severity_level"]
   
      # 4. Populate ProcessingResult message with uint32 safety checks
      result_msg = result_pb2.ProcessingResult(
          uuidv7=get_uuidv7(),
          timestamp=int(frame.timestamp) & 0xFFFFFFFF,  # Clamp to uint32 max
          latitude=frame.latitude,
          longitude=frame.longitude,
          overall_score=status_flag,  # 0 = found, 1 = not found
          area_transit_ridership=0,
          area_gdp=0,
          area_income=census_data.get("median_household_income", 0) or 0,
          area_commercial=0,
          traffic_density=census_data.get("population", 0) or 0,
          pothole_severity=pothole_severity,
      )


      # 5. Push result to queue for downstream consumption
      if stream_id not in STREAM_QUEUES:
        STREAM_QUEUES[stream_id] = queue.Queue()
      STREAM_QUEUES[stream_id].put(result_msg)


    return video_pb2.StreamResponse(frames_received=frames_processed)




class ProcessingServiceServicer(result_pb2_grpc.ProcessingServiceServicer):


  def StreamResults(self, request, context):
    # stream_id = request.stream_id


    # # Initialize queue if consumer connects before frames arrive
    # if stream_id not in STREAM_QUEUES:
    #   STREAM_QUEUES[stream_id] = queue.Queue()


    # q = STREAM_QUEUES[stream_id]

    # # Stream out queued results to subscriber
    # while context.is_active():
    #   try:
    #     item = q.get(timeout=1.0)
    #     yield item
    #   except queue.Empty:
    #     continue
    # def StreamResults(self, request, context):
    # stream_id = request.stream_id

    while context.is_active():
        # 1. Fetch current queue instance dynamically to avoid stale references
        q = STREAM_QUEUES.get(stream_id)
        if q is None:
            time.sleep(0.1)
            continue

        try:
            item = q.get(timeout=1.0)

            # 2. End of Stream signal (Sentinel check)
            if item is None:
                break

            yield item

        except queue.Empty:
            continue
        except (grpc.RpcError, GeneratorExit):
            # 3. Handle client disconnection during yield cleanly
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
       
    acs_resp = requests.get(acs_url)
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

def estimate_pothole_severity(
    image_input, model_path: str = "length_of_pothole.pt", camera_distance: float = 90.0
) -> dict:
    """Estimates pothole severity from an input image using Ultralytics YOLO."""
    
    # 1. Load model directly (Ultralytics auto-loads weights)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pothole_model = YOLO(model_path)

    # 2. Run inference directly on PIL/NumPy image
    results = pothole_model(image_input, device=device, verbose=False)[0]
    boxes = results.boxes

    # Handle case where no potholes are detected
    if boxes is None or len(boxes) == 0:
        return {
            "severity_level": "None",
            "average_depth_metric": 0.0,
            "detected_count": 0,
        }

    # 3. Extract bounding box coordinates [xmin, ymin, xmax, ymax]
    perceived_depths = []
    xyxy_boxes = boxes.xyxy.cpu().numpy()  # Extract coordinates tensor as NumPy array

    for bbox in xyxy_boxes:
        xmin, ymin, xmax, ymax = bbox[:4]
        length = float(ymax - ymin)
        width = float(xmax - xmin)

        if width > 0:
            perceived_focal_length = (length * camera_distance) / width
            perceived_depths.append(perceived_focal_length)

    if not perceived_depths:
        return {
            "severity_level": "None",
            "average_depth_metric": 0.0,
            "detected_count": 0,
        }

    avg_depth = float(np.mean(perceived_depths))

    # 4. Classify severity
    if avg_depth < 60.0:
        severity = "Minor"
    elif 60.0 <= avg_depth < 100.0:
        severity = "Moderate"
    else:
        severity = "Severe"

    return {
        "severity_level": severity,
        "average_depth_metric": round(avg_depth, 2),
        "detected_count": len(perceived_depths),
    }

if __name__ == "__main__":
  serve()

