import cv2
import grpc
import video_pb2
import video_pb2_grpc


def frame_generator(video_file, stream_id):
  cap = cv2.VideoCapture(video_file)
  seq = 0
  while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
      break
    _, buffer = cv2.imencode(".jpg", frame)

    yield video_pb2.VideoFrame(
        data=buffer.tobytes(),
        timestamp=seq * 33,
        latitude=37.7749,
        longitude=-122.4194,
        sequence=seq,
        stream_id=stream_id,
    )
    seq += 1
  cap.release()


def send_video():
  channel = grpc.insecure_channel("localhost:8000")
  stub = video_pb2_grpc.VideoServiceStub(channel)
  response = stub.StreamFrames(frame_generator("test.mp4", "stream_001"))
  print(f"Server acknowledged receiving {response.frames_received} frames.")


if __name__ == "__main__":
  send_video()
