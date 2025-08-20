from typing import Any

import requests
from duckiebot_hardware_test_ros_interface import AbstractHardwareTestROSInterface, HardwareTestJsonParamType


class HardwareTestDuckiebattery(AbstractHardwareTestROSInterface):
    def __init__(self, node: Any, test_id: str = "Duckiebattery") -> None:
        super().__init__(node, test_id, service_identifier="tests/battery")

    def get_test_data(self, _: dict) -> dict:
        return {}

    def test_description_expectation(self) -> str:
        return self.html_util_ul(
            [
                "The Duckiebattery firmware version should be at least <code>2.0.2</code>.",
                "The PCB version should be at least <code>16</code>.",
                "Run the test first with the charging cable plugged in.",
                "Then unplug the charging cable, wait 5 seconds and rerun the test.",
                "If the versions and charging state are correct for both tests, you can then mark the test as Success.",
            ]
        )

    def test_description_log_gather(self) -> str:
        return self.html_util_ul(
            [
                "On your laptop, run the following command to save the logs.",
                "Replace the <code>[path/to/save]</code> to the directory path where you would like to save the logs.",
                "<code>docker -H [ROBOT_NAME].local logs device-health > [path/to/save/]logs-db-device-health.txt</code>",
                "Also on your laptop, run the following commands and save the logs in the terminal to text files.",
                "<code>dts duckiebot battery info [ROBOT_NAME]</code>",
                "<code>dts duckiebot battery check_firmware [ROBOT_NAME]</code>",
            ]
        )

    def test_description_preparation(self) -> str:
        return self.html_util_ul(
            [
                "Place your Duckiebot on a flat surface with the charging cable plugged in."
            ]
        )

    def cb_run_test(self, _):
        try:
            # check versions
            response = requests.get("http://localhost/health/battery/info")
            data_info = response.json()
            # check charging status
            response = requests.get("http://localhost/health/battery")
            data = response.json()
            # format response
            response = self.html_util_ul(
                [
                    f"version: <code>{data_info['version']}</code>",
                    f"boot/pcb_version: <code>{data_info['boot']['pcb_version']}</code>",
                    f"battery/charging: <strong>{data['battery']['charging']}</strong>",
                ]
            )
            success = True
        except Exception:
            response = ""
            success = False
        lst_block = self.format_obj(
            key="Duckiebattery status",
            value_type=HardwareTestJsonParamType.HTML,
            value=response,
        )
        return self.format_response_object(
            success=success,
            lst_blocks=[lst_block],
        )
