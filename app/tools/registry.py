"""Tool registry - Maps tool names to schemas and executors. Whitelist enforcement."""

from app.tools.search_properties import SEARCH_PROPERTIES_SCHEMA, SearchPropertiesArgs
from app.tools.get_property_details import GET_PROPERTY_DETAILS_SCHEMA, GetPropertyDetailsArgs
from app.tools.compare_properties import COMPARE_PROPERTIES_SCHEMA, ComparePropertiesArgs
from app.tools.search_locality import SEARCH_LOCALITY_SCHEMA, SearchLocalityArgs
from app.tools.calculate_emi import CALCULATE_EMI_SCHEMA, CalculateEMIArgs
from app.tools.update_preferences import UPDATE_PREFERENCES_SCHEMA, UpdatePreferencesArgs

# All available tool schemas for Groq
TOOL_SCHEMAS = [
    SEARCH_PROPERTIES_SCHEMA,
    GET_PROPERTY_DETAILS_SCHEMA,
    COMPARE_PROPERTIES_SCHEMA,
    SEARCH_LOCALITY_SCHEMA,
    CALCULATE_EMI_SCHEMA,
    UPDATE_PREFERENCES_SCHEMA,
]

# Whitelist: only these tool names are allowed
ALLOWED_TOOLS = {
    "search_properties",
    "get_property_details",
    "compare_properties",
    "search_locality_information",
    "calculate_emi",
    "update_preferences",
}

# Map tool names to their argument models
TOOL_ARG_MODELS = {
    "search_properties": SearchPropertiesArgs,
    "get_property_details": GetPropertyDetailsArgs,
    "compare_properties": ComparePropertiesArgs,
    "search_locality_information": SearchLocalityArgs,
    "calculate_emi": CalculateEMIArgs,
    "update_preferences": UpdatePreferencesArgs,
}
