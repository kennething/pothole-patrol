use rocket_db_pools::Connection;
use rocket::serde::Serialize;

use crate::utils::db::Db;

#[derive(Serialize)]
#[serde(crate = "rocket::serde", rename_all = "camelCase")]
pub struct SerializedEntry {}

pub struct Entry {}
impl Entry {
  pub fn new() -> Self {
    Self {}
  }

  pub async fn serialize(&self, db: &mut Connection<Db>) -> SerializedEntry {
    SerializedEntry {}
  }
}
