# Dashboard

Uses Next.js to serve a dashboard for viewing pothole data.

## Setup Instructions

1. Ensure Bun is installed on your machine.

2. Select this directory:

   ```sh
   cd dashboard
   ```

3. Install dependencies:

   ```sh
   bun install
   ```

4. Create a `.env` in the root of this directory with the following content:

   ```sh
   BACKEND_URL=http://localhost:9100
   ```

5. Run the development server:

   ```sh
   bun dev -- -p 3100
   ```
