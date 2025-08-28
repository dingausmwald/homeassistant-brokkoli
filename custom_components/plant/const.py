"""Constants"""

from homeassistant.const import ATTR_ICON

DOMAIN = "plant"
DOMAIN_SENSOR = "sensor"
DOMAIN_PLANTBOOK = "seedfinder"
CYCLE_DOMAIN = "cycle"

REQUEST_TIMEOUT = 30

# ATTRs are used by machines
ATTR_BATTERY = "battery"
ATTR_BRIGHTNESS = "brightness"
ATTR_MOISTURE = "moisture"
ATTR_CONDUCTIVITY = "conductivity"
ATTR_ILLUMINANCE = "illuminance"
ATTR_HUMIDITY = "humidity"
ATTR_CO2 = "co2"
ATTR_PPFD = "ppfd"
ATTR_MMOL = "mmol"
ATTR_MOL = "mol"
ATTR_DLI = "dli"
ATTR_WATER_CONSUMPTION = "water_consumption"
ATTR_FERTILIZER_CONSUMPTION = "fertilizer_consumption"
ATTR_POWER_CONSUMPTION = "power_consumption"
ATTR_PH = "ph"

# Device Classes
DEVICE_CLASS_PH = "ph"  # Eigene Device Class für pH

ATTR_TEMPERATURE = "temperature"
ATTR_PROBLEM = "problem"
ATTR_SENSORS = "sensors"
ATTR_SENSOR = "sensor"
ATTR_METERS = "meters"
ATTR_THRESHOLDS = "thresholds"
ATTR_ENTITY = "entity"
ATTR_SELECT = "select"
ATTR_OPTIONS = "options"
ATTR_PLANT = "plant"
ATTR_STRAIN = "strain"
ATTR_IMAGE = "image"
ATTR_SEARCH_FOR = "search_for"
ATTR_BREEDER = "breeder"
ATTR_PID = "pid"

# Readings are used by humans
READING_BATTERY = "battery"
READING_TEMPERATURE = "temperature"
READING_MOISTURE = "soil moisture"
READING_CONDUCTIVITY = "conductivity"
READING_ILLUMINANCE = "illuminance"
READING_HUMIDITY = "air humidity"
READING_CO2 = "air CO2"
READING_PPFD = "ppfd (mol)"
READING_MMOL = "mmol"
READING_MOL = "mol"
READING_DLI = "dli"
READING_MOISTURE_CONSUMPTION = "water consumption"
READING_FERTILIZER_CONSUMPTION = "fertilizer consumption"
READING_POWER_CONSUMPTION = "power consumption"
READING_PH = "soil pH"

ATTR_MAX_ILLUMINANCE_HISTORY = "max_illuminance"
ATTR_LIMITS = "limits"
ATTR_MIN = "min"
ATTR_MAX = "max"
ATTR_CURRENT = "current"

DEFAULT_MIN_BATTERY_LEVEL = 20
DEFAULT_MIN_TEMPERATURE = 10
DEFAULT_MAX_TEMPERATURE = 40
DEFAULT_MIN_MOISTURE = 20
DEFAULT_MAX_MOISTURE = 60
DEFAULT_MIN_CONDUCTIVITY = 500
DEFAULT_MAX_CONDUCTIVITY = 3000
DEFAULT_MIN_ILLUMINANCE = 0
DEFAULT_MAX_ILLUMINANCE = 100000
DEFAULT_MIN_HUMIDITY = 20
DEFAULT_MAX_HUMIDITY = 60
DEFAULT_MIN_CO2 = 60
DEFAULT_MAX_CO2 = 60
DEFAULT_MIN_MMOL = 2000
DEFAULT_MAX_MMOL = 20000
DEFAULT_MIN_MOL = 2
DEFAULT_MAX_MOL = 30
DEFAULT_MIN_DLI = 2
DEFAULT_MAX_DLI = 30

# Neue Konstanten für Water/Fertilizer Consumption
DEFAULT_MIN_WATER_CONSUMPTION = 0.1
DEFAULT_MAX_WATER_CONSUMPTION = 2.0
DEFAULT_MIN_FERTILIZER_CONSUMPTION = 0.1
DEFAULT_MAX_FERTILIZER_CONSUMPTION = 2.0
DEFAULT_MIN_POWER_CONSUMPTION = 0.1
DEFAULT_MAX_POWER_CONSUMPTION = 5.0

# pH Defaults
DEFAULT_MIN_PH = 5.5
DEFAULT_MAX_PH = 7.5

DEFAULT_IMAGE_PATH = "/config/www/images/plants/"
DEFAULT_IMAGE_LOCAL_URL = "/local/images/plants/"

DATA_SOURCE = "data_source"
DATA_SOURCE_PLANTBOOK = "OpenPlantbook"
DATA_SOURCE_MANUAL = "Manual"
DATA_SOURCE_DEFAULT = "Default values"
DATA_UPDATED = "plant_data_updated"

UNIT_PPFD = "mol/s⋅m²s"
UNIT_MICRO_PPFD = "μmol/s⋅m²"
UNIT_DLI = "mol/d⋅m²"
UNIT_MICRO_DLI = "μmol/d⋅m²"
UNIT_CONDUCTIVITY = "μS/cm"
UNIT_VOLUME = "L"

FLOW_WRONG_PLANT = "wrong_plant"
FLOW_RIGHT_PLANT = "right_plant"
FLOW_ERROR_NOTFOUND = "opb_notfound"
FLOW_STRING_DESCRIPTION = "desc"

FLOW_PLANT_INFO = "plant_info"
FLOW_PLANT_SPECIES = "plant_species"
FLOW_PLANT_NAME = "plant_name"
FLOW_PLANT_IMAGE = "image_url"
FLOW_PLANT_LIMITS = "limits"

FLOW_SENSOR_TEMPERATURE = "temperature_sensor"
FLOW_SENSOR_MOISTURE = "moisture_sensor"
FLOW_SENSOR_CONDUCTIVITY = "conductivity_sensor"
FLOW_SENSOR_ILLUMINANCE = "illuminance_sensor"
FLOW_SENSOR_HUMIDITY = "humidity_sensor"
FLOW_SENSOR_CO2 = "co2_sensor"
FLOW_SENSOR_POWER_CONSUMPTION = "power_consumption_sensor"
FLOW_SENSOR_PH = "ph_sensor"

FLOW_TEMP_UNIT = "temperature_unit"
FLOW_ILLUMINANCE_TRIGGER = "illuminance_trigger"
FLOW_HUMIDITY_TRIGGER = "humidity_trigger"
FLOW_CO2_TRIGGER = "co2_trigger"
FLOW_TEMPERATURE_TRIGGER = "temperature_trigger"
FLOW_DLI_TRIGGER = "dli_trigger"
FLOW_MOISTURE_TRIGGER = "moisture_trigger"
FLOW_CONDUCTIVITY_TRIGGER = "conductivity_trigger"
FLOW_WATER_CONSUMPTION_TRIGGER = "water_consumption_trigger"
FLOW_FERTILIZER_CONSUMPTION_TRIGGER = "fertilizer_consumption_trigger"
FLOW_POWER_CONSUMPTION_TRIGGER = "power_consumption_trigger"

FLOW_FORCE_SPECIES_UPDATE = "force_update"

ICON_CONDUCTIVITY = "mdi:spa-outline"
ICON_DLI = "mdi:counter"
ICON_HUMIDITY = "mdi:water-percent"
ICON_CO2 = "mdi:molecule-co2"
ICON_ILLUMINANCE = "mdi:brightness-6"
ICON_MOISTURE = "mdi:water"
ICON_PPFD = "mdi:white-balance-sunny"
ICON_TEMPERATURE = "mdi:thermometer"
ICON_WATER_CONSUMPTION = "mdi:water-pump"
ICON_FERTILIZER_CONSUMPTION = "mdi:chart-line-variant"
ICON_POWER_CONSUMPTION = "mdi:flash"
ICON_PH = "mdi:ph"

OPB_GET = "get"
OPB_SEARCH = "search"
OPB_SEARCH_RESULT = "search_result"
OPB_PID = "pid"
OPB_DISPLAY_PID = "display_pid"

# PPFD to DLI: /1000000 * 3600 to get from microseconds to hours
PPFD_DLI_FACTOR = 0.0036
# See https://www.apogeeinstruments.com/conversion-ppfd-to-lux/
# This equals normal sunlight
DEFAULT_LUX_TO_PPFD = 0.0185

SERVICE_REPLACE_SENSOR = "replace_sensor"
SERVICE_REMOVE_PLANT = "remove_plant"
SERVICE_REMOVE_CYCLE = "remove_cycle"
SERVICE_MOVE_TO_AREA = "move_to_area"
SERVICE_EXPORT_PLANTS = "export_plants"
SERVICE_IMPORT_PLANTS = "import_plants"

STATE_LOW = "Low"
STATE_HIGH = "High"
STATE_DLI_LOW = "Previous DLI Low"
STATE_DLI_HIGH = "Previous DLI High"

CONF_MIN_BATTERY_LEVEL = f"min_{ATTR_BATTERY}"
CONF_MIN_TEMPERATURE = f"min_{ATTR_TEMPERATURE}"
CONF_MAX_TEMPERATURE = f"max_{ATTR_TEMPERATURE}"
CONF_MIN_MOISTURE = f"min_{ATTR_MOISTURE}"
CONF_MAX_MOISTURE = f"max_{ATTR_MOISTURE}"
CONF_MIN_CONDUCTIVITY = f"min_{ATTR_CONDUCTIVITY}"
CONF_MAX_CONDUCTIVITY = f"max_{ATTR_CONDUCTIVITY}"
CONF_MIN_ILLUMINANCE = f"min_{ATTR_ILLUMINANCE}"
CONF_MAX_ILLUMINANCE = f"max_{ATTR_ILLUMINANCE}"
CONF_MIN_HUMIDITY = f"min_{ATTR_HUMIDITY}"
CONF_MAX_HUMIDITY = f"max_{ATTR_HUMIDITY}"
CONF_MIN_CO2 = f"min_{ATTR_CO2}"
CONF_MAX_CO2 = f"max_{ATTR_CO2}"
CONF_MIN_MMOL = f"min_{ATTR_MMOL}"
CONF_MAX_MMOL = f"max_{ATTR_MMOL}"
CONF_MIN_MOL = f"min_{ATTR_MOL}"
CONF_MAX_MOL = f"max_{ATTR_MOL}"
CONF_MIN_DLI = f"min_{ATTR_DLI}"
CONF_MAX_DLI = f"max_{ATTR_DLI}"

CONF_MIN_WATER_CONSUMPTION = f"min_{ATTR_WATER_CONSUMPTION}"
CONF_MAX_WATER_CONSUMPTION = f"max_{ATTR_WATER_CONSUMPTION}"
CONF_MIN_FERTILIZER_CONSUMPTION = f"min_{ATTR_FERTILIZER_CONSUMPTION}"
CONF_MAX_FERTILIZER_CONSUMPTION = f"max_{ATTR_FERTILIZER_CONSUMPTION}"
CONF_MIN_POWER_CONSUMPTION = f"min_{ATTR_POWER_CONSUMPTION}"
CONF_MAX_POWER_CONSUMPTION = f"max_{ATTR_POWER_CONSUMPTION}"
CONF_MIN_PH = f"min_{ATTR_PH}"
CONF_MAX_PH = f"max_{ATTR_PH}"

CONF_MIN_BRIGHTNESS = "min_brightness"  # DEPRECATED. Only used for config migration
CONF_MAX_BRIGHTNESS = "max_brightness"  # DEPRECATED. Only used for config migration

CONF_CHECK_DAYS = "check_days"
CONF_STRAIN = "strain"
CONF_IMAGE = "entity_picture"

CONF_PLANTBOOK = "openplantbook"
CONF_PLANTBOOK_MAPPING = {
    CONF_MIN_TEMPERATURE: "min_temp",
    CONF_MAX_TEMPERATURE: "max_temp",
    CONF_MIN_MOISTURE: "min_soil_moist",
    CONF_MAX_MOISTURE: "max_soil_moist",
    CONF_MIN_ILLUMINANCE: "min_light_lux",
    CONF_MAX_ILLUMINANCE: "max_light_lux",
    CONF_MIN_CONDUCTIVITY: "min_soil_ec",
    CONF_MAX_CONDUCTIVITY: "max_soil_ec",
    CONF_MIN_HUMIDITY: "min_env_humid",
    CONF_MAX_HUMIDITY: "max_env_humid",
    CONF_MIN_CO2: "min_env_co2",
    CONF_MAX_CO2: "max_env_co2",
    CONF_MIN_MMOL: "min_light_mmol",
    CONF_MAX_MMOL: "max_light_mmol",
    CONF_MIN_POWER_CONSUMPTION: "min_power_consumption",
    CONF_MAX_POWER_CONSUMPTION: "max_power_consumption",
    # Neue Mappings für Water/Fertilizer Consumption
    CONF_MIN_WATER_CONSUMPTION: "min_water_consumption",
    CONF_MAX_WATER_CONSUMPTION: "max_water_consumption",
    CONF_MIN_FERTILIZER_CONSUMPTION: "min_fertilizer_consumption",
    CONF_MAX_FERTILIZER_CONSUMPTION: "max_fertilizer_consumption",
}

# Growth phases
GROWTH_PHASE_SEEDS = "seeds"
GROWTH_PHASE_GERMINATION = "germination"
GROWTH_PHASE_ROOTING = "rooting"
GROWTH_PHASE_GROWING = "growing"
GROWTH_PHASE_FLOWERING = "flowering"
GROWTH_PHASE_HARVESTED = "harvested"
GROWTH_PHASE_REMOVED = "removed"
DEFAULT_GROWTH_PHASE = GROWTH_PHASE_ROOTING

GROWTH_PHASES = [
    GROWTH_PHASE_SEEDS,
    GROWTH_PHASE_GERMINATION,
    GROWTH_PHASE_ROOTING,
    GROWTH_PHASE_GROWING,
    GROWTH_PHASE_FLOWERING,
    GROWTH_PHASE_HARVESTED,
    GROWTH_PHASE_REMOVED,    # Ans Ende verschoben
]

ATTR_FLOWERING_DURATION = "flowering_duration"
ATTR_ORIGINAL_FLOWERING_DURATION = "original_flowering_duration"  # Neue Konstante für die Original-Blütezeit aus OpenPlantbook

# Neue Konstanten für zusätzliche Pflanzeneigenschaften
ATTR_WEBSITE = "website"
ATTR_INFOTEXT1 = "infotext1"
ATTR_INFOTEXT2 = "infotext2" 
ATTR_EFFECTS = "effects"
ATTR_SMELL = "smell"
ATTR_TASTE = "taste"
ATTR_LINEAGE = "lineage"
ATTR_TYPE = "type"  # Replaces "sorte" for consistency

# Benutzerdefinierte Pflanzenattribute
ATTR_PHENOTYPE = "phenotype"
ATTR_HUNGER = "hunger"
ATTR_GROWTH_STRETCH = "growth_stretch"
ATTR_FLOWER_STRETCH = "flower_stretch"
ATTR_MOLD_RESISTANCE = "mold_resistance"
ATTR_DIFFICULTY = "difficulty"
ATTR_YIELD = "yield"
ATTR_NOTES = "notes"
ATTR_IMAGES = "images"  # Neues Attribut für Bilderliste

# Neue Konstante für den Plant-Erstellungsstatus
ATTR_IS_NEW_PLANT = "is_new_plant"

SERVICE_CREATE_PLANT = "create_plant"

# Neue Konstanten für Device Types
DEVICE_TYPE_PLANT = "plant"
DEVICE_TYPE_CYCLE = "cycle"
DEVICE_TYPE_CONFIG = "config"  # Neuer Gerätetyp für Konfiguration
ATTR_DEVICE_TYPE = "device_type"

DEVICE_TYPES = [
    DEVICE_TYPE_PLANT,
    DEVICE_TYPE_CYCLE
]  # Config wird nicht in der Auswahl angezeigt

# Icons für Device Types
ICON_DEVICE_PLANT = "mdi:flower-outline"
ICON_DEVICE_CYCLE = "mdi:grass"
ICON_DEVICE_CONFIG = "mdi:cog"  # Icon für Konfiguration

SERVICE_MOVE_TO_CYCLE = "move_to_cycle"

SERVICE_CREATE_CYCLE = "create_cycle"

# Aggregation Methoden
AGGREGATION_MEDIAN = "median"
AGGREGATION_MEAN = "mean"
AGGREGATION_MIN = "min"
AGGREGATION_MAX = "max"
AGGREGATION_ORIGINAL = "original"  # Neue Methode für DLI/PPFD Berechnungen

AGGREGATION_METHODS = [
    AGGREGATION_MEDIAN,
    AGGREGATION_MEAN, 
    AGGREGATION_MIN,
    AGGREGATION_MAX
]

# Erweiterte Methoden für DLI/PPFD
AGGREGATION_METHODS_EXTENDED = [
    AGGREGATION_ORIGINAL,  # Original zuerst, da dies der Standardwert sein soll
    AGGREGATION_MEDIAN,
    AGGREGATION_MEAN, 
    AGGREGATION_MIN,
    AGGREGATION_MAX
]

# Default Aggregationen pro Sensor-Typ
DEFAULT_AGGREGATIONS = {
    'temperature': AGGREGATION_MEAN,
    'moisture': AGGREGATION_MEDIAN,
    'conductivity': AGGREGATION_MEDIAN,
    'illuminance': AGGREGATION_MEAN,
    'humidity': AGGREGATION_MEAN,
    'CO2': AGGREGATION_MEAN,
    'ppfd': AGGREGATION_ORIGINAL,
    'dli': AGGREGATION_ORIGINAL,
    'total_integral': AGGREGATION_ORIGINAL,
    'moisture_consumption': AGGREGATION_ORIGINAL,
    'fertilizer_consumption': AGGREGATION_ORIGINAL,
    'total_water_consumption': AGGREGATION_ORIGINAL,
    'total_fertilizer_consumption': AGGREGATION_ORIGINAL,
    'power_consumption': AGGREGATION_MEAN,
    'total_power_consumption': AGGREGATION_ORIGINAL,
    'health': AGGREGATION_MEAN,  # Hinzugefügt für Health Helper
    'ph': AGGREGATION_MEDIAN,  # Neue Default-Aggregation für pH
}

# Config Flow Keys
CONF_AGGREGATION = "aggregation"

# Neue Konstanten für Sensor-Normalisierung
ATTR_NORMALIZE_MOISTURE = "normalize_moisture"
ATTR_NORMALIZE_WINDOW = "normalize_window"
ATTR_NORMALIZE_PERCENTILE = "normalize_percentile"
DEFAULT_NORMALIZE_WINDOW = 7  # Tage
DEFAULT_NORMALIZE_PERCENTILE = 95

# Füge die neue Service-Konstante hinzu
SERVICE_CLONE_PLANT = "clone_plant"

# Neue Konstante für Topfgröße
ATTR_POT_SIZE = "pot_size"
DEFAULT_POT_SIZE = 0.4  # 0,4 Liter als Standardwert

# Neue Konstante für Wasserkapazität
ATTR_WATER_CAPACITY = "water_capacity"
DEFAULT_WATER_CAPACITY = 50  # 50% als Standardwert

# Neue Konstanten für Default-Werte
CONF_DEFAULT_MAX_MOISTURE = "default_max_moisture"
CONF_DEFAULT_MIN_MOISTURE = "default_min_moisture"
CONF_DEFAULT_MAX_ILLUMINANCE = "default_max_illuminance"
CONF_DEFAULT_MIN_ILLUMINANCE = "default_min_illuminance"
CONF_DEFAULT_MAX_DLI = "default_max_dli"
CONF_DEFAULT_MIN_DLI = "default_min_dli"
CONF_DEFAULT_MAX_TEMPERATURE = "default_max_temperature"
CONF_DEFAULT_MIN_TEMPERATURE = "default_min_temperature"
CONF_DEFAULT_MAX_CONDUCTIVITY = "default_max_conductivity"
CONF_DEFAULT_MIN_CONDUCTIVITY = "default_min_conductivity"
CONF_DEFAULT_MAX_HUMIDITY = "default_max_humidity"
CONF_DEFAULT_MIN_HUMIDITY = "default_min_humidity"
CONF_DEFAULT_MAX_CO2 = "default_max_co2"
CONF_DEFAULT_MIN_CO2 = "default_min_co2"

# Neue Default-Konstanten für Water/Fertilizer Consumption
CONF_DEFAULT_MIN_WATER_CONSUMPTION = "default_min_water_consumption"
CONF_DEFAULT_MAX_WATER_CONSUMPTION = "default_max_water_consumption"
CONF_DEFAULT_MIN_FERTILIZER_CONSUMPTION = "default_min_fertilizer_consumption"
CONF_DEFAULT_MAX_FERTILIZER_CONSUMPTION = "default_max_fertilizer_consumption"
CONF_DEFAULT_MIN_POWER_CONSUMPTION = "default_min_power_consumption"
CONF_DEFAULT_MAX_POWER_CONSUMPTION = "default_max_power_consumption"
CONF_DEFAULT_MAX_PH = "default_max_ph"  # Neue Konstanten für pH
CONF_DEFAULT_MIN_PH = "default_min_ph"

ATTR_WATER_CONSUMPTION = "water_consumption"
ATTR_FERTILIZER_CONSUMPTION = "fertilizer_consumption"
ATTR_POWER_CONSUMPTION = "power_consumption"

DEFAULT_KWH_PRICE = 0.3684  # Default kWh Preis in Euro
ATTR_KWH_PRICE = "kwh_price"  # Attribut für den kWh Preis
READING_ENERGY_COST = "energy cost"  # Lesbarer Name für Energiekosten
ICON_ENERGY_COST = "mdi:currency-eur"  # Icon für Energiekosten

# Neue Konstanten für Bild-Download
SERVICE_ADD_IMAGE = "add_image"
FLOW_DOWNLOAD_PATH = "download_path"

# Service to add manual watering entries
SERVICE_ADD_WATERING = "add_watering"
SERVICE_ADD_CONDUCTIVITY = "add_conductivity"
SERVICE_ADD_PH = "add_ph"

# Treatment Options
TREATMENT_NONE = ""
TREATMENT_CUT = "cut"
TREATMENT_SUPER_CROPPING = "super cropping"
TREATMENT_TOPPING = "topping"
TREATMENT_LOLLIPOP = "lollipop"
TREATMENT_FIM = "fim"
TREATMENT_RIB = "rib"
TREATMENT_SPRAY_PEST = "spray pest"
TREATMENT_SPRAY_WATER = "spray water"

TREATMENT_OPTIONS = [
    TREATMENT_CUT,
    TREATMENT_SUPER_CROPPING,
    TREATMENT_TOPPING,
    TREATMENT_LOLLIPOP,
    TREATMENT_FIM,
    TREATMENT_RIB,
    TREATMENT_SPRAY_PEST,
    TREATMENT_SPRAY_WATER,
]

# Health Rating Constants
HEALTH_MIN_VALUE = 0
HEALTH_MAX_VALUE = 5
HEALTH_STEP = 0.5
HEALTH_DEFAULT = HEALTH_MAX_VALUE  # Volle Punktzahl als Standard
CONF_DEFAULT_HEALTH = "default_health"  # Für Config Node

# Neue Konstanten für die Positionierung von Pflanzen
ATTR_POSITION_X = "position_x"
ATTR_POSITION_Y = "position_y"
SERVICE_CHANGE_POSITION = "change_position"
ATTR_POSITION_HISTORY = "position_history"
