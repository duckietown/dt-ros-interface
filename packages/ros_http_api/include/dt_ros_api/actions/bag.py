import os
import re
import time
import signal
import datetime
import subprocess
import dataclasses
from enum import IntEnum

from flask import Blueprint, request

from dt_device_utils import get_device_hostname
from dt_ros_api.utils import response_ok, response_error
from dt_ros_api.constants import (
    FILES_API_DIR,
    BAG_RECORDER_DIR,
    BAG_RECORDER_MAX_DURATION_SECS
)


rosbag = Blueprint('rosbag', __name__)
shelf = dict()


@dataclasses.dataclass
class ROSBag:

    class Status(IntEnum):
        INIT = -1
        RECORDING = 0
        POSTPROCESSING = 1
        READY = 2
        ERROR = 10

    @dataclasses.dataclass
    class Recorder:
        process: subprocess.Popen
        pid: int
        pgid: int

    recorder: Recorder
    path: str
    status: Status

TOPIC_RE = re.compile(r"^/[A-Za-z0-9_/]*[A-Za-z0-9_]$")


def _safe_destination_dir(experiment: str):
    base_dir = os.path.abspath(BAG_RECORDER_DIR)
    exp = (experiment or "").strip()
    normalized = os.path.normpath(exp.lstrip('/'))
    if normalized in ("", ".", "..") or normalized.startswith("../"):
        return None
    candidate = os.path.abspath(os.path.join(base_dir, normalized))
    if os.path.commonpath([base_dir, candidate]) != base_dir:
        return None
    return candidate


def _safe_topics(raw_topics: str):
    topics = (raw_topics or "--all").split(":")
    if len(topics) == 1 and topics[0] == "--all":
        return topics
    safe = []
    for topic in topics:
        t = topic.strip()
        if not t:
            return None
        # prevent option injection into rosbag arguments
        if t.startswith('-'):
            return None
        if not TOPIC_RE.match(t):
            return None
        safe.append(t)
    return safe


@rosbag.route('/bag/record/start/<path:experiment>', methods=['POST', 'GET'])
def _rosbag_start(experiment: str):
    # record specified topics, or all if not specified
    if request.method == "POST":
        raw_topics = request.form.get("topics", "--all")
    else:
        raw_topics = request.args.get("topics", "--all")
    topics = _safe_topics(raw_topics)
    if topics is None:
        return response_error("Invalid topics parameter.")

    destination_dir = _safe_destination_dir(experiment)
    if destination_dir is None:
        return response_error("Invalid experiment path.")
    # make sure target directory exists
    subprocess.run(["mkdir", "-p", destination_dir])
    bag_name = datetime.datetime.now().isoformat().replace(':', '_').split('.')[0]
    bag_path = os.path.abspath(os.path.join(destination_dir, f"{bag_name}.bag"))

    # compile command
    cmd = [
        "rosbag",
        "record",
        # this means infinite buffer size
        "--buffsize=0",
        f"--output-name={bag_path}",
        f"--duration={BAG_RECORDER_MAX_DURATION_SECS}",
    ] + topics
    # launch recorder
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp)
    # store Bag recorder info
    bag = ROSBag(
        ROSBag.Recorder(proc, proc.pid, os.getpgid(proc.pid)),
        bag_path,
        ROSBag.Status.RECORDING
    )
    # store bag handler
    shelf[bag_name] = bag
    # return current API rosbag
    return response_ok({
        'name': bag_name,
        'local': bag_path,
        'cmd': cmd
    })


def _is_only_initialized(bag):
    return not os.path.isfile(f"{bag.path}") and not os.path.isfile(f"{bag.path}.active")


def _is_running(bag):
    return bag.recorder.process.poll() is None


def _is_postprocessing(bag):
    return os.path.isfile(f"{bag.path}.active")


def _is_ready(bag):
    return os.path.isfile(f"{bag.path}") and not os.path.isfile(f"{bag.path}.active")


@rosbag.route('/bag/record/status/<string:bag_name>')
def _rosbag_status(bag_name: str):
    bag = shelf.get(bag_name, None)
    if bag is None:
        return response_error(f"No bag with name `{bag_name}` is being recorded")
    # check if the files are there
    if _is_only_initialized(bag):
        bag.status = ROSBag.Status.INIT
    # check if the bag is being recorded
    elif _is_running(bag):
        bag.status = ROSBag.Status.RECORDING
    # check if the bag is being post-processed
    elif _is_postprocessing(bag):
        bag.status = ROSBag.Status.POSTPROCESSING
    # check if the bag is being post-processed
    elif _is_ready(bag):
        bag.status = ROSBag.Status.READY
    else:
        bag.status = ROSBag.Status.ERROR
    # extra data
    extra = {}
    if bag.status == ROSBag.Status.READY:
        bag_uri = os.path.relpath(bag.path, FILES_API_DIR)
        extra['url'] = f'http://{get_device_hostname()}.local/files/data/{bag_uri}'
    # return current API rosbag
    return response_ok({
        'name': bag_name,
        'status': bag.status.name,
        'local': bag.path,
        **extra
    })


@rosbag.route('/bag/record/stop/<string:bag_name>')
def _rosbag_stop(bag_name: str):
    bag = shelf.get(bag_name, None)
    if bag is None:
        return response_error(f"No bag with name `{bag_name}` is being recorded")
    # stop recording
    try:
        os.killpg(bag.recorder.pgid, signal.SIGINT)
    except ProcessLookupError:
        pass
    # wait for the bag to be completed
    while _is_running(bag):
        time.sleep(1)
    # return current API rosbag
    return response_ok({
        'name': bag_name
    })


@rosbag.route('/bag/delete/<string:bag_name>')
def _rosbag_delete(bag_name: str):
    bag: ROSBag = shelf.get(bag_name, None)
    if bag is None:
        return response_error(f"No bag with name `{bag_name}` is being recorded")
    # make sure the recording is over
    if not _is_ready(bag):
        return response_error(f"Bag is still recording")
    # delete recording
    try:
        os.remove(bag.path)
    except BaseException as e:
        return response_error(f"Error: {str(e)}")
    # return current API rosbag
    return response_ok({
        'name': bag_name
    })
