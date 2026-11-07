type CallbackFn = (error: Error | null) => void;

export interface ServerToClientEvents {}

export interface ClientToServerEvents {
  sendFrame: (
    blob: Blob,
    data: {
      timestamp: number;
      longitude: number | null;
      latitude: number | null;
    },
    callback: CallbackFn
  ) => void;
}

export interface InterServerEvents {}

export interface SocketData {}
