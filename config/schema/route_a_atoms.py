from typing import Any, Dict


def atom(
    subject: str,
    measure: str,
    aggregation: str = "total",
    *,
    scope: str = "company",
    forbidden_subjects: list[str] | None = None,
    forbidden_scopes: list[str] | None = None,
    forbidden_aggregations: list[str] | None = None,
) -> Dict[str, Any]:
    return {
        "atoms": {
            "subject": [subject],
            "scope": [scope],
            "measure": [measure],
            "aggregation": [aggregation],
        },
        "mutex": {
            "subjects": forbidden_subjects or [],
            "scopes": forbidden_scopes or [],
            "aggregations": forbidden_aggregations or [],
        },
    }


ROUTE_A_ATOM_METADATA = {
    # E
    "total_ghg_emissions": atom("ghg", "emission", forbidden_scopes=["scope_1", "scope_2", "scope_3"], forbidden_aggregations=["intensity", "per_capita"]),
    "ghg_emissions_intensity": atom("ghg", "emission", "intensity", forbidden_aggregations=["total"]),
    "scope_1_emissions": atom("ghg", "emission", scope="scope_1", forbidden_scopes=["scope_2", "scope_3"], forbidden_aggregations=["intensity"]),
    "scope_2_emissions": atom("ghg", "emission", scope="scope_2", forbidden_scopes=["scope_1", "scope_3"], forbidden_aggregations=["intensity"]),
    "energy_consumption_total": atom("energy", "consumption", forbidden_subjects=["electricity", "natural_gas"], forbidden_aggregations=["intensity"]),
    "energy_consumption_intensity": atom("energy", "consumption", "intensity", forbidden_aggregations=["total"]),
    "natural_gas_consumption": atom("natural_gas", "consumption", forbidden_subjects=["electricity"]),
    "electricity_consumption": atom("electricity", "consumption", forbidden_subjects=["natural_gas", "renewable_electricity"], forbidden_aggregations=["intensity"]),
    "water_consumption": atom("water", "consumption", forbidden_subjects=["wastewater"], forbidden_aggregations=["intensity"]),
    "wastewater_discharge": atom("wastewater", "discharge", forbidden_subjects=["water"]),
    "air_pollutant_emissions": atom("air_pollutant", "emission"),
    "non_hazardous_waste": atom("non_hazardous_waste", "generation", forbidden_subjects=["hazardous_waste"]),
    "hazardous_waste": atom("hazardous_waste", "generation", forbidden_subjects=["non_hazardous_waste"]),
    "environmental_investment": atom("environment", "investment"),
    "environmental_penalty_count": atom("environmental_violation", "count"),
    # S
    "total_employees": atom("employee", "count", forbidden_scopes=["new_hire", "departed_employee"], forbidden_aggregations=["percentage"]),
    "male_employees": atom("employee", "count", scope="male", forbidden_scopes=["female", "new_hire", "departed_employee"], forbidden_aggregations=["percentage"]),
    "female_employees": atom("employee", "count", scope="female", forbidden_scopes=["male", "new_hire", "departed_employee"], forbidden_aggregations=["percentage"]),
    "female_employee_ratio": atom("employee", "count", "percentage", scope="female", forbidden_scopes=["new_hire", "departed_employee"], forbidden_subjects=["director", "management"]),
    "employee_turnover_rate": atom("employee", "turnover", "percentage"),
    "training_total_hours": atom("employee_training", "duration", forbidden_aggregations=["average", "per_capita"]),
    "training_hours_per_employee": atom("employee_training", "duration", "average", forbidden_aggregations=["total"]),
    "training_coverage_rate": atom("employee_training", "coverage", "percentage", forbidden_subjects=["anti_corruption_training"]),
    "social_security_coverage": atom("social_security", "coverage", "percentage"),
    "employee_medical_checkup_coverage": atom("medical_checkup", "coverage", "percentage"),
    "trained_employees_count": atom("employee_training", "participants"),
    "safety_accident_count": atom("safety_accident", "count"),
    "occupational_health_safety_investment": atom("occupational_safety", "investment", forbidden_subjects=["environment"]),
    "safety_emergency_drill_count": atom("emergency_drill", "count"),
    "lost_work_days_due_to_injury": atom("work_injury", "lost_days"),
    "r_and_d_personnel_count": atom("r_and_d", "personnel"),
    "r_and_d_expense": atom("r_and_d", "investment"),
    "public_welfare_investment": atom("public_welfare", "investment"),
    # G
    "board_size": atom("director", "count", forbidden_scopes=["independent", "female"], forbidden_aggregations=["percentage"]),
    "independent_directors": atom("director", "count", scope="independent", forbidden_aggregations=["percentage"]),
    "independent_director_ratio": atom("director", "count", "percentage", scope="independent"),
    "female_directors": atom("director", "count", scope="female", forbidden_aggregations=["percentage"]),
    "board_meetings": atom("board_meeting", "count", forbidden_subjects=["shareholder_meeting", "committee_meeting"]),
    "shareholder_meetings": atom("shareholder_meeting", "count", forbidden_subjects=["board_meeting"]),
    "anti_corruption_training_sessions": atom("anti_corruption_training", "sessions", forbidden_aggregations=["participants", "duration"]),
    "anti_corruption_training_participants": atom("anti_corruption_training", "participants", forbidden_aggregations=["sessions", "duration"]),
    "confirmed_corruption_cases": atom("corruption_case", "count", forbidden_subjects=["anti_corruption_training"]),
}


def enrich_route_a_item(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata = ROUTE_A_ATOM_METADATA.get(item.get("field_key"), {})
    return {**item, **metadata} if metadata else dict(item)


__all__ = ["ROUTE_A_ATOM_METADATA", "enrich_route_a_item"]
