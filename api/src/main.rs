#[macro_use]
extern crate rocket;

use rocket::{ fairing::AdHoc, http::{ Status, Method }, Rocket, Orbit };
use rocket_cors::{ AllowedHeaders, AllowedOrigins, CorsOptions };
use rocket_db_pools::Database;
use sqlx::{ Pool, Postgres };
use std::env;

mod models;
mod routes;
mod utils;

use crate::utils::db::Db;

pub mod result {
  tonic::include_proto!("result");
}

#[get("/")]
fn index() -> Status {
  Status::NotFound
}

#[launch]
fn rocket() -> _ {
  dotenvy::dotenv().ok();

  let cors: rocket_cors::Cors = CorsOptions::default()
    .allowed_origins(AllowedOrigins::some_exact(&[std::env::var("FRONTEND_URL").expect("FRONTEND_URL missing")]))
    .allowed_methods(vec![Method::Get, Method::Post, Method::Put, Method::Delete].into_iter().map(From::from).collect())
    .allowed_headers(AllowedHeaders::some(&["Authorization", "Accept", "Content-Type"]))
    .allow_credentials(true)
    .to_cors()
    .expect("Failed to create CORS fairing");

  rocket
    ::build()
    .attach(cors)
    .attach(Db::init())
    .attach(AdHoc::on_ignite("sqlx migrations", utils::migrations::run_migrations))
    .attach(
      AdHoc::on_liftoff("grpc subscriber", |rocket: &Rocket<Orbit>| {
        Box::pin(async move {
          let pool: Pool<Postgres> = rocket.state::<Db>().unwrap().0.clone();

          let grpc_url: String = env::var("GRPC_SERVER_URL").expect("GRPC_SERVER_URL missing");
          let stream_id: String = env::var("STREAM_ID").expect("STREAM_ID missing");

          tokio::spawn(async move {
            utils::grpc::subscribe(pool, grpc_url, stream_id).await;
          });
        })
      })
    )
    .mount("/", routes![index])
    .mount("/pothole", routes![routes::pothole::Area, routes::pothole::Detail])
}
