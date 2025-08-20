from typing import Any

from dtps import DTPSContext
from duckiebot_hardware_test_ros_interface import AbstractHardwareTestROSInterface


class HardwareTestMotor(AbstractHardwareTestROSInterface):
    duration: int
    info_str: str
    side: str
    speed: float

    def __init__(
        self,
        node: Any,
        info_str: str,
        test_in_queue: DTPSContext,
        speed: float = 0.5,
        duration: int = 3,
    ) -> None:
        self.info_str = info_str
        super().__init__(node, f"Wheel ({self.info_str})", test_in_queue, service_identifier=f"tests/{self.info_str}")
        self.speed = speed
        self.duration = duration

    def get_test_data(self, data: dict) -> dict:
        data.update({
            "info_str": self.info_str,
            "speed": self.speed,
            "duration": self.duration
        })
        return data

    def test_description_expectation(self) -> str:
        return self.html_util_ul(
            [
                f"The {self.info_str} motor should start spinning.",
                f"In about {self.duration} seconds, it should stop moving.",
            ]
        )

    def test_description_preparation(self) -> str:
        return self.html_util_ul(
            [
                "Place your Duckiebot upside down on a flat surface with its wheels in the air.",
                "When you run the test, the wheels will start to spin.",
            ]
        )
