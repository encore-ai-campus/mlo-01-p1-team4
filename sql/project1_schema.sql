CREATE DATABASE IF NOT EXISTS project1
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE project1;

CREATE TABLE IF NOT EXISTS car_listing (
    car_id            INT         PRIMARY KEY,
    region            VARCHAR(50) NOT NULL,
    sub_region        VARCHAR(50) NOT NULL,
    brand             VARCHAR(50) NOT NULL,
    model_year        INT         NOT NULL,
    fuel_type         VARCHAR(30) NOT NULL,
    mileage_km        INT         NOT NULL,
    price_krw         INT         NOT NULL,
    status            VARCHAR(20) NOT NULL,
    registration_date DATE        NOT NULL
) ENGINE=InnoDB;

CREATE INDEX idx_car_search
    ON car_listing (region, sub_region, brand, model_year);
