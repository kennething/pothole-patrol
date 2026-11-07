use rocket_db_pools::sqlx::{ self, sqlite::SqliteRow, Row, Sqlite };

pub fn get_from_row<'a, T: sqlx::Decode<'a, Sqlite> + sqlx::Type<Sqlite>>(row: &'a SqliteRow, column: &str) -> T {
  row.try_get::<T, _>(column).unwrap()
}
