#[macro_use]
extern crate rocket;

use rocket_db_pools::Database;
use rocket::http::Status;

mod models;
mod routes;
mod utils;
mod db;

#[get("/")]
fn index() -> Status {
  Status::NotFound
}

#[launch]
fn rocket() -> _ {
  rocket::build().attach(db::db::Db::init()).mount("/", routes![index]).mount("/pothole", routes![routes::pothole::Area])
}
