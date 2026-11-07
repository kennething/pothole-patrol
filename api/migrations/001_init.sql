CREATE TABLE entries (
    uuid TEXT UNIQUE PRIMARY KEY,
    timestamp INTEGER NOT NULL,

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    overall_score INTEGER NOT NULL,
    area_transit_ridership INTEGER NOT NULL,
    area_gdp INTEGER NOT NULL,
    area_income INTEGER NOT NULL,
    area_commercial INTEGER NOT NULL,
    traffic_density INTEGER NOT NULL,
    pothole_severity INTEGER NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_entries_timestamp
    ON entries (timestamp);

CREATE INDEX idx_entries_latitude_longitude
    ON entries (latitude, longitude);
