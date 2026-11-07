type CallbackFn<T = string> = (success: boolean, data?: T) => void;

export interface ServerToClientEvents {}

export interface ClientToServerEvents {}

export interface InterServerEvents {}

export interface SocketData {}
