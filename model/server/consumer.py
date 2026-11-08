import os

import grpc
import result_pb2
import result_pb2_grpc

# Must match the port server.py binds (see server.add_insecure_port) and the
# GRPC_SERVER_URL used by websocket/utils/grpc.ts and api/src/main.rs.
GRPC_SERVER_URL = os.environ.get("GRPC_SERVER_URL", "localhost:8000").removeprefix(
    "http://"
).removeprefix("https://")


def listen():
  channel = grpc.insecure_channel(GRPC_SERVER_URL)
  stub = result_pb2_grpc.ProcessingServiceStub(channel)

  print(f"Listening for stream_001 results on {GRPC_SERVER_URL}...")
  request = result_pb2.StreamRequest(stream_id="stream_001")
  results = stub.StreamResults(request)

  for res in results:
    print(
        f"[CONSUMER] UUIDv7: {res.uuidv7} | Frame Time: {res.timestamp}ms |"
        f" Overall: {res.overall_score} | Severity: {res.pothole_severity} |"
        f" Density: {res.traffic_density} | Income: {res.area_income}"
    )


if __name__ == "__main__":
  listen()
