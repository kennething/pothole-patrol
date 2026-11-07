import { io, type Socket } from "socket.io-client";
import { type Raw } from "vue";

export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig();
  const socket: Raw<Socket<ServerToClientEvents, ClientToServerEvents>> = markRaw(io(config.public.backendUrl, { autoConnect: false }));

  return { provide: { socket } };
});
