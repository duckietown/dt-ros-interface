# # ! DO NOT MANUALLY INVOKE THIS setup.py, USE CATKIN INSTEAD
from distutils.core import setup
from catkin_pkg.python_setup import generate_distutils_setup

setup_args = generate_distutils_setup(
    packages=["dt_ros_api", "duckiebattery_hardware_test", "wifi_dongle_hardware_test"],
    package_dir={'': 'include'},
)
setup(**setup_args)
