#!/bin/bash

source /environment.sh

# YOUR CODE BELOW THIS LINE
# ----------------------------------------------------------------------------


# NOTE: Use the variable DT_PROJECT_PATH to know the absolute path to your code
# NOTE: Use `dt-exec COMMAND` to run the main process (blocking process)


# launch robot-type specific launcher
exec dt-launcher-default-${ROBOT_TYPE}


# ----------------------------------------------------------------------------
# YOUR CODE ABOVE THIS LINE
