-- schema.sql
-- Exposure database schema, modeled loosely on a real-world "Statement of Values" (SOV)
-- submission format that cedants/brokers send to a Cat Analyst for modeling.
-- Normalized into 3 tables because in practice a single physical location can carry
-- multiple coverage types (building, contents, business interruption/ALE) under one
-- policy, and separating them lets us do coverage-level SQL rollups later.

DROP TABLE IF EXISTS coverages;
DROP TABLE IF EXISTS policies;
DROP TABLE IF EXISTS locations;

-- One row per physical property (this is what gets geocoded and hit by hazard).
CREATE TABLE locations (
    location_id     INTEGER PRIMARY KEY,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    county          TEXT NOT NULL,          -- Miami-Dade, Broward, or Palm Beach
    construction_class TEXT NOT NULL,       -- HAZUS Hurricane Model building classes
    occupancy       TEXT NOT NULL,          -- Residential (this portfolio is residential-only)
    year_built      INTEGER NOT NULL,
    num_stories     INTEGER NOT NULL
);

-- One row per policy. In this synthetic portfolio it's 1:1 with locations
-- (single-location policies), but kept as a separate table because real SOVs
-- often have multi-location policies, and interviewers may ask why you split this out.
CREATE TABLE policies (
    policy_id       INTEGER PRIMARY KEY,
    location_id     INTEGER NOT NULL REFERENCES locations(location_id),
    total_insured_value REAL NOT NULL,      -- TIV in USD, building coverage only at this table level
    deductible_pct  REAL NOT NULL           -- hurricane deductible as % of TIV (FL practice: 2-10%)
);

-- Coverage-level breakdown. Real property policies split TIV across coverage types;
-- we model Building / Contents / ALE (Additional Living Expense) as is standard for
-- FL residential policies. This lets us later show "loss by coverage type" in SQL,
-- which is a real reporting cut Cat Analysts are asked for.
CREATE TABLE coverages (
    coverage_id     INTEGER PRIMARY KEY,
    policy_id       INTEGER NOT NULL REFERENCES policies(policy_id),
    coverage_type   TEXT NOT NULL,          -- 'Building', 'Contents', 'ALE'
    coverage_value  REAL NOT NULL
);

CREATE INDEX idx_locations_county ON locations(county);
CREATE INDEX idx_locations_construction ON locations(construction_class);
CREATE INDEX idx_policies_location ON policies(location_id);
CREATE INDEX idx_coverages_policy ON coverages(policy_id);
