#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2023 Bitcraze AB
#
#  Crazyflie Python Library
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
Example script that makes the Crazyflie follow a wall

This examples uses the Flow and Multi-ranger decks to measure distances
in all directions and do wall following. Straight walls with corners
are advised to have in the test environment.
This is a python port of c-based app layer example from the Crazyflie-firmware
found here https://github.com/bitcraze/crazyflie-firmware/tree/master/examples/
demos/app_wall_following_demo

For the example to run the following hardware is needed:
 * Crazyflie 2.0
 * Crazyradio PA
 * Flow deck
 * Multiranger deck
"""
import logging
import sys
import time

from wall_following.wall_following import WallFollowing

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper
from cflib.utils.multiranger import Multiranger

URI = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

if len(sys.argv) > 1:
    URI = sys.argv[1]

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

wall_following = WallFollowing(
    angle_value_buffer=0.1, ref_distance_from_wall=0.3,
    max_forward_speed=0.3, init_state=WallFollowing.StateWF.FORWARD)


if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    # Setup logging to get the yaw data
    lg_stab = LogConfig(name='Stabilizer', period_in_ms=100)
    lg_stab.add_variable('stabilizer.yaw', 'float')

    cf = Crazyflie(rw_cache='./cache')
    with SyncCrazyflie(URI, cf=cf) as scf:
        with MotionCommander(scf) as motion_commander:
            with Multiranger(scf) as multiranger:
                with SyncLogger(scf, lg_stab) as logger:

                    keep_flying = True
                    while keep_flying:

                        # initialize variables
                        velocity_x = 0.0
                        velocity_y = 0.0
                        yaw_rate = 0.0
                        state_wf = WallFollowing.StateWF.HOVER

                        # Get Yaw
                        log_entry = logger.next()
                        data = log_entry[1]
                        actual_yaw = data['stabilizer.yaw']
                        actual_yaw_rad = actual_yaw * 3.1415 / 180

                        # get front range in milimeters
                        front_range = multiranger.front
                        if front_range is None:
                            front_range = 999

                        # get top range in milimeters
                        top_range = multiranger.up
                        if top_range is None:
                            top_range = 999

                        # choose here the direction that you want the wall following to turn to
                        #     direction = -1 turning right and follow wall with left-range
                        #    direction = 1 turning left and follow wall with right-range
                        direction = -1
                        side_range = multiranger.left  # Get range in milimeters
                        if side_range is None:
                            side_range = 999

                        # get velocity commands and current state from wall following state machine
                        velocity_x, velocity_y, yaw_rate, state_wf = wall_following.wall_follower(
                            front_range, side_range, actual_yaw_rad, -1, time.time())

                        print('velocity_x', velocity_x, 'velocity_y', velocity_y,
                              'yaw_rate', yaw_rate, 'state_wf', state_wf)

                        # convert yaw_rate from rad to deg
                        # the negative sign is because of this ticket:
                        #    https://github.com/bitcraze/crazyflie-lib-python/issues/389
                        yaw_rate_deg = -1*yaw_rate * 180 / 3.1415

                        motion_commander.start_linear_motion(
                            velocity_x, velocity_y, 0, rate_yaw=yaw_rate_deg)

                        # if spacebar is pressed, stop the demo
                        if top_range < 0.2:
                            keep_flying = False