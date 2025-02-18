#!/usr/bin/env python3

import asyncio

import rospy
from geometry_msgs.msg import Quaternion

from dt_robot_utils import get_robot_name
from dtps import context
from dtps_http import RawData
from duckietown.dtros import DTROS, NodeType
from duckietown_messages.utils.exceptions import DataDecodingError
from duckietown_messages.geometry_3d import Transformation

from geometry_msgs.msg import Point, Pose, PoseWithCovariance
from nav_msgs.msg import Odometry

from geometry_msgs.msg import Pose, Twist
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

    @staticmethod
    def compute_twist_from_pose(current_pose: Pose, previous_pose: Pose, dt: float) -> Twist:
        """
        Compute a naive twist (linear & angular velocity) from two Pose objects
        and a time difference using a first-order finite difference.

        :param current_pose: The current Pose.
        :param previous_pose: The previous Pose.
        :param dt: Time difference between the poses in seconds.
        :return: geometry_msgs/Twist representing the estimated velocity.
        """

        twist = Twist()

        # Guard against division-by-zero or near-zero
        if dt <= 1.0e-9:
            # Return a zero Twist if dt is too small
            return twist

        # --- 1. Compute linear velocity (in world frame) ---
        dx = current_pose.position.x - previous_pose.position.x
        dy = current_pose.position.y - previous_pose.position.y
        dz = current_pose.position.z - previous_pose.position.z

        twist.linear.x = dx / dt
        twist.linear.y = dy / dt
        twist.linear.z = dz / dt

        # --- 2. Compute angular velocity ---
        # Extract quaternions [x, y, z, w]
        q_current = [
            current_pose.orientation.x,
            current_pose.orientation.y,
            current_pose.orientation.z,
            current_pose.orientation.w
        ]
        q_previous = [
            previous_pose.orientation.x,
            previous_pose.orientation.y,
            previous_pose.orientation.z,
            previous_pose.orientation.w
        ]

        # Compute the difference quaternion q_diff = q_prev^-1 * q_current
        # Then normalize for numerical stability
        q_inv_prev = quaternion_inverse(q_previous)
        q_diff = quaternion_multiply(q_inv_prev, q_current)

        # Convert that difference quaternion to Euler angles (roll, pitch, yaw)
        roll, pitch, yaw = euler_from_quaternion(q_diff)

        # The Euler angles represent the rotation that happened over dt
        twist.angular.x = roll  / dt
        twist.angular.y = pitch / dt
        twist.angular.z = yaw   / dt

        return twist

    async def publish(self, data: RawData):
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

        # Create odometry message
        # TODO: If you receive a proper timestamp from the incoming data, use it instead of rospy.Time.now()
        current_stamp = rospy.Time.now()
        odom_msg = Odometry(
            header=rospy.Header(
                stamp=current_stamp,
                frame_id='map',
            ),
            child_frame_id='base_link',
            pose=PoseWithCovariance(
                pose=pose_ros
            )
        )

        # Compute the twist if we have a previous pose and timestamp
        if self._previous_pose is not None and self._previous_stamp is not None:
            dt = (current_stamp - self._previous_stamp).to_sec()
            twist = self.compute_twist_from_pose(pose_ros, self._previous_pose, dt)
            odom_msg.twist.twist = twist

        # Update internal state
        self._previous_pose = pose_ros
        self._previous_stamp = current_stamp

        # Publish messages
        self._state_pub.publish(odom_msg)
        rospy.loginfo_once("Begun publishing odometry messages")

    async def worker(self):
        # create switchboard context
        switchboard = (await context("switchboard")).navigate(self._robot_name)
        # wheel encoder queue
        pose_topic = await (switchboard / "pose").until_ready()
        rospy.logdebug("Detected pose topic")
        # subscribe
        await pose_topic.subscribe(self.publish)
        rospy.logdebug("Subscribed to pose topic")
        
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
