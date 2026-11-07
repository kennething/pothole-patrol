import { ClientToServerEvents, ServerToClientEvents, InterServerEvents, SocketData } from "./utils/events";
import { createServer } from "https";
import { Server } from "socket.io";
import express from "express";
import cors from "cors";
import "dotenv/config";

process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

const app = express();
app.use(cors()).use(express.json());

const server = createServer(app);
const io = new Server<ClientToServerEvents, ServerToClientEvents, InterServerEvents, SocketData>(server, { cors: {} });

io.on("connection", (socket) => {
  // socket.on("pollFrame", (blob) => events.pollFrame(io, socket, blob as unknown as ArrayBuffer));
  // socket.on("connectMainSocket", (callback) => events.connectMainSocket(socket, callback));
  // socket.on("pair", (code, callback) => events.pair(io, socket, code as UUID, callback));
  // socket.timeout(99_999_999).on("confirmPair", (callback) => socket.to(socket.data.uuid!).emit("pairingConfirmed", () => callback(true)));
  // socket.on("terminatePairing", () => events.terminatePairing(io, socket));
  // socket.timeout(99_999_999).on("joinQueue", (callback) => queue.push({ socket, callback }));
  // socket.timeout(99_999_999).on("confirmMatch", (callback) => events.confirmMatch(io, socket, callback as CallbackFn<string[]>));
});

const port = Number(process.env.PORT) || 9000;
server.listen(port, "0.0.0.0", () => console.log(`Server is up on port ${port}`));
