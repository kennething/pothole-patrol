use rocket_db_pools::{ sqlx::{ self, Row }, Database };

#[derive(Database)]
#[database("postgres")]
pub struct Db(pub sqlx::PgPool);

pub fn get_from_row<'a, T: sqlx::Decode<'a, sqlx::Postgres> + sqlx::Type<sqlx::Postgres>>(row: &'a sqlx::postgres::PgRow, column: &str) -> T {
  row.try_get::<T, _>(column).unwrap()
}
