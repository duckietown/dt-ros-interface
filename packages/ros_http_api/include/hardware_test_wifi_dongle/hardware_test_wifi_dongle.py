from typing import Any

import netifaces
from duckiebot_hardware_test_ros_interface import AbstractHardwareTestROSInterface, HardwareTestJsonParamType


class HardwareTestWiFiDongle(AbstractHardwareTestROSInterface):
    wifi_interface: str

    def __init__(self, node: Any, test_id: str = "USB WiFi Dongle", wifi_interface: str = "wlan0") -> None:
        super().__init__(node, test_id, service_identifier="tests/wifi")
        self.wifi_interface = wifi_interface

    def get_test_data(self, _: dict) -> dict:
        return {}

    def test_description_expectation(self) -> str:
        return self.html_util_ul(
            [
                "The IP address of the <code>wlan0</code> network interface should be displayed below.",
            ]
        )

    def test_description_preparation(self) -> str:
        return self.html_util_ul(
            [
                "Make sure the USB Wifi dongle is plugged in to your Duckiebot and is blinking.",
            ]
        )

    def test_description_log_gather(self) -> str:
        return self.html_util_ul(
            [
                "On your laptop, run the following command to save the logs.",
                "Replace the <code>[path/to/save]</code> to the directory path where you would like to save the logs.",
                "<code>ssh duckie@[ROBOT_NAME].local ifconfig > [path/to/save/]logs-network-ifconfig.txt</code>",
                "(You might need to provide the password to your Duckiebot when prompted.)",
            ]
        )

    def _get_ipv4_addr(self) -> str:
        addresses = netifaces.ifaddresses(self.wifi_interface)
        if netifaces.AF_INET in addresses:
            return addresses[netifaces.AF_INET][0]["addr"]
        return "None"

    def cb_run_test(self, _):
        try:
            response = self._get_ipv4_addr()
            success = True
        except Exception:
            response = ""
            success = False
        lst_block = self.format_obj(
            key=f"Getting the IP of {self.wifi_interface}:",
            value_type=HardwareTestJsonParamType.STRING,
            value=response,
        )
        return self.format_response_object(
            success=success,
            lst_blocks=[lst_block]
        )
