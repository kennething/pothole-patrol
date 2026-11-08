import { ClientToServerEvents, ServerToClientEvents, InterServerEvents, SocketData } from "./utils/events";
import { createGrpcStream } from "./utils/grpc";
import { createServer } from "http";
import { Server } from "socket.io";
import express from "express";
import cors from "cors";
import "dotenv/config";

if (!process.env.CAMERA_URL || !process.env.GRPC_SERVER_URL) {
  console.error("missing CAMERA_URL or GRPC_SERVER_URL");
  process.exit(1);
}

process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
const MAX_IMAGE_SIZE = 5_000_000;

const app = express();
app.use(cors()).use(express.json());

const server = createServer(app);
const io = new Server<ClientToServerEvents, ServerToClientEvents, InterServerEvents, SocketData>(server, {
  cors: {
    origin: process.env.CAMERA_URL
  },
  maxHttpBufferSize: MAX_IMAGE_SIZE
});

io.on("connection", (socket) => {
  const grpcStream = createGrpcStream();
  grpcStream.on("error", (error) => console.error("gRPC stream error:", error));

  let sequence = 0;

  socket.on("sendFrame", (frame, metadata, callback) => {
    if (!Buffer.isBuffer(frame) || frame.length > MAX_IMAGE_SIZE) return callback(new Error("Invalid frame"));

    const accepted = grpcStream.write({
      data: frame,
      timestamp: metadata.timestamp,
      latitude: metadata.latitude ?? 0,
      longitude: metadata.longitude ?? 0,
      sequence: sequence++,
      streamId: socket.id
    });

    console.log(accepted, sequence);
    if (accepted) return callback(null);
    // TODO: handle backpressure properly
    grpcStream.once("drain", () => callback(null));
  });

  socket.on("disconnect", () => grpcStream.end());
});

const port = Number(process.env.PORT) || 9000;
server.listen(port, "0.0.0.0", () => console.log(`Server is up on port ${port}`));
