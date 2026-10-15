"""Mission profile: the planner's only input (ADR-0018).

Describes what the operator wants to do, in the terms licensing rules are written in: where the
operator is established, where it launches from and operates from, which markets it serves,
which radio services and bands it uses. Licence applicability rules in ``knowledge/`` read the
facts exposed by :meth:`MissionProfile.facts`, so every field name there is part of the
knowledge-pack contract.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

#: ISO 3166-1 alpha-2, upper case (``GB`` for the United Kingdom).
CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]


class OrbitRegime(StrEnum):
    LEO = "LEO"
    MEO = "MEO"
    GEO = "GEO"
    HEO = "HEO"


class RadioService(StrEnum):
    """ITU Radio Regulations space radiocommunication services (RR Article 1)."""

    EARTH_EXPLORATION_SATELLITE = "earth_exploration_satellite"
    FIXED_SATELLITE = "fixed_satellite"
    MOBILE_SATELLITE = "mobile_satellite"
    BROADCASTING_SATELLITE = "broadcasting_satellite"
    SPACE_OPERATION = "space_operation"
    SPACE_RESEARCH = "space_research"
    AMATEUR_SATELLITE = "amateur_satellite"
    RADIONAVIGATION_SATELLITE = "radionavigation_satellite"


class FrequencyBand(StrEnum):
    VHF = "VHF"
    UHF = "UHF"
    L = "L"
    S = "S"
    C = "C"
    X = "X"
    KU = "Ku"
    K = "K"
    KA = "Ka"
    Q = "Q"
    V = "V"
    E = "E"
    OPTICAL = "optical"


class MissionProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    operator_name: str = Field(default="", max_length=200)
    operator_country: CountryCode
    #: Administration that submits the ITU filings. Defaults to the operator's country.
    filing_administration: CountryCode | None = None
    #: Where the satellites are commanded from. Defaults to the operator's country.
    control_country: CountryCode | None = None
    #: Country of the launch site; ``None`` when not decided yet.
    launch_country: CountryCode | None = None
    ground_station_countries: list[CountryCode] = Field(default_factory=list)
    #: Countries where the operator will provide services to users (market access).
    service_countries: list[CountryCode] = Field(default_factory=list)
    orbit: OrbitRegime
    altitude_km: float | None = Field(default=None, gt=0)
    satellite_count: int = Field(ge=1, le=100_000)
    services: list[RadioService] = Field(min_length=1)
    frequency_bands: list[FrequencyBand] = Field(default_factory=list)
    #: Imaging payload whose data is distributed (triggers remote-sensing regimes).
    earth_observation_imaging: bool = False
    #: End-user terminals in a service market (triggers type approval / terminal licensing).
    user_terminals: bool = False
    target_launch_date: dt.date
    #: When commercial service starts. Defaults to the launch date.
    service_start_date: dt.date | None = None

    @model_validator(mode="after")
    def _service_after_launch(self) -> MissionProfile:
        if self.service_start_date and self.service_start_date < self.target_launch_date:
            raise ValueError("service_start_date cannot be before target_launch_date")
        return self

    @property
    def effective_service_start(self) -> dt.date:
        return self.service_start_date or self.target_launch_date

    def facts(self) -> dict[str, Any]:
        """The values licence rules are evaluated against, with defaults resolved."""
        return {
            "operator_country": self.operator_country,
            "filing_administration": self.filing_administration or self.operator_country,
            "control_country": self.control_country or self.operator_country,
            "launch_country": self.launch_country,
            "ground_station_countries": list(self.ground_station_countries),
            "service_countries": list(self.service_countries),
            "orbit": self.orbit.value,
            "altitude_km": self.altitude_km,
            "satellite_count": self.satellite_count,
            "services": [s.value for s in self.services],
            "frequency_bands": [b.value for b in self.frequency_bands],
            "earth_observation_imaging": self.earth_observation_imaging,
            "user_terminals": self.user_terminals,
        }


#: Field names a licence rule may test, with whether the fact is a list.
FACT_FIELDS: dict[str, bool] = {
    "operator_country": False,
    "filing_administration": False,
    "control_country": False,
    "launch_country": False,
    "ground_station_countries": True,
    "service_countries": True,
    "orbit": False,
    "altitude_km": False,
    "satellite_count": False,
    "services": True,
    "frequency_bands": True,
    "earth_observation_imaging": False,
    "user_terminals": False,
}
