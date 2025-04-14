#!/usr/bin/env python3
"""The Control Mapper node."""

import asyncio

import dtps
import rospy
from dt_robot_utils import get_robot_name
from dtps_http import RawData
from duckietown.dtros import DTROS, TopicType
from duckietown.dtros import NodeType as ROSNodeType
from duckietown_messages.standard.boolean import Boolean
from duckietown_messages.utils.exceptions import DataDecodingError
from duckietown_msgs.msg import BoolStamped


class ControlMapperNode(DTROS):
    """Control Mapper node."""

    _joystick_override_publisher: rospy.Publisher
    _robot_name: str
    is_shutdown: bool

    def __init__(self) -> None:
        """Initialize Control Mapper node."""
        super().__init__(
            "control_mapper",
            ROSNodeType.MAPPING,
            "A control mapper.",
        )
        self._robot_name = get_robot_name()
        self._joystick_override_publisher = rospy.Publisher(
            f"/{self._robot_name}/joy_mapper_node/joystick_override",
            BoolStamped,
            queue_size=1,
            dt_topic_type=TopicType.MAPPING,
        )
        self.loginfo("Initialized.")

    async def _join(self) -> None:
        """Join."""
        while not self.is_shutdown:
            await asyncio.sleep(1)

    async def _on_autopilot(self, raw_data: RawData) -> None:
        try:
            autopilot: Boolean = Boolean.from_rawdata(raw_data)
        except DataDecodingError as error:
            self.logerr(
                f"Failed to decode an incoming message: {error.message}",
            )
            return
        joystick_override_message = BoolStamped(
            header=rospy.Header(
                stamp=rospy.Time.now(),
            ),
            data=not autopilot.data,
        )
        self._joystick_override_publisher.publish(joystick_override_message)

    def spin(self) -> None:
        """Spin."""
        try:
            asyncio.run(self.worker())
        except RuntimeError:
            if not self.is_shutdown:
                self.logerr("An error occurred while running the event loop.")
                raise

    async def worker(self) -> None:
        """Worker."""
        self.loginfo("Retrieving switchboard context...")
        switchboard = await dtps.context("switchboard")
        self.loginfo("Switchboard context retrieved.")
        self.loginfo("Waiting for DTPS queues to come online...")
        autopilot_queue = await (
            switchboard
            / self._robot_name
            / "node"
            / "control_mapper"
            / "autopilot"
        ).until_ready()
        self.loginfo("DTPS queues have come online.")
        self.loginfo("Subscribing to DTPS queues...")
        await autopilot_queue.subscribe(self._on_autopilot)
        self.loginfo("Subscribed to DTPS queues.")
        self.loginfo("Running...")
        await self._join()
        self.loginfo("Shutting down...")


if __name__ == "__main__":
    node = ControlMapperNode()
    node.spin()
