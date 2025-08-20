from typing import Any

from duckiebot_hardware_test_ros_interface import AbstractHardwareTestROSInterface


class HardwareTestWheelEncoder(AbstractHardwareTestROSInterface):
    info_str: str

    def __init__(self, node: Any, info_str: str) -> None:
        self.info_str = info_str
        super().__init__(node, f"Wheel Encoder ({self.info_str})")

    def cb_run_test(self, _):
        return self.format_response_stream(
            success=True,  # does not matter here
            test_topic_name=f"{self.info_str}_wheel_encoder_driver_node/tick",
            test_topic_type="duckietown_msgs/WheelEncoderStamped",
            lst_blocks=[],
        )

    def get_test_data(self, _: dict) -> dict:
        return {}

    def test_description_expectation(self) -> str:
        return self.html_util_ul(
            [
                "Once your start the test, a <strong>Tick value</strong> field will appear below.",
                f"When you turn the {self.info_str} wheel, if the value changes according to your movement rate, the test is passed.",
                "(The change of directions would not be reflected.)",
            ]
        )

    def test_description_preparation(self) -> str:
        return self.html_util_ul(
            [
                "Put your Duckiebot upside down, where you can reach and turn the wheels by hand.",
            ]
        )
