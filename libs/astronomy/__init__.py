"""
astronomy-core: The scientific engine for telesco-pi.

This package implements the astronomical domain logic for the telesco-pi platform.
It is designed as a pure Python library with no dependencies on the FastAPI backend,
WebSocket layer, or any UI framework.

Key modules:
    contracts: Typed, versioned data contracts for integration with backend/frontend.
    domain: Core scientific domain types (observer, targets, constraints).
    catalogs: Local offline catalogs (Messier, NGC/IC, bright stars, TLE).
    visibility: Ephemeris calculations and target scoring.
    planner: Night session planner and scheduler.
    calibration: Initial alignment and calibration flow.
    pointing: Local alt-az pointing model.
    solving: Plate solving integration (local astrometry.net first).
    processing: Image processing pipelines (planetary, live stacking).
    orbital: TLE-based orbital tracking and pass calculation.
    jobs: Job orchestration and persistence.

Scientific rigor notes:
    - All empirical metrics are labeled as such.
    - Pending hardware validation is explicitly noted.
    - No claim of scientific accuracy without confidence level.
    - Performance budgets are conservative estimates for Raspberry Pi 5.
"""

from __future__ import annotations
