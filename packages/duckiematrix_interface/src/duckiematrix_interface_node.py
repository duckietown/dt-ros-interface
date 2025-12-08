#!/usr/bin/env python3

import asyncio

import rospy
from geometry_msgs.msg import Quaternion

from dt_robot_utils import get_robot_name
from dtps import context
from dtps_http import RawData
from duckietown.dtros import DTROS, NodeType
from duckietown_messages.utils.exceptions import DataDecodingError
from duckietown_messages.geometry_3d import Transformation, Twist as DTTwist

from geometry_msgs.msg import Point, Pose, PoseWithCovariance, TwistWithCovariance, Twist
from nav_msgs.msg import Odometry

from tf.transformations import (
    quaternion_inverse,
    quaternion_multiply,
    euler_from_quaternion
)


class DuckieMatrixInterfaceNode(DTROS):

    def __init__(self):
        super(DuckieMatrixInterfaceNode, self).__init__(
            node_name="duckiematrix_interface_node",
            node_type=NodeType.DIAGNOSTICS
        )
        self._robot_name = get_robot_name()

        # Publishers
        self._state_pub = rospy.Publisher("~state", Odometry, queue_size=1)

        # Internal state for twist calculation
        self._previous_pose = None
        self._previous_stamp = None

    async def publish_pose(self, data: RawData):
        # decode data
        try:
            pose: Transformation = Transformation.from_rawdata(data)  # type: ignore
        except DataDecodingError as e:
            self.logerr(f"Failed to decode an incoming message: {e.message}")
            return

        # Convert to ROS Pose
        pose_ros = Pose()
        pose_ros.position = Point(pose.position.x, pose.position.y, pose.position.z)
        pose_ros.orientation = Quaternion(
            pose.rotation.x,
            pose.rotation.y,
            pose.rotation.z,
            pose.rotation.w
        )

        # Update internal state
        self._previous_pose = pose_ros
        self._previous_stamp = rospy.Time.now()

    async def publish_twist(self, data: RawData):
        # decode data
        try:
            twist_data = DTTwist.from_rawdata(data)  # Assuming twist data is directly decodable
        except DataDecodingError as e:
            self.logerr(f"Failed to decode an incoming message: {e.message}")
            return

        # Create Twist message
        twist = Twist()
        twist.linear.x = twist_data.linear_velocity.x
        twist.linear.y = twist_data.linear_velocity.y
        twist.linear.z = twist_data.linear_velocity.z
        twist.angular.x = twist_data.angular_velocity.x
        twist.angular.y = twist_data.angular_velocity.y
        twist.angular.z = twist_data.angular_velocity.z

        # Create odometry message
        current_stamp = rospy.Time.now()
        odom_msg = Odometry(
            header=rospy.Header(
                stamp=current_stamp,
                frame_id='map',
            ),
            child_frame_id='base_link',
            pose=PoseWithCovariance(
                pose=self._previous_pose
            ),
            twist=TwistWithCovariance(
                twist=twist)
        )

        # Publish messages
        self._state_pub.publish(odom_msg)
        rospy.loginfo_once("Begun publishing odometry messages")

    async def worker(self):
        # create switchboard context
        switchboard = (await context("switchboard")).navigate(self._robot_name)
        # pose and twist queues
        pose_topic = await (switchboard / "state" / "pose").until_ready()
        twist_topic = await (switchboard / "state" / "twist").until_ready()
        rospy.logdebug("Detected pose and twist topics")
        # subscribe
        await pose_topic.subscribe(self.publish_pose)
        await twist_topic.subscribe(self.publish_twist)
        rospy.logdebug("Subscribed to pose and twist topics")
        
        # ---
        await self.join()

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

    def on_shutdown(self):
        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        if loop is not None:
            self.loginfo("Shutting down the event loop")
            loop.stop()


if __name__ == '__main__':
    node = DuckieMatrixInterfaceNode()
    node.spin()
