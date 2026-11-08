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


# Import generated modules from both original proto files
import result_pb2
import result_pb2_grpc
import video_pb2
import video_pb2_grpc


import numpy as np
import torch
from PIL import Image
from torchvision.transforms import functional as F


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

      model = YOLO("yolov8n.pt")
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
        q = STREAM_QUEUES.get(request.stream_id)

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
    """Estimates the depth/severity metric of pothole(s) from an input image.


    Parameters:
        image_input (str | PIL.Image.Image | np.ndarray): File path, PIL Image,
          or NumPy OpenCV array.
        model_path (str): Path to the trained PyTorch model checkpoint.
        camera_distance (float): Camera distance from ground in centimeters
          (default: 90 cm).


    Returns:
        dict: Output containing calculated depth metric, detection count, and
        severity classification.
    """
    # 1. Load and convert image to RGB PIL Image
    if isinstance(image_input, str):
        image = Image.open(image_input).convert("RGB")
    elif isinstance(image_input, np.ndarray):
        # Convert BGR OpenCV array to RGB PIL Image
        image = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
    elif isinstance(image_input, Image.Image):
        image = image_input.convert("RGB")
    else:
        raise ValueError(
            "Unsupported input format. Provide a file path, PIL Image, or NumPy array."
        )


    # 2. Preprocess image into tensor
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    tensor_image = F.to_tensor(cv_image).unsqueeze(0)


    # 3. Load model and set to evaluation mode
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = YOLO(model_path)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()

    # 4. Perform model inference
    with torch.no_grad():
        pred_bboxes = model(tensor_image.to(device))


    # Handle edge case where no potholes are detected
    if pred_bboxes is None or len(pred_bboxes) == 0:
        return {
            "severity_level": "None",
            "average_depth_metric": 0.0,
            "detected_count": 0,
        }


    # 5. Calculate focal depth metric for each detected bounding box
    perceived_depths = []
    for bbox in pred_bboxes:
        # Bounding box format: [xmin, ymin, xmax, ymax]
        xmin, ymin, xmax, ymax = bbox[0], bbox[1], bbox[2], bbox[3]
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


    # 6. Classify severity based on calculated depth metric
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

