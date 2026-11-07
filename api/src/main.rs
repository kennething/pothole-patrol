#[macro_use]
extern crate rocket;

use rocket::{ fairing::AdHoc, http::Status, Rocket, Orbit };
use rocket_db_pools::Database;
use sqlx::{Pool, Postgres};
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

  rocket
    ::build()
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
    .mount("/pothole", routes![routes::pothole::Area])
}
