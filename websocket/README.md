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

4. Create a `.env` file in this directory with the following content:

   ```sh
   CAMERA_URL=https://<ip>:3000 # url of the camera stream
   BACKEND_URL=https://<ip>:8000 # url of the model backend server
   ```

   where `<ip>` is your local network IP address.

5. Run the server:

   ```sh
   bun run serve
   ```
