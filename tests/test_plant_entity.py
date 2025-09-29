"""Test plant entity functionality in the plant integration."""
import importlib.machinery
import importlib.util
import sys
from pathlib import Path


def _load_module(module_name, file_path):
    """Load a module from a file path."""
    path = Path(file_path).resolve()
    loader = importlib.machinery.SourceFileLoader(module_name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    loader.exec_module(module)
    return module


def test_plant_attributes():
    """Test plant attributes."""
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that key attributes are defined
    assert const.ATTR_PLANT == "plant"
    assert const.ATTR_SENSORS == "sensors"
    assert const.ATTR_METERS == "meters"
    assert const.ATTR_THRESHOLDS == "thresholds"
    assert const.ATTR_PROBLEM == "problem"


def test_plant_device_types():
    """Test plant device types."""
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that device types are defined
    assert const.DEVICE_TYPE_PLANT == "plant"
    assert const.DEVICE_TYPE_CYCLE == "cycle"
    assert const.DEVICE_TYPE_CONFIG == "config"
    
    # Test that device types list contains expected values
    assert "plant" in const.DEVICE_TYPES
    assert "cycle" in const.DEVICE_TYPES


def test_growth_phases():
    """Test growth phases."""
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that growth phases are defined
    assert const.GROWTH_PHASE_SEEDS == "seeds"
    assert const.GROWTH_PHASE_GERMINATION == "germination"
    assert const.GROWTH_PHASE_ROOTING == "rooting"
    assert const.GROWTH_PHASE_GROWING == "growing"
    assert const.GROWTH_PHASE_FLOWERING == "flowering"
    assert const.GROWTH_PHASE_HARVESTED == "harvested"
    assert const.GROWTH_PHASE_REMOVED == "removed"
    
    # Test default growth phase
    assert const.DEFAULT_GROWTH_PHASE == "rooting"
    
    # Test that all growth phases are in the list
    expected_phases = [
        "seeds", "germination", "rooting", "growing", "flowering", "harvested", "removed"
    ]
    
    for phase in expected_phases:
        assert phase in const.GROWTH_PHASES


def test_plant_attributes_extended():
    """Test extended plant attributes."""
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test that extended attributes are defined
    assert const.ATTR_STRAIN == "strain"
    assert const.ATTR_BREEDER == "breeder"
    assert const.ATTR_IMAGE == "image"
    assert const.ATTR_PHENOTYPE == "phenotype"
    assert const.ATTR_HUNGER == "hunger"
    assert const.ATTR_GROWTH_STRETCH == "growth_stretch"
    assert const.ATTR_FLOWER_STRETCH == "flower_stretch"
    assert const.ATTR_MOLD_RESISTANCE == "mold_resistance"
    assert const.ATTR_DIFFICULTY == "difficulty"
    assert const.ATTR_YIELD == "yield"
    assert const.ATTR_NOTES == "notes"
    assert const.ATTR_IMAGES == "images"


def test_plant_config_attributes():
    """Test plant configuration attributes."""
    # Load required modules
    const = _load_module("custom_components.plant.const", "custom_components/plant/const.py")
    
    # Test configuration attributes
    assert const.CONF_MIN_TEMPERATURE == "min_temperature"
    assert const.CONF_MAX_TEMPERATURE == "max_temperature"
    assert const.CONF_MIN_MOISTURE == "min_moisture"
    assert const.CONF_MAX_MOISTURE == "max_moisture"
    assert const.CONF_MIN_CONDUCTIVITY == "min_conductivity"
    assert const.CONF_MAX_CONDUCTIVITY == "max_conductivity"
    
    # Test consumption configuration attributes
    assert const.CONF_MIN_WATER_CONSUMPTION == "min_water_consumption"
    assert const.CONF_MAX_WATER_CONSUMPTION == "max_water_consumption"
    assert const.CONF_MIN_FERTILIZER_CONSUMPTION == "min_fertilizer_consumption"
    assert const.CONF_MAX_FERTILIZER_CONSUMPTION == "max_fertilizer_consumption"
    assert const.CONF_MIN_POWER_CONSUMPTION == "min_power_consumption"
    assert const.CONF_MAX_POWER_CONSUMPTION == "max_power_consumption"
    assert const.CONF_MIN_PH == "min_ph"
    assert const.CONF_MAX_PH == "max_ph"