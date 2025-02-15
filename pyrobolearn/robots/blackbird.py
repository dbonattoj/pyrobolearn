# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""Provide the Blackbird robotic platform.
"""

import os
import numpy as np

from pyrobolearn.robots.legged_robot import BipedRobot

__author__ = "Brian Delhaisse"
__copyright__ = "Copyright 2018, PyRoboLearn"
__license__ = "GNU GPLv3"
__version__ = "1.0.0"
__maintainer__ = "Brian Delhaisse"
__email__ = "briandelhaisse@gmail.com"
__status__ = "Development"


class Blackbird(BipedRobot):
    r"""Blackbird biped robot

    The Blackbird biped robot has been designed by Gabrael Levine [1]. "Blackbird stands 1.2 meters tall and weighs
    roughly 15 kg" [1].

    References:
        - [1] https://hackaday.io/project/160882-blackbird-bipedal-robot
        - [2] https://github.com/G-Levine
    """

    def __init__(self, simulator, position=(0, 0, 1.2), orientation=(0, 0, 0, 1), fixed_base=False, scale=1.,
                 urdf=os.path.dirname(__file__) + '/urdfs/blackbird/blackbird_biped.urdf'):
        """
        Initialize the Blackbird robot.

        Args:
            simulator (Simulator): simulator instance.
            position (np.array[float[3]]): Cartesian world position.
            orientation (np.array[float[4]]): Cartesian world orientation expressed as a quaternion [x,y,z,w].
            fixed_base (bool): if True, the robot base will be fixed in the world.
            scale (float): scaling factor that is used to scale the robot.
            urdf (str): path to the urdf. Do not change it unless you know what you are doing.
        """

        self.height = 1.2
        self.base_height = self.height

        # check parameters
        if position is None:
            position = (0., 0., self.height)
        if len(position) == 2:  # assume x, y are given
            position = tuple(position) + (self.height,)
        if orientation is None:
            orientation = (0, 0, 0, 1)
        if fixed_base is None:
            fixed_base = False

        super(Blackbird, self).__init__(simulator, urdf, position, orientation, fixed_base, scale)
        self.name = 'blackbird'

        # TODO: create constraints in pybullet
        # From the user guide: "URDF, SDF and MJCF specify articulated bodies as a tree-structures without loops.
        # The 'createConstraint' allows you to connect specific links of bodies to close those loops."

        # self.legs = [[self.get_link_ids(link) for link in links if link in self.link_names]
        #              for links in [['left_pelvis_rotation', 'left_hip', 'left_thigh', 'left_knee', 'left_shin',
        #                             'left_tarsus', 'left_toe'],
        #                            ['right_pelvis_rotation', 'right_hip', 'right_thigh', 'right_knee', 'right_shin',
        #                             'right_tarsus', 'right_toe']]]
        #
        # self.feet = [self.get_link_ids(link) for link in ['left_toe', 'right_toe'] if link in self.link_names]
        #
        # # set joint angles to home position
        # self.set_home_joint_positions()

    def get_home_joint_positions(self):
        """Return the joint positions for the home position"""
        return np.array([0, 0, 1.0204, -1.97, -0.084, 2.06, -1.9, 0, 0, 1.0204, -1.97, -0.084, 2.06, -1.9])


if __name__ == "__main__":
    from itertools import count
    from pyrobolearn.simulators import Bullet
    from pyrobolearn.worlds import BasicWorld

    # Create simulator
    sim = Bullet()

    # create world
    world = BasicWorld(sim)

    # create robot
    robot = Blackbird(sim)

    # print information about the robot
    robot.print_info()

    # position control using sliders
    # robot.add_joint_slider()

    # run simulator
    for _ in count():
        # robot.update_joint_slider()
        # robot.move_home_joint_positions()
        world.step(sleep_dt=1./240)
