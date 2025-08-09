from typing import Any

from duckiebot_hardware_test_ros_interface import AbstractHardwareTestROSInterface


class CameraHardwareTest(AbstractHardwareTestROSInterface):
    def __init__(self, node: Any, test_id: str = "Camera") -> None:
        super().__init__(node, test_id)

    def cb_run_test(self, _):
        return self.format_response_stream(
            success=True,  # does not matter here
            test_topic_name="camera_node/image/compressed",
            test_topic_type="sensor_msgs/CompressedImage",
            lst_blocks=[],
        )

    def get_test_data(self, _: dict) -> dict:
        return {}

    def test_description_expectation(self) -> str:
        return self.html_util_ul(
            [
                "You should see a live camera stream from your Duckiebot displayed below.",
                "Move your Duckiebot in a few directions and confirm that the camera stream is updating with the camera motion.",
            ]
        )

    def test_description_preparation(self) -> str:
        return self.html_util_ul(
            [
                "Place the Duckiebot on a flat surface within your reach, and make sure that the lens cap has been removed from the camera."
            ]
        )
