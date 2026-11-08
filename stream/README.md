# Camera Stream

Uses Nuxt 4 and Socket.IO to establish a websocket connection with the backend
and stream video from a phone's camera.

Serves as a standin for a dashcam, road camera, or any other camera that can
stream video to a server.

## Setup Instructions

1. Ensure Bun is installed on your machine.

2. Select this directory:

   ```sh
   cd stream
   ```

3. Install dependencies:

   ```sh
   bun install
   ```

4. Create a `.env` in the root of this directory with the following content:

   ```sh
   NUXT_PUBLIC_BACKEND_URL=http://localhost:9000
   ```

5. Run the development server:

   ```sh
   bun dev
   ```
