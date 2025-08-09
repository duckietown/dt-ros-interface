from typing import Any, List

from dtps import DTPSContext
from duckiebot_hardware_test_ros_interface import AbstractHardwareTestROSInterface

TEST_TIMEOUT_BUFFER = 3


class LEDHardwareTest(AbstractHardwareTestROSInterface):
    duration: int
    fade_in_duration: int
    fade_out_duration: int
    info_str: str
    led_ids: List[int]
    test_in_queue: DTPSContext
    test_out_queue: DTPSContext

    def __init__(
        self,
        node: Any,
        info_str: str,
        test_in_queue: DTPSContext,
        led_ids: List[int],
        fade_in_duration: int = 1,
        duration: int = 3,
        fade_out_duration: int = 1,
    ) -> None:
        self.info_str = info_str
        test_timeout = fade_in_duration + duration + fade_out_duration + TEST_TIMEOUT_BUFFER
        super().__init__(node, f"LEDs ({self.info_str})", test_in_queue, test_timeout, service_identifier=f"tests/{self.info_str}")
        self.led_ids = led_ids
        self.fade_in_duration = fade_in_duration
        self.duration = duration
        self.fade_out_duration = fade_out_duration

    def get_test_data(self, data: dict) -> dict:
        data.update({
            "led_ids": self.led_ids,
            "fade_in_duration": self.fade_in_duration,
            "duration": self.duration,
            "fade_out_duration": self.fade_out_duration
        })
        return data

    def test_description_expectation(self) -> str:
        return self.html_util_ul(
            [
                "The Duckiebot LEDs should start shining.",
                "The LEDs should show a smooth transition of these colors: "
                "RED -> YELLOW -> GREEN -> BLUE -> PURPLE -> RED.",
                f"In about {self.fade_in_duration + self.duration + self.fade_out_duration} seconds, "
                f"they should be off.",
            ]
        )

    def test_description_preparation(self) -> str:
        return self.html_util_ul(
            [
                f"Place your Duckiebot on a flat surface in a position that allows you to see the {self.info_str} LEDs.",
            ]
        )
