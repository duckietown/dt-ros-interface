#!/bin/bash

source /environment.sh

# YOUR CODE BELOW THIS LINE
# ----------------------------------------------------------------------------


# NOTE: Use the variable DT_PROJECT_PATH to know the absolute path to your code
# NOTE: Use `dt-exec COMMAND` to run the main process (blocking process)

if [ "$ROBOT_HARDWARE" == "raspberry_pi_64" ]; then
    exec roslaunch --wait camera_driver camera_pi5.launch veh:=$VEHICLE_NAME
else
    exec roslaunch --wait camera_driver camera_driver_node.launch veh:=$VEHICLE_NAME
fi


# ----------------------------------------------------------------------------
# YOUR CODE ABOVE THIS LINE
