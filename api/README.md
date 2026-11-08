# API & Database Backend

Receives data via gRPC from the model backend and stores it in a SQLite database
for serving to the dashboard frontend with Rocket.rs.

## Setup Instructions

1. Make sure Rust and Cargo are installed on your machine.

2. Select this directory:

   ```sh
   cd api
   ```

3. Install `watchexec` for hot reloading:

   ```sh
   cargo install --locked watchexec-cli
   ```

4. Create a `.env` in the root of this directory with the following content:

   ```sh
   GRPC_SERVER_URL=http://localhost:8000
   STREAM_ID= # a unique id for this stream
   ```

5. Run the server:

   ```sh
   watchexec -r -e rs -- "cargo run --bin backend"
   ```
