from typing import Any

from dtps import DTPSContext
from duckiebot_hardware_test_ros_interface import AbstractHardwareTestROSInterface


class ButtonHardwareTest(AbstractHardwareTestROSInterface):
    led_blink_hz: int
    led_blink_secs: int

    def __init__(self, node: Any, test_in_queue: DTPSContext, test_id: str = "Top button", test_timeout: int = 60, led_blink_secs: int = 3, led_blink_hz: int = 1) -> None:
        super().__init__(node, test_id, test_in_queue, test_timeout)
        self.led_blink_secs = led_blink_secs
        self.led_blink_hz = led_blink_hz

    def get_test_data(self, data: dict) -> dict:
        data.update({
            "led_blink_secs": self.led_blink_secs,
            "led_blink_hz": self.led_blink_hz
        })
        return data

    def test_description_expectation(self) -> str:
        return self.html_util_ul(
            [
                f"You should see the LED in the power button blink for about {self.led_blink_secs} seconds.",
                "When the LED <strong>stops</strong> blinking, press and release the button to complete the test.",
                "Try performing this test several times to verify that pressing the power button terminates the test promptly.",
            ]
        )

    def test_description_preparation(self) -> str:
        return self.html_util_ul(
            [
                "Place your Duckiebot on a flat surface and locate the power button on the top plate."
            ]
        )
