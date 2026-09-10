"""
Module 3: Holland Parametric Wind Field
=========================================
Computes the peak wind speed each property in our portfolio experiences from
each synthetic hurricane event. This is the "hazard" step of the cat-model
pipeline: hazard (how strong is the wind here) is kept separate from
vulnerability (how much damage does that wind cause) and financial (how much
$ loss does that damage cause) - this three-module split (hazard /
vulnerability / financial) is exactly how RMS/AIR structure their own models,
and being able to name that separation is a real interview talking point.

METHODOLOGY: Holland (1980) parametric wind profile model.
Reference: Holland, G.J. (1980), "An Analytic Model of the Wind and Pressure
Profiles in Hurricanes," Monthly Weather Review, 108, 1212-1218.
I am CONFIDENT in the functional form of this equation below (it's the
standard, widely-reproduced Holland formula found in essentially every
tropical cyclone wind-field paper). What I am NOT independently certain of is
the exact empirical B-parameter regression used by any specific commercial
model - see the disclosure in estimate_b_parameter() below.

SCOPING DECISION - what "hazard footprint" means here:
This project computes wind at a storm's LANDFALL SNAPSHOT only (peak
intensity, single point in time), not full track-integrated exposure as the
storm moves across the region over several hours. A full track-integrated
footprint (what RMS/AIR actually do) would sum wind duration/intensity along
the entire storm path near the portfolio. That's a meaningfully more complex
piece of engineering. I'm using the single-snapshot simplification and
disclosing it explicitly - it's defensible for a portfolio project but you
should say plainly in an interview: "I modeled peak intensity at landfall as
a simplification; a full model integrates the wind field along the entire
track duration."
"""

import numpy as np
from math import radians

EARTH_RADIUS_KM = 6371.0
OMEGA = 7.2921159e-5      # Earth's rotation rate (rad/s) - exact physical constant
RHO_AIR = 1.15            # kg/m^3, near-surface tropical air density.
                          # Commonly used in Holland-model literature; some
                          # sources use 1.2 kg/m^3 instead - minor, disclosed
                          # uncertainty, doesn't change results materially.
PN_MB = 1013.0            # Ambient ("far-field") pressure, standard assumption


def haversine_km_vec(lat1, lon1, lat2_arr, lon2_arr):
    """Distance from a single point to an array of points, vectorized."""
    lat1r, lon1r = radians(lat1), radians(lon1)
    lat2r = np.radians(lat2_arr)
    lon2r = np.radians(lon2_arr)
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def bearing_deg_vec(lat1, lon1, lat2_arr, lon2_arr):
    """Compass bearing (0=N,90=E) from a single point to an array of points."""
    lat1r = radians(lat1)
    lat2r = np.radians(lat2_arr)
    dlon = np.radians(lon2_arr - lon1)
    x = np.sin(dlon) * np.cos(lat2r)
    y = np.cos(lat1r) * np.sin(lat2r) - np.sin(lat1r) * np.cos(lat2r) * np.cos(dlon)
    return (np.degrees(np.arctan2(x, y)) + 360) % 360


def estimate_rmw_km(pressure_mb):
    """
    Fallback estimate for Radius of Maximum Winds (RMW) when HURDAT2 doesn't
    have it recorded - which is true for 78 of our 79 historical FL landfalls
    (RMW was only added to HURDAT2's format starting with very recent storms,
    ~2021+; I checked this directly against the uploaded file rather than
    assuming it).

    UNCERTAINTY DISCLOSURE: published empirical models DO exist for RMW as a
    function of pressure/intensity and latitude (e.g., Vickery & Wadhera,
    2008, J. Applied Meteorology and Climatology - a commonly cited paper for
    exactly this). I do not have confident, verified recall of that paper's
    exact regression coefficients, so rather than presenting invented
    coefficients as if they were Vickery & Wadhera's real numbers, I'm using
    a simple physically-reasonable placeholder instead: stronger storms
    (lower pressure) tend to have tighter, smaller RMW, modeled here as a
    linear decrease with pressure deficit, bounded to a plausible 15-60km
    range. If you need this defensible beyond "reasonable placeholder," look
    up Vickery & Wadhera (2008) directly and swap in their real formula.
    """
    pressure_deficit = max(PN_MB - pressure_mb, 1)
    rmw_km = 60 - (pressure_deficit * 0.35)
    return float(np.clip(rmw_km, 15, 60))


def estimate_b_parameter(pressure_mb):
    """
    Holland's B parameter controls how 'peaked' vs. 'broad' the wind profile
    is. Physically valid range is roughly 1.0-2.5 (Holland 1980).

    UNCERTAINTY DISCLOSURE: commercial/academic models calibrate B via
    regression against observed flight-level or H*Wind data (Holland 1980;
    Vickery & Skerlj). I don't have confident recall of a specific published
    regression's exact coefficients, so this is an illustrative, monotonic
    relationship (stronger storm -> tighter wind field -> higher B) rather
    than a literature-derived formula. Flag this plainly if asked.
    """
    pressure_deficit = PN_MB - pressure_mb
    b = 1.0 + pressure_deficit / 120.0
    return float(np.clip(b, 1.0, 2.5))


def holland_wind_speed_kt(r_km, rmw_km, pressure_mb, storm_lat):
    """
    Core Holland (1980) parametric wind equation. Vectorized over r_km
    (array of distances from storm center to each portfolio location).
    Returns 1-minute sustained wind speed in knots at each distance.
    """
    b = estimate_b_parameter(pressure_mb)
    delta_p_pa = (PN_MB - pressure_mb) * 100.0          # mb -> Pa
    f = 2 * OMEGA * abs(np.sin(radians(storm_lat)))      # Coriolis parameter

    r_m = np.maximum(r_km * 1000.0, 1000.0)              # floor at 1km, avoid div-by-zero at center
    rmw_m = rmw_km * 1000.0

    term = (rmw_m / r_m) ** b
    v_squared = (b / RHO_AIR) * term * delta_p_pa * np.exp(-term) + (r_m * f / 2) ** 2
    v_ms = np.sqrt(v_squared) - (r_m * f / 2)
    v_kt = np.clip(v_ms, 0, None) * 1.94384              # m/s -> kt
    return v_kt


def apply_motion_asymmetry(base_wind_kt, bearing_to_location_deg, heading_deg, forward_speed_kmh):
    """
    Real hurricanes are NOT symmetric: in the Northern Hemisphere, the
    front-right quadrant (relative to the storm's direction of travel) is
    measurably stronger because the storm's forward motion vector adds
    constructively with the cyclonic rotation there, and subtracts on the
    back-left side. This is well-established meteorological fact.

    UNCERTAINTY DISCLOSURE: the exact magnitude of this effect (what fraction
    of forward speed to add/subtract, and the precise quadrant geometry) is
    modeled with more sophistication in the literature than I'm reproducing
    here. This is a simplified cosine-weighted adjustment - directionally
    correct (physically real effect, real phenomenon), but the 0.5 scaling
    factor below is illustrative, not calibrated against observational data.
    """
    forward_speed_kt = forward_speed_kmh * 0.539957      # km/h -> kt
    # Max enhancement at 90 deg clockwise from heading (front-right quadrant, N. Hem.)
    angle_from_max_quadrant = bearing_to_location_deg - (heading_deg + 90)
    asymmetry_factor = 0.5 * forward_speed_kt * np.cos(np.radians(angle_from_max_quadrant))
    return np.clip(base_wind_kt + asymmetry_factor, 0, None)


def gust_from_sustained(sustained_wind_kt):
    """
    Converts 1-minute sustained wind to a peak 3-second gust estimate.
    Engineering literature commonly uses a gust factor in roughly the
    1.1-1.3 range depending on terrain/exposure and averaging period
    (see general discussion in ASCE 7 commentary on wind speed conversions).
    I have NOT verified an exact, terrain-specific coefficient here - using
    1.15 as a round, illustrative mid-range value. Flag as approximate if
    pressed on the specific number in an interview.
    """
    GUST_FACTOR = 1.15
    return sustained_wind_kt * GUST_FACTOR


def compute_event_footprint(event, locations_lat, locations_lon):
    """
    For one synthetic event, compute peak gust wind speed (kt) at every
    portfolio location. Vectorized across all locations at once.
    """
    r_km = haversine_km_vec(event["landfall_lat"], event["landfall_lon"], locations_lat, locations_lon)
    bearing = bearing_deg_vec(event["landfall_lat"], event["landfall_lon"], locations_lat, locations_lon)
    rmw_km = estimate_rmw_km(event["pressure_mb"])

    sustained = holland_wind_speed_kt(r_km, rmw_km, event["pressure_mb"], event["landfall_lat"])
    sustained_asym = apply_motion_asymmetry(sustained, bearing, event["heading_deg"], event["forward_speed_kmh"])
    gust = gust_from_sustained(sustained_asym)
    return gust


if __name__ == "__main__":
    import sqlite3
    import time
    from pathlib import Path

    DB_PATH = Path(__file__).resolve().parent.parent / "db" / "portfolio.db"
    conn = sqlite3.connect(DB_PATH)

    locations = conn.execute("SELECT location_id, latitude, longitude FROM locations").fetchall()
    loc_ids = np.array([r[0] for r in locations])
    loc_lat = np.array([r[1] for r in locations])
    loc_lon = np.array([r[2] for r in locations])

    # Sanity test: run the footprint calc on Hurricane Andrew's actual
    # historical parameters (not a synthetic variant) to see if the physics
    # produces plausible numbers before we run the full 10,270-event catalog.
    andrew = conn.execute(
        "SELECT landfall_lat, landfall_lon, max_wind_kt, pressure_mb, forward_speed_kmh, heading_deg "
        "FROM historical_events WHERE name LIKE '%ANDREW%' LIMIT 1"
    ).fetchone()
    andrew_event = {
        "landfall_lat": andrew[0], "landfall_lon": andrew[1],
        "max_wind_kt": andrew[2], "pressure_mb": andrew[3],
        "forward_speed_kmh": andrew[4], "heading_deg": andrew[5],
    }
    print("Testing Holland wind field on real Hurricane Andrew (1992) parameters:")
    print(f"  Landfall: {andrew_event['landfall_lat']}, {andrew_event['landfall_lon']}, "
          f"{andrew_event['pressure_mb']}mb, recorded max wind {andrew_event['max_wind_kt']}kt")
    gust = compute_event_footprint(andrew_event, loc_lat, loc_lon)
    print(f"  Modeled peak gust across portfolio: min={gust.min():.1f}kt, "
          f"max={gust.max():.1f}kt, mean={gust.mean():.1f}kt")
    print(f"  (Sanity check: max modeled gust should be same order of magnitude as "
          f"Andrew's real ~145kt sustained -> ~167kt gust at 1.15x factor, for "
          f"locations very close to the landfall point)")

    # Now time the full-catalog computation to decide on storage strategy
    # before committing to a table design.
    synthetic_events = conn.execute(
        "SELECT event_id, landfall_lat, landfall_lon, pressure_mb, forward_speed_kmh, heading_deg, annual_rate "
        "FROM synthetic_events"
    ).fetchall()
    print(f"\nTiming full footprint computation across {len(synthetic_events)} events x {len(loc_ids)} locations...")

    start = time.time()
    total_above_threshold = 0
    for row in synthetic_events:
        event = {"landfall_lat": row[1], "landfall_lon": row[2], "pressure_mb": row[3],
                  "forward_speed_kmh": row[4], "heading_deg": row[5]}
        gust = compute_event_footprint(event, loc_lat, loc_lon)
        total_above_threshold += int((gust >= 50).sum())  # 50kt gust ~ minimal damage onset, see Module 4
    elapsed = time.time() - start
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Total (event, location) pairs with gust >= 50kt: {total_above_threshold:,} "
          f"out of {len(synthetic_events) * len(loc_ids):,} possible pairs "
          f"({100*total_above_threshold/(len(synthetic_events)*len(loc_ids)):.1f}%)")

    conn.close()
