from typing import Any

from duckiebot_hardware_test_ros_interface import AbstractHardwareTestROSInterface


class HardwareTestToF(AbstractHardwareTestROSInterface):
    sensor_name: str

    def __init__(self, node: Any, sensor_name: str) -> None:
        self.sensor_name = sensor_name
        super().__init__(node, f"Time-of-Flight ({self.sensor_name})")

    def cb_run_test(self, _):
        return self.format_response_stream(
            success=True,  # does not matter here
            test_topic_name=f"{self.sensor_name}_tof_driver_node/range",
            test_topic_type="sensor_msgs/Range",
            lst_blocks=[],
        )

    def get_test_data(self, _: dict) -> dict:
        return {}

    def test_description_expectation(self) -> str:
        sensor_name_human = self.sensor_name.replace("_", " ")
        return self.html_util_ul(
            [
                "Once your start the test, a <strong>Range:</strong> field will appear below.",
                f"When you move your hand closer and farther to the <strong>{sensor_name_human}</strong> ToF, the range reading should change accordingly, i.e. moving closer leads to a smaller value, and farther with a greater value.",
                "The data below should show (in red color) <em>Out of range</em>.",
            ]
        )

    def test_description_preparation(self) -> str:
        return self.html_util_ul(
            [
                "Place your Duckiebot on a flat surface with at least one meter of empty space in front of the Time-of-Flight sensor on the front bumper.",
            ]
        )
