"""The sample mission new users can open in one click (ADR-0018).

Fictional operator; chosen to exercise several jurisdictions at once: a Luxembourg-established
Earth-observation constellation with ground stations in the UK and the US and customers in France,
the UK and the US.
"""

from __future__ import annotations

import datetime as dt

from app.planner.mission import FrequencyBand, MissionProfile, OrbitRegime, RadioService


def sample_mission(today: dt.date) -> MissionProfile:
    launch = dt.date(today.year + 2, 3, 1)
    return MissionProfile(
        name="Sample: 8-satellite Earth-observation constellation",
        operator_name="Example Orbital S.à r.l. (fictional)",
        operator_country="LU",
        ground_station_countries=["GB", "US"],
        service_countries=["FR", "GB", "US"],
        orbit=OrbitRegime.LEO,
        altitude_km=550,
        satellite_count=8,
        services=[RadioService.EARTH_EXPLORATION_SATELLITE, RadioService.SPACE_OPERATION],
        frequency_bands=[FrequencyBand.S, FrequencyBand.X],
        earth_observation_imaging=True,
        target_launch_date=launch,
    )
