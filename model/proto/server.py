from concurrent import futures
import queue
import cv2
import grpc
import numpy as np
from ultralytics import YOLO
import uuid
# Import generated modules from both original proto files
import result_pb2
import result_pb2_grpc
import video_pb2
import video_pb2_grpc

# Thread-safe queue mapping stream_id -> queue of ProcessingResult messages
STREAM_QUEUES = {}

# Initialize YOLO model
model = YOLO("yolov8n.pt")


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
      results = model(img)[0]
      boxes = results.boxes

      # 3. Target check: 0 if objects detected, 1 if none found
      has_detections = len(boxes) > 0
      status_flag = 0 if has_detections else -1

      # 4. Populate ProcessingResult message
      result_msg = result_pb2.ProcessingResult(
          uuidv7=str(uuid.uuid7()),
          timestamp=frame.timestamp,
          latitude=frame.latitude,
          longitude=frame.longitude,
          overall_score=status_flag,  # 0 = found, -1 = not found
          area_transit_ridership=0,
          area_gdp=0,
          area_income=0,
          area_commercial=0,
          traffic_density=len(boxes) if has_detections else 0,
          pothole_severity=0,
      )

      # 5. Push result to queue for downstream consumption
      if stream_id not in STREAM_QUEUES:
        STREAM_QUEUES[stream_id] = queue.Queue()
      STREAM_QUEUES[stream_id].put(result_msg)

    return video_pb2.StreamResponse(frames_received=frames_processed)


class ProcessingServiceServicer(result_pb2_grpc.ProcessingServiceServicer):

  def StreamResults(self, request, context):
    stream_id = request.stream_id

    # Initialize queue if consumer connects before frames arrive
    if stream_id not in STREAM_QUEUES:
      STREAM_QUEUES[stream_id] = queue.Queue()

    q = STREAM_QUEUES[stream_id]

    # Stream out queued results to subscriber
    while context.is_active():
      try:
        # Non-blocking pull with timeout to maintain context checks
        item = q.get(timeout=1.0)
        yield item
      except queue.Empty:
        continue


def serve():
  server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

  # Bind both original services to the server
  video_pb2_grpc.add_VideoServiceServicer_to_server(
      VideoServiceServicer(), server
  )
  result_pb2_grpc.add_ProcessingServiceServicer_to_server(
      ProcessingServiceServicer(), server
  )

  server.add_insecure_port("[::]:50051")
  print("gRPC Video Processing Server listening on port 50051...")
  server.start()
  server.wait_for_termination()


if __name__ == "__main__":
  serve()