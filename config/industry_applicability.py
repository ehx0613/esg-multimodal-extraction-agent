from typing import Dict


CORE = "core"
OPTIONAL = "optional"
UNLIKELY = "unlikely"
NOT_APPLICABLE = "not_applicable"
DEFAULT_INDUSTRY = "general"


INDUSTRY_APPLICABILITY: Dict[str, Dict[str, str]] = {
    "finance": {
        "wastewater_discharge": NOT_APPLICABLE,
        "air_pollutant_emissions": NOT_APPLICABLE,
        "hazardous_waste": NOT_APPLICABLE,
        "non_hazardous_waste": UNLIKELY,
        "natural_gas_consumption": UNLIKELY,
        "environmental_investment": OPTIONAL,
        "scope_1_emissions": OPTIONAL,
        "scope_2_emissions": OPTIONAL,
        "water_consumption": OPTIONAL,
        "electricity_consumption": OPTIONAL,
        "data_security_privacy": CORE,
        "anti_corruption_policy": CORE,
        "anti_corruption_training_sessions": CORE,
        "anti_corruption_training_participants": CORE,
        "training_coverage_rate": CORE,
        "social_security_coverage": CORE,
        "employee_medical_checkup_coverage": OPTIONAL,
        "safety_accident_count": OPTIONAL,
        "occupational_health_safety_investment": UNLIKELY,
        "lost_work_days_due_to_injury": NOT_APPLICABLE,
    },
    "pharma": {
        "wastewater_discharge": CORE,
        "air_pollutant_emissions": CORE,
        "hazardous_waste": CORE,
        "non_hazardous_waste": CORE,
        "environmental_investment": CORE,
        "environmental_penalty_count": CORE,
        "water_consumption": CORE,
        "energy_consumption_total": CORE,
        "electricity_consumption": CORE,
        "occupational_health_safety_investment": CORE,
        "safety_accident_count": CORE,
        "employee_medical_checkup_coverage": CORE,
        "r_and_d_expense": CORE,
        "r_and_d_personnel_count": CORE,
        "data_security_privacy": OPTIONAL,
    },
    "manufacturing": {
        "total_ghg_emissions": CORE,
        "scope_1_emissions": CORE,
        "scope_2_emissions": CORE,
        "energy_consumption_total": CORE,
        "energy_consumption_intensity": CORE,
        "natural_gas_consumption": OPTIONAL,
        "electricity_consumption": CORE,
        "water_consumption": CORE,
        "wastewater_discharge": CORE,
        "air_pollutant_emissions": CORE,
        "non_hazardous_waste": CORE,
        "hazardous_waste": CORE,
        "environmental_investment": CORE,
        "occupational_health_safety_investment": CORE,
        "safety_accident_count": CORE,
        "lost_work_days_due_to_injury": CORE,
        "data_security_privacy": OPTIONAL,
    },
    "service": {
        "total_ghg_emissions": OPTIONAL,
        "scope_1_emissions": UNLIKELY,
        "scope_2_emissions": OPTIONAL,
        "ghg_emissions_intensity": UNLIKELY,
        "energy_consumption_total": OPTIONAL,
        "energy_consumption_intensity": UNLIKELY,
        "wastewater_discharge": UNLIKELY,
        "air_pollutant_emissions": UNLIKELY,
        "hazardous_waste": UNLIKELY,
        "non_hazardous_waste": UNLIKELY,
        "natural_gas_consumption": UNLIKELY,
        "electricity_consumption": OPTIONAL,
        "water_consumption": OPTIONAL,
        "environmental_investment": OPTIONAL,
        "environmental_penalty_count": OPTIONAL,
        "occupational_health_safety_investment": UNLIKELY,
        "safety_accident_count": OPTIONAL,
        "safety_emergency_drill_count": UNLIKELY,
        "lost_work_days_due_to_injury": UNLIKELY,
        "r_and_d_expense": UNLIKELY,
        "r_and_d_personnel_count": UNLIKELY,
        "data_security_privacy": CORE,
        "employee_training_development": CORE,
        "total_employees": CORE,
        "male_employees": CORE,
        "female_employees": CORE,
        "female_employee_ratio": CORE,
        "employee_turnover_rate": CORE,
        "training_total_hours": CORE,
        "training_hours_per_employee": CORE,
        "training_coverage_rate": CORE,
        "trained_employees_count": CORE,
        "social_security_coverage": CORE,
        "employee_medical_checkup_coverage": OPTIONAL,
        "anti_corruption_policy": CORE,
        "anti_corruption_training_sessions": OPTIONAL,
        "anti_corruption_training_participants": OPTIONAL,
        "board_size": CORE,
        "independent_directors": CORE,
        "independent_director_ratio": CORE,
        "female_directors": CORE,
        "board_meetings": CORE,
        "shareholder_meetings": CORE,
        "confirmed_corruption_cases": OPTIONAL,
        "public_welfare_investment": CORE,
    },
}


INDUSTRY_PRIORITY_WEIGHTS = {
    CORE: 20,
    OPTIONAL: 5,
    UNLIKELY: -10,
    NOT_APPLICABLE: -999,
}


def get_applicability(industry: str, field_key: str) -> str:
    industry = industry or DEFAULT_INDUSTRY
    return INDUSTRY_APPLICABILITY.get(industry, {}).get(field_key, CORE)


def get_priority_weight(industry: str, field_key: str) -> int:
    return INDUSTRY_PRIORITY_WEIGHTS.get(get_applicability(industry, field_key), 0)


def is_applicable(industry: str, field_key: str) -> bool:
    return get_applicability(industry, field_key) != NOT_APPLICABLE
