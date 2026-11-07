use rocket::{ Build, Rocket };
use rocket_db_pools::Database;

use crate::utils::db::Db;

pub async fn run_migrations(rocket: Rocket<Build>) -> Rocket<Build> {
  let db: &Db = Db::fetch(&rocket).expect("Database pool not initialized");

  sqlx::migrate!("./migrations").run(&db.0).await.expect("Database migrations failed");

  rocket
}
