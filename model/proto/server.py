from concurrent import futures
import grpc
import video_pb2
import video_pb2_grpc


class VideoServiceServicer(video_pb2_grpc.VideoServiceServicer):

  def StreamFrames(self, request_iterator, context):
    frames_processed = 0

    for frame in request_iterator:
      frames_processed += 1
      print(
          f"Received frame #{frames_processed} (ID: {frame.stream_id},"
          f" Seq: {frame.sequence}, Bytes: {len(frame.data)})"
      )

    print(f"Stream closed by client. Total received: {frames_processed}")
    return video_pb2.StreamResponse(frames_received=frames_processed)


def serve():
  server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
  video_pb2_grpc.add_VideoServiceServicer_to_server(
      VideoServiceServicer(), server
  )
  server.add_insecure_port("[::]:50051")
  print("Minimal Video Server running on port 50051...")
  server.start()
  server.wait_for_termination()


if __name__ == "__main__":
  serve()