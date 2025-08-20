from typing import Any

from dtps import DTPSContext
from duckiebot_hardware_test_ros_interface import AbstractHardwareTestROSInterface


class HardwareTestOledDisplay(AbstractHardwareTestROSInterface):
    duration: int
    text: str

    def __init__(self, node: Any, test_in_queue: DTPSContext, test_id: str = "Display", text: str = " Testing... ", duration: int = 5) -> None:
        super().__init__(node, test_id, test_in_queue)
        self.text = text
        self.duration = duration

    def get_test_data(self, data: dict) -> dict:
        data.update({
            "text": self.text,
            "duration": self.duration
        })
        return data

    def test_description_expectation(self) -> str:
        return self.html_util_ul(
            [
                f"Once the test is started, the top display should show: <strong>{self.text}</strong>.",
                f"In about <strong>{self.duration}</strong> seconds, the test page should disappear, and the homepage should be shown again.",
            ]
        )

    def test_description_preparation(self) -> str:
        return self.html_util_ul(
            [
                "Place your Duckiebot on a flat surface with the top screen visible.",
            ]
        )
