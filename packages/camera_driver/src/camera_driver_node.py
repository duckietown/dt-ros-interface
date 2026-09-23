#!/usr/bin/env python3

import asyncio
import os
from typing import Optional

import rospy
from duckietown.dtros import DTROS, NodeType, TopicType
from sensor_msgs.msg import CompressedImage as ROSCompressedImage, CameraInfo as ROSCameraInfo

from dt_robot_utils import get_robot_name
from dtps import context, ContextConfig
from dtps_http import RawData
from duckietown_messages.sensors.camera import Camera
from duckietown_messages.calibrations.camera_intrinsic import CameraIntrinsicCalibration
from duckietown_messages.sensors.compressed_image import CompressedImage
from duckietown_messages.utils.exceptions import DataDecodingError

from hardware_test_camera import HardwareTestCamera


class CameraNode(DTROS):
    """
    Relays JPEG frames from a DTPS source.

    Publisher:
        ~image/compressed (:obj:`CompressedImage`): The acquired camera images
        ~camera_info (:obj:`CameraInfo`): The camera parameters

    """

    def __init__(self, camera_name: str = "front_center"):
        # Initialize the DTROS parent class
        super(CameraNode, self).__init__(
            node_name="camera",
            node_type=NodeType.DRIVER,
            help="Reads a stream of images from a camera and publishes the frames over ROS",
        )
        self._robot_name = get_robot_name()
        self._camera_name = camera_name
        self._camera_shm_path = os.environ.get("DT_CAMERA_SHM_IN_PATH", "").strip()
        self._shm_topic_paths = {
            "jpeg": self._camera_shm_path,
            "info": self._topic_shm_path(self._camera_shm_path, ".info"),
            "parameters": self._topic_shm_path(
                self._camera_shm_path,
                ".parameters",
            ),
        }
        topic_shm_only_variables = {
            "jpeg": "DT_CAMERA_SHM_ONLY_JPEG",
            "info": "DT_CAMERA_SHM_ONLY_INFO",
            "parameters": "DT_CAMERA_SHM_ONLY_PARAMETERS",
        }
        self._shm_topic_only = {}
        for topic_name, shm_path in self._shm_topic_paths.items():
            shm_only_variable = topic_shm_only_variables[topic_name]
            shm_only_requested = self._read_boolean_environment(
                shm_only_variable,
                False,
            )
            shm_is_enabled = shm_path != ""
            if shm_only_requested and not shm_is_enabled:
                self.logwarn(
                    f"Ignoring {shm_only_variable}=1 because "
                    "DT_CAMERA_SHM_IN_PATH is not configured."
                )
            self._shm_topic_only[topic_name] = shm_is_enabled and shm_only_requested
        self._topic_handlers = {
            "jpeg": self.publish,
            "info": self.save_camera_info,
            "parameters": self.save_camera_intrinsics,
        }
        # user hardware test
        # self._hardware_test = HardwareTestCamera()
        self.camera_info: Optional[Camera] = None
        self.camera_intrinsics: Optional[CameraIntrinsicCalibration] = None

        # Setup publishers
        self._has_published: bool = False
        self.pub_img = rospy.Publisher(
            "~image/compressed",
            ROSCompressedImage,
            queue_size=1,
            dt_topic_type=TopicType.DRIVER,
            dt_help="The stream of JPEG compressed images from the camera",
        )
        self.time = rospy.Time.now()

        self.pub_camera_info = rospy.Publisher(
            "~camera_info",
            ROSCameraInfo,
            latch=True,
            queue_size=1,
            dt_topic_type=TopicType.DRIVER,
            dt_help="The camera calibration information",
        )
        # ---
        self.loginfo("Initialized.")

    def _read_boolean_environment(self, variable_name: str, default: bool) -> bool:
        """Read a ``0`` or ``1`` transport option and warn for invalid values."""
        default_value = "1" if default else "0"
        variable_value = os.environ.get(variable_name, default_value)
        variable_value = variable_value.strip()
        if variable_value not in ("0", "1"):
            self.logwarn(
                f"{variable_name} must be '0' or '1'; using '{default_value}'."
            )
            return default
        return variable_value == "1"

    @staticmethod
    def _topic_shm_path(base_path: str, suffix: str) -> str:
        """Derive a topic channel path from the compatible JPEG base path."""
        if not base_path:
            return ""
        return base_path + suffix

    def _source_timestamp_to_ros_time(self, timestamp: Optional[float]):
        """Preserve the source camera timestamp in an outgoing ROS header."""
        if timestamp is None:
            return rospy.Time.now()
        try:
            return rospy.Time.from_sec(float(timestamp))
        except (TypeError, ValueError):
            self.logwarn("Camera image has an invalid source timestamp; using ROS publish time.")
            return rospy.Time.now()

    async def publish(self, data: RawData):
        try:
            jpeg: CompressedImage = CompressedImage.from_rawdata(data)
        except DataDecodingError as e:
            self.logerr(f"Failed to decode an incoming message: {e.message}")
            return
        self.time = self._source_timestamp_to_ros_time(jpeg.header.timestamp)
        # create CompressedImage message
        msg: ROSCompressedImage = ROSCompressedImage(
            header=rospy.Header(
                stamp=self.time,
                frame_id=jpeg.header.frame,
            ),
            format=jpeg.format,
            data=jpeg.data,
        )
        # publish image
        self.pub_img.publish(msg)
        self.publish_camera_info()
        # ---
        if not self._has_published:
            self.log("Published the first image.")
            self._has_published = True

    async def save_camera_intrinsics(self, rdata: RawData):
        try:
            self.camera_intrinsics = CameraIntrinsicCalibration.from_rawdata(rdata)
        except DataDecodingError as e:
            self.logerr(f"Failed to decode an incoming message: {e.message}")
            return

    def publish_camera_info(self):
        if self.camera_intrinsics is None:
            self.loginfo(f"No camera intrinsic parameters received by ROS yet")
            return

        if self.camera_info is None:
            self.loginfo(f"No camera information received by ROS yet")
            return

        msg: ROSCameraInfo = ROSCameraInfo(
            header=rospy.Header(
                # TODO: reuse the timestamp from the incoming message
                stamp=self.time,
                frame_id=self.camera_intrinsics.header.frame,
            ),
            width=self.camera_info.width,
            height=self.camera_info.height,
            distortion_model="plumb_bob",
            D=self.camera_intrinsics.D,
            K=self.camera_intrinsics.K,
            R=self.camera_intrinsics.R,
            P=self.camera_intrinsics.P,
        )
        self.pub_camera_info.publish(msg)

    async def save_camera_info(self, rdata: RawData):
        """
        Get the camera specification and save it to a variable.
        """
        try:
            camera: Camera = Camera.from_rawdata(rdata)
        except DataDecodingError as e:
            self.logerr(f"Failed to decode an incoming message: {e.message}")
            self.logwarn("Camera information not available yet.")
            return
        
        if self.camera_info is None:
            self.log("Received camera information.")

        self.camera_info = camera
        
    async def worker(self):
        # create switchboard context
        switchboard = (await context("switchboard")).navigate(self._robot_name)
        camera = switchboard / "sensor" / "camera" / self._camera_name
        subscriptions = []
        try:
            for topic_name, shm_path in self._shm_topic_paths.items():
                shm_only = self._shm_topic_only[topic_name]
                topic_context = camera / topic_name
                if shm_only:
                    self.loginfo(
                        f"Using camera {topic_name} SHM input at '{shm_path}'."
                    )
                else:
                    topic_context = await topic_context.until_ready()
                    topic_context = topic_context.configure(
                        ContextConfig(patient=True)
                    )
                subscription = await topic_context.subscribe(
                    self._topic_handlers[topic_name],
                    shm_path=shm_path or None,
                    shm_only=shm_only,
                )
                subscriptions.append(subscription)
            # create hardware test
            HardwareTestCamera(self)
            await self.join()
        finally:
            for subscription in subscriptions:
                await subscription.unsubscribe()
    
    async def join(self):
        while not self.is_shutdown:
            await asyncio.sleep(1)

    def spin(self):
        try:
            asyncio.run(self.worker())
        except RuntimeError:
            if not self.is_shutdown:
                self.logerr("An error occurred while running the event loop")
                raise


if __name__ == "__main__":
    # initialize the node
    camera_node = CameraNode()
    # keep the node alive
    camera_node.spin()
