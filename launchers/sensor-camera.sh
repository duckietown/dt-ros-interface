#!/bin/bash

source /environment.sh

# Initialize launch file.
dt-launchfile-init

# YOUR CODE BELOW THIS LINE
# ----------------------------------------------------------------------------

if [ "$ROBOT_HARDWARE" == "raspberry_pi_64" ]; then
    exec roslaunch --wait camera_driver camera_pi5.launch veh:=$VEHICLE_NAME
else
    exec roslaunch --wait camera_driver camera_driver_node.launch veh:=$VEHICLE_NAME
fi

# ----------------------------------------------------------------------------
# YOUR CODE ABOVE THIS LINE

# Wait for app to end.
dt-launchfile-join
