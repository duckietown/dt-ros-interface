#!/usr/bin/env python3

"""The Image Relayer node."""

import asyncio
from typing import Dict, List, Tuple, Type

import rospy
from dt_node_utils.node import Node, NodeType
from dt_robot_utils import get_robot_name
from dtps import ContextConfig, DTPSContext, PublisherInterface
from dtps_http import RawData
from duckietown.dtros import DTROS, NodeType as ROSNodeType, TopicType
from duckietown_messages.sensors.compressed_image import CompressedImage
from duckietown_messages.standard.dictionary import Dictionary
from sensor_msgs.msg import CompressedImage as ROSCompressedImage

ROBOT_NAME = get_robot_name()


class ImageRelayerNode(Node):
    """Relays images from ROS to DTPS.

    Args:
        name (:obj:`str`): The name of the node.
    """

    def __init__(self, name: str):
        super().__init__(name, NodeType.DRIVER, "A ROS to DTPS image relayer.")
        self._dtps_topics: List[str]
        self._ros_topics: List[List[str]]
        self._queues: Dict[str, DTPSContext]
        self._subscriber: Type[rospy.Subscriber] | None = None
        self._publisher: PublisherInterface | None = None
        self.loginfo("Initialized.")

    @staticmethod
    def _get_topics() -> Tuple[List[str], List[List[str]]]:
        """Returns the relavent DTPS and ROS image topics.

        :return: The relavent DTPS and ROS image topics.
        :rtype:  :obj:`Tuple[List[str], List[List[str]]]`
        """
        dtps_topics = ["topic_of_interest"]
        ros_topics = rospy.client.get_published_topics()
        for ros_topic in ros_topics:
            if (ros_topic[1] == "sensor_msgs/CompressedImage"
                    and "/camera_node/" not in ros_topic[0]):
                split_dtps_topic = ros_topic[0].split("/")[2 : -1] + ["jpeg"]
                dtps_topics.append("/".join(split_dtps_topic))
        return dtps_topics, ros_topics

    async def _initialize_queues(self) -> None:
        """Initializes the DTPS queues."""
        await self.dtps_init()
        self._dtps_topics, self._ros_topics = self._get_topics()
        await self._set_up_queues()
        await self.dtps_expose()

    def _on_compressed_image_message(self,
                                     message: ROSCompressedImage) -> None:
        """Handles compressed image messages from ROS.

        :param message: (:obj:`ROSCompressedImage`): Compressed image
        message.
        """
        raw_data = CompressedImage(format="jpeg",
                                   data=message.data).to_rawdata()
        asyncio.run_coroutine_threadsafe(self._publisher.publish(raw_data),
                                         self._event_loop)

    async def _on_topic_of_interest_data(self, raw_data: RawData) -> None:
        """Handles raw data from the
        `switchboard/vehicle_name/node/image_relayer/topic_of_interest`
        queue.

        :param raw_data: (:obj:`RawData`): Raw data from the
        `switchboard/vehicle_name/node/image_relayer/topic_of_interest`
        queue.
        """
        if self._subscriber:
            self._subscriber.unregister()
        if self._publisher:
            await self._publisher.terminate()
        dictionary = Dictionary.from_rawdata(raw_data)
        if "/image_relayer/" not in dictionary.data["topic"]:
            return None
        topic = dictionary.data["topic"].split("/image_relayer/")[1]
        self._publisher = await self._queues[topic].publisher()
        ros_topic = f"/{ROBOT_NAME}/{topic[: -5]}/compressed"
        self._subscriber = rospy.Subscriber(ros_topic,
                                            ROSCompressedImage,
                                            self._on_compressed_image_message,
                                            queue_size=1,
                                            dt_topic_type=TopicType.DRIVER)

    async def _set_up_queues(self) -> None:
        """Sets up the DTPS queues."""
        self._queues = {}
        for topic in self._dtps_topics:
            queue = await (self.context / topic).queue_create()
            self._queues[topic] = queue.configure(ContextConfig(patient=True))
        await self._queues["topic_of_interest"].subscribe(
            self._on_topic_of_interest_data)

    async def worker(self) -> None:
        """`worker` function."""
        await self._initialize_queues()
        while not self.is_shutdown:
            if rospy.client.get_published_topics() != self._ros_topics:
                for topic in self._dtps_topics:
                    await self._queues[topic].remove()
                self._dtps_topics, self._ros_topics = self._get_topics()
                await self._set_up_queues()
            await asyncio.sleep(1)
        self.loginfo("Worker has stopped.")


class ImageRelayerROSNode(DTROS):
    """Relays images from ROS to DTPS.

    Args:
        node_name (:obj:`str`): The name of the node.
    """

    def __init__(self, node_name: str):
        super().__init__(node_name, ROSNodeType.DRIVER,
                         "A ROS to DTPS image relayer.")
        image_relayer_node = ImageRelayerNode(node_name)
        self.loginfo("Initialized.")
        image_relayer_node.spin()


if __name__ == "__main__":
    ImageRelayerROSNode("image_relayer")
