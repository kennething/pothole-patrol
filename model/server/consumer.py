import grpc
import result_pb2
import result_pb2_grpc


def listen():
  channel = grpc.insecure_channel("localhost:50051")
  stub = result_pb2_grpc.ProcessingServiceStub(channel)

  print("Listening for stream_001 results...")
  request = result_pb2.StreamRequest(stream_id="stream_001")
  results = stub.StreamResults(request)

  for res in results:
    status_str = "FOUND" if res.overall_score == 0 else "NOT FOUND"
    print(
        f"[CONSUMER] UUIDv7: {res.uuidv7} | Frame Time: {res.timestamp}s |"
        f" Status: {res.overall_score} ({status_str}) | Objects:"
        f" {res.traffic_density}"
    )


if __name__ == "__main__":
  listen()