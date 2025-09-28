import py_compile
from pathlib import Path


def test_sensor_module_compiles():
    path = Path("custom_components/plant/sensor.py").resolve()
    py_compile.compile(str(path), doraise=True)

