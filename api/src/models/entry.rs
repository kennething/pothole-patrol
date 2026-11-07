use rocket_db_pools::sqlx::{ self, SqliteConnection, sqlite::SqliteRow };
use crate::{ db::functions::get_from_row };
use rocket::serde::Serialize;

#[derive(Serialize)]
#[serde(crate = "rocket::serde", rename_all = "camelCase")]
pub struct SerializedEntry {}

pub struct Entry {}
impl Entry {
  pub fn new() -> Self {
    Self {}
  }

  pub async fn serialize(&self, db: &mut SqliteConnection) -> SerializedEntry {
    SerializedEntry {}
  }
}
