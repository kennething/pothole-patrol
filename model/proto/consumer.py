import grpc
import result_pb2
import result_pb2_grpc


def listen_results():
  channel = grpc.insecure_channel("localhost:50051")
  stub = result_pb2_grpc.ProcessingServiceStub(channel)

  request = result_pb2.StreamRequest(stream_id="stream_001")
  results = stub.StreamResults(request)

  for res in results:
    status_str = "FOUND" if res.overall_score == 0 else "NOT FOUND"
    print(
        f"Stream: {res.stream_id} | Time: {res.timestamp} | Status:"
        f" {res.overall_score} ({status_str}) | Objects Detected:"
        f" {res.traffic_density}"
    )


if __name__ == "__main__":
  listen_results()