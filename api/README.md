# API & Database Backend

Receives data via gRPC from the model backend and stores it in a PostgreSQL
database for serving to the dashboard frontend with Rocket.rs.

## Setup Instructions

1. Make sure Rust, Cargo, and Docker are installed on your machine.

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

5. Create and run the database:

   ```sh
   docker run --name rocket-postgres \
   -e POSTGRES_USER=user \
   -e POSTGRES_PASSWORD=password \
   -e POSTGRES_DB=db \
   -p 9101:5432 \
   -d postgres:17
   ```

6. Run the server:

   ```sh
   watchexec -r -e rs -- "cargo run --bin backend"
   ```

## Accessing the Database

Run the following command to access the database:

```sh
docker exec -it rocket-postgres psql -U user -d db
```
