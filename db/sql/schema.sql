-- =============================================================================
-- Car Rental System — Reference Schema
-- Target:  MySQL 8.0+
-- Encoding: utf8mb4
--
-- Architecture: normalised operational tables + append-only event log
--
--   OPERATIONAL (mutable, normalised)
--     user            staff accounts
--     client          renters
--     vehicle         fleet
--     reservation     optional pre-booking (intent)
--     active_rental   vehicle currently out (fact in progress)
--
--   EVENT LOG (immutable, denormalised by design)
--     rental_event    one row per closed rental; full JSON snapshot
--
--   ARCHIVE (mutable, normalised, references event log)
--     rental_archive  closed rentals; joins for current data,
--                     links to rental_event for historical truth
--
--   ANCILLARY
--     blacklist       clients refused service
--     notification    outbound email audit trail
--
-- Conventions
--   • Every table has created_at / updated_at managed by MySQL triggers.
--   • Monetary values are DECIMAL(10,2) in EUR.
--   • Soft deletes via is_deleted + deleted_at on client and vehicle.
--   • Surrogate INT PKs everywhere; natural keys kept as UNIQUE columns.
--   • Boolean columns use TINYINT(1) (MySQL has no native BOOLEAN type,
--     but BOOLEAN is accepted as an alias and maps to TINYINT(1)).
--   • JSON columns require MySQL 8.0+.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- USER
-- Staff accounts. Surrogate PK so renaming a login does not cascade.
-- ---------------------------------------------------------------------------
CREATE TABLE `user` (
    id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,   -- bcrypt / argon2; never plain text
    role VARCHAR(30) NOT NULL DEFAULT 'agent',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_user PRIMARY KEY (id),
    CONSTRAINT uq_user_username UNIQUE (username),
    CONSTRAINT chk_user_role CHECK (role IN ('admin', 'agent'))
);


-- ---------------------------------------------------------------------------
-- CLIENT
-- People who rent vehicles.
-- Two address blocks: domestic (France) and foreign.
-- Soft delete: is_deleted + deleted_at — preserves FK integrity.
-- ---------------------------------------------------------------------------
CREATE TABLE client (
    id INT NOT NULL AUTO_INCREMENT,
    last_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NULL,
    nationality VARCHAR(50) NULL,

    -- Identity documents
    national_id VARCHAR(20) NULL,
    licence_number VARCHAR(30) NULL,
    licence_issued_on DATE NULL,
    passport_number VARCHAR(30) NULL,
    passport_issued_on DATE NULL,

    -- Domestic address (default country: France)
    address_line VARCHAR(200) NULL,
    city VARCHAR(100) NULL,
    postal_code VARCHAR(10) NULL,
    country VARCHAR(50) NOT NULL DEFAULT 'France',
    phone VARCHAR(20) NULL,

    -- Foreign address (for non-resident renters)
    foreign_address_line VARCHAR(200) NULL,
    foreign_city VARCHAR(100) NULL,
    foreign_country VARCHAR(50) NULL,
    foreign_phone VARCHAR(20) NULL,

    -- Contact / consent
    email VARCHAR(200) NULL,
    email_consent TINYINT(1) NOT NULL DEFAULT 0,

    -- Second driver flag; actual second driver identified in active_rental
    has_second_driver TINYINT(1) NOT NULL DEFAULT 0,

    photo_url VARCHAR(500) NULL,

    -- Soft delete
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    deleted_at DATETIME NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_client PRIMARY KEY (id)
);


-- ---------------------------------------------------------------------------
-- VEHICLE
-- The rental fleet.
-- status makes availability explicit; no need to query reservations.
-- Soft delete preserves FK integrity for historical records.
-- ---------------------------------------------------------------------------
CREATE TABLE vehicle (
    id INT NOT NULL AUTO_INCREMENT,
    brand VARCHAR(100) NOT NULL,
    licence_plate VARCHAR(20) NOT NULL,
    colour VARCHAR(30) NULL,
    fuel_type VARCHAR(10) NOT NULL,
    spare_wheel TINYINT(1) NOT NULL DEFAULT 0,
    fuel_level TINYINT NULL                    -- percentage 0–100
    COMMENT 'Fuel level percentage 0-100',
    automatic TINYINT(1) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'available',
    price_per_day DECIMAL(10, 2) NOT NULL                -- EUR
    COMMENT 'Daily rental rate in EUR',
    photo_url VARCHAR(500) NULL,

    -- Soft delete
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    deleted_at DATETIME NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_vehicle PRIMARY KEY (id),
    CONSTRAINT uq_vehicle_plate UNIQUE (licence_plate),
    CONSTRAINT chk_vehicle_status CHECK (
        status IN ('available', 'rented', 'maintenance', 'retired')
    ),
    CONSTRAINT chk_fuel_type CHECK (
        fuel_type IN ('petrol', 'diesel', 'electric', 'hybrid')
    ),
    CONSTRAINT chk_fuel_level CHECK (fuel_level BETWEEN 0 AND 100)
);


-- ---------------------------------------------------------------------------
-- RESERVATION
-- Optional pre-booking. Represents intent, not a confirmed rental.
-- A vehicle may be rented directly without a prior reservation (walk-in).
-- ---------------------------------------------------------------------------
CREATE TABLE reservation (
    id INT NOT NULL AUTO_INCREMENT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    price_per_day DECIMAL(10, 2) NOT NULL    -- rate locked at booking time
    COMMENT 'Rate locked at booking time, EUR',
    vehicle_id INT NOT NULL,
    client_id INT NOT NULL,
    created_by INT NOT NULL,   -- user.id

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_reservation PRIMARY KEY (id),
    CONSTRAINT fk_reservation_vehicle FOREIGN KEY (vehicle_id)
    REFERENCES vehicle (id),
    CONSTRAINT fk_reservation_client FOREIGN KEY (client_id)
    REFERENCES client (id),
    CONSTRAINT fk_reservation_user FOREIGN KEY (created_by)
    REFERENCES `user` (id),
    CONSTRAINT chk_reservation_dates CHECK (end_date >= start_date)
);


-- ---------------------------------------------------------------------------
-- ACTIVE_RENTAL
-- A vehicle that is currently out. Created when a vehicle leaves,
-- deleted (or marked closed) when it returns.
-- Links to reservation when one exists; NULL for walk-ins.
-- second_driver_id resolves the "who is the second driver" problem.
-- ---------------------------------------------------------------------------
CREATE TABLE active_rental (
    id INT NOT NULL AUTO_INCREMENT,
    reservation_id INT NULL,       -- NULL = walk-in
    vehicle_id INT NOT NULL,
    client_id INT NOT NULL,
    second_driver_id INT NULL,       -- client.id
    opened_by INT NOT NULL,   -- user.id
    start_date DATE NOT NULL,
    expected_end_date DATE NOT NULL,
    price_per_day DECIMAL(10, 2) NOT NULL
    COMMENT 'Agreed rate for this rental, EUR',
    status VARCHAR(20) NOT NULL DEFAULT 'active',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_active_rental PRIMARY KEY (id),
    CONSTRAINT fk_active_rental_res FOREIGN KEY (reservation_id)
    REFERENCES reservation (id),
    CONSTRAINT fk_active_rental_vehicle FOREIGN KEY (vehicle_id)
    REFERENCES vehicle (id),
    CONSTRAINT fk_active_rental_client FOREIGN KEY (client_id)
    REFERENCES client (id),
    CONSTRAINT fk_active_rental_driver2 FOREIGN KEY (second_driver_id)
    REFERENCES client (id),
    CONSTRAINT fk_active_rental_user FOREIGN KEY (opened_by)
    REFERENCES `user` (id),
    CONSTRAINT chk_active_rental_dates CHECK (expected_end_date >= start_date),
    CONSTRAINT chk_active_rental_status CHECK (status IN ('active', 'overdue'))
);


-- ---------------------------------------------------------------------------
-- RENTAL_EVENT  — the immutable event log
--
-- One row written at the moment a rental is closed. Never updated or deleted.
-- The payload JSON contains a complete snapshot of vehicle + client state
-- at the time of closure. This is the legal and historical source of truth.
--
-- Because this table is append-only, it is intentionally NOT in 3NF:
-- the payload duplicates data from client and vehicle. This is correct —
-- normalisation guards against update anomalies, which cannot exist here.
--
-- soft FK: vehicle_id and client_id are stored for convenience but are
-- NOT declared as FOREIGN KEYs — a vehicle or client can be soft-deleted
-- without invalidating history.
-- ---------------------------------------------------------------------------
CREATE TABLE rental_event (
    id INT NOT NULL AUTO_INCREMENT,
    event_type VARCHAR(30) NOT NULL DEFAULT 'rental_closed',
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    recorded_by INT NOT NULL,   -- user.id (hard FK: users not deleted)

    -- Soft references — informational only, not enforced
    vehicle_id INT NOT NULL,
    client_id INT NOT NULL,

    -- The complete snapshot at closure time
    payload JSON NOT NULL,

    CONSTRAINT pk_rental_event PRIMARY KEY (id),
    CONSTRAINT fk_rental_event_user FOREIGN KEY (recorded_by)
    REFERENCES `user` (id),
    CONSTRAINT chk_rental_event_type CHECK (
        event_type IN ('rental_closed', 'rental_cancelled', 'rental_modified')
    )
);


-- ---------------------------------------------------------------------------
-- RENTAL_ARCHIVE
-- Operational record of every completed rental.
-- Normalised: reads current client/vehicle via JOIN.
-- Links to rental_event for the immutable historical snapshot.
-- price_per_day kept here — may differ from vehicle's current rate.
-- number_of_days and total are generated columns (never stored redundantly).
-- ---------------------------------------------------------------------------
CREATE TABLE rental_archive (
    id INT NOT NULL AUTO_INCREMENT,
    event_id INT NOT NULL,   -- rental_event.id
    reservation_id INT NULL,       -- NULL = walk-in
    vehicle_id INT NOT NULL,
    client_id INT NOT NULL,
    closed_by INT NOT NULL,   -- user.id
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    price_per_day DECIMAL(10, 2) NOT NULL
    COMMENT 'Rate applied, EUR',

    -- Generated columns: always consistent, never manually set
    number_of_days INT GENERATED ALWAYS AS (
        DATEDIFF(end_date, start_date)
    ) STORED,
    total DECIMAL(10, 2) GENERATED ALWAYS AS (
        DATEDIFF(end_date, start_date) * price_per_day
    ) STORED,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_rental_archive PRIMARY KEY (id),
    CONSTRAINT fk_archive_event FOREIGN KEY (event_id)
    REFERENCES rental_event (id),
    CONSTRAINT fk_archive_reservation FOREIGN KEY (reservation_id)
    REFERENCES reservation (id),
    CONSTRAINT fk_archive_vehicle FOREIGN KEY (vehicle_id)
    REFERENCES vehicle (id),
    CONSTRAINT fk_archive_client FOREIGN KEY (client_id)
    REFERENCES client (id),
    CONSTRAINT fk_archive_user FOREIGN KEY (closed_by)
    REFERENCES `user` (id),
    CONSTRAINT chk_archive_dates CHECK (end_date >= start_date)
);


-- ---------------------------------------------------------------------------
-- BLACKLIST
-- Clients refused service. date_end allows lifting a ban.
-- ---------------------------------------------------------------------------
CREATE TABLE blacklist (
    id INT NOT NULL AUTO_INCREMENT,
    client_id INT NOT NULL,
    reason TEXT NULL,
    date_start DATE NOT NULL,
    date_end DATE NULL,       -- NULL = permanent ban
    added_by INT NOT NULL,   -- user.id

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_blacklist PRIMARY KEY (id),
    CONSTRAINT fk_blacklist_client FOREIGN KEY (client_id)
    REFERENCES client (id),
    CONSTRAINT fk_blacklist_user FOREIGN KEY (added_by)
    REFERENCES `user` (id),
    CONSTRAINT chk_blacklist_dates CHECK (date_end IS NULL OR date_end >= date_start)
);


-- ---------------------------------------------------------------------------
-- NOTIFICATION
-- Audit trail for every outbound email (invoice, reminder, etc.).
-- ---------------------------------------------------------------------------
CREATE TABLE notification (
    id INT NOT NULL AUTO_INCREMENT,
    archive_id INT NOT NULL,   -- rental_archive.id
    type VARCHAR(30) NOT NULL,
    recipient VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL,
    sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    provider_msg_id VARCHAR(200) NULL,       -- ID returned by email provider

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT pk_notification PRIMARY KEY (id),
    CONSTRAINT fk_notification_archive FOREIGN KEY (archive_id)
    REFERENCES rental_archive (id),
    CONSTRAINT chk_notification_type CHECK (
        type IN ('invoice', 'return_reminder', 'overdue_alert')
    ),
    CONSTRAINT chk_notification_status CHECK (
        status IN ('sent', 'failed', 'bounced', 'pending')
    )
);


-- =============================================================================
-- INDEXES
-- =============================================================================

-- Availability queries: find active rentals for a vehicle in a date range
CREATE INDEX idx_active_rental_vehicle_dates
ON active_rental (vehicle_id, start_date, expected_end_date);

-- Availability queries: find reservations for a vehicle in a date range
CREATE INDEX idx_reservation_vehicle_dates
ON reservation (vehicle_id, start_date, end_date);

-- Archive lookups by client or vehicle
CREATE INDEX idx_archive_client ON rental_archive (client_id);
CREATE INDEX idx_archive_vehicle ON rental_archive (vehicle_id);
CREATE INDEX idx_archive_dates ON rental_archive (start_date, end_date);

-- Blacklist check before opening a rental
CREATE INDEX idx_blacklist_client ON blacklist (client_id, date_start, date_end);

-- Vehicle availability filter
CREATE INDEX idx_vehicle_status ON vehicle (status);

-- Notification lookups
CREATE INDEX idx_notification_archive ON notification (archive_id);


-- =============================================================================
-- VIEWS
-- =============================================================================

-- Operational view: current archive with readable names, computed totals
CREATE VIEW v_rental_archive AS
SELECT
    ra.id AS archive_id,
    ra.reservation_id,
    ra.event_id,
    ra.start_date,
    ra.end_date,
    ra.number_of_days,
    ra.price_per_day,
    ra.total,
    v.brand AS vehicle_brand,
    v.licence_plate,
    v.colour,
    v.fuel_type,
    c.last_name AS client_last_name,
    c.first_name AS client_first_name,
    c.email AS client_email,
    c.national_id AS client_national_id,
    c.licence_number AS client_licence_number,
    u.username AS closed_by
FROM rental_archive AS ra
INNER JOIN vehicle AS v ON ra.vehicle_id = v.id
INNER JOIN client AS c ON ra.client_id = c.id
INNER JOIN `user` AS u ON ra.closed_by = u.id;


-- Invoice view: pulls the immutable snapshot from the event log
-- Uses MySQL JSON operators; returns one row per archive entry
CREATE VIEW v_invoice AS
SELECT
    ra.id AS archive_id,
    ra.start_date,
    ra.end_date,
    ra.number_of_days,
    ra.price_per_day,
    ra.total,
    re.recorded_at AS closed_at,
    u.username AS agent,
    re.payload -> '$.vehicle.brand' AS vehicle_brand,
    re.payload -> '$.vehicle.licence_plate' AS licence_plate,
    re.payload -> '$.client.last_name' AS client_last_name,
    re.payload -> '$.client.first_name' AS client_first_name,
    re.payload -> '$.client.email' AS client_email,
    re.payload -> '$.client.licence_number' AS client_licence_number,
    re.payload -> '$.client.national_id' AS client_national_id,
    re.payload -> '$.period.price_per_day' AS agreed_price_per_day
FROM rental_archive AS ra
INNER JOIN rental_event AS re ON ra.event_id = re.id
INNER JOIN `user` AS u ON ra.closed_by = u.id;
