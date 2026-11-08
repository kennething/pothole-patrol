# WebSocket Server

Uses Express and Socket.IO to establish a websocket connection with the camera
stream.

Forwards streamed video to the model backend via gRPC for processing.

## Setup Instructions

1. Ensure Bun is installed on your machine.

2. Select this directory:

   ```sh
   cd websocket
   ```

3. Install dependencies:

   ```sh
   bun install
   ```

4. Create a `.env` in the root of this directory with the following content:

   ```sh
   CAMERA_URL=http://localhost:3000
   GRPC_SERVER_URL=localhost:8000
   ```

5. Run the server:

   ```sh
   bun run serve
   ```
