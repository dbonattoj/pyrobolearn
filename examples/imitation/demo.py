# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""Imitation learning demonstration using DMPs and ROS with the Franka robot.
"""

import pyrobolearn as prl


# variables
joint_ids = None  # None for all the actuated joints, or you can select which joint you want to move; e.g. [0, 1, 2]
num_basis = 20
rate = 30
use_real_robot = True

# create middleware
ros = prl.middlewares.ROS(subscribe=True, teleoperate=True)
if not use_real_robot:
    ros.disable_middleware()  # disable the middleware if not using the real robot

# create simulator
sim = prl.simulators.Bullet(middleware=ros)

# create basic world (with gravity and floor)
world = prl.worlds.BasicWorld(sim)

# load Franka Emika Panda robot in the world
input("Press Enter to load the robot")
robot = prl.robots.Franka(sim)
world.load_robot(robot)
robot.print_info()

# create state/action
state = prl.states.ExponentialPhaseState(ticks=rate)
action = prl.actions.JointPositionAction(robot, joint_ids=joint_ids)
print("State: {}".format(state))
print("Action: {}".format(action))

# create environment
env = prl.envs.Env(world, state)

# create DMP policy
policy = prl.policies.BioDiscreteDMPPolicy(action, state, num_basis=num_basis, rate=rate)

# create interface/bridge
interface = prl.interfaces.MouseKeyboardInterface(sim)
bridge = prl.bridges.BridgeMouseKeyboardImitationTask(world, interface=interface, verbose=True)

# create recorder
recorder = prl.recorders.StateRecorder(prl.states.JointPositionState(robot, joint_ids=joint_ids), rate=rate)

# create imitation learning task
task = prl.tasks.ILTask(env, policy, interface=bridge, recorders=recorder)

# record, train, and test policy using the policy
# task.run()

# record demonstrations in simulation/reality
print("\nRecording phase: press `ctrl+r` to start/stop the recording. Once finished, press `shift+r`.")
task.record(signal_from_interface=True)
print("Recording phase: finished the recording!")
sim.disable_middleware()  # disable the middleware (get/set info only from/to simulation)

# train policy
input("Press Enter to start the training")
print("Training phase: training the policy...")
task.train(signal_from_interface=False)
print("Training phase: policy trained!")

# plot what the DMP policy has learned by performing a rollout
policy.plot_rollout(nrows=3, ncols=3, suptitle='DMP position trajectories in joint space',
                    titles=['q' + str(i) for i in range(robot.num_actuated_joints)], show=True)

# test policy in simulation
print("Reproduction phase: test policy in simulation...")
# robot.set_home_joint_positions()
task.test(num_steps=rate*100, signal_from_interface=False)
print("Reproduction phase: Policy tested!")

# test policy on real robot
if use_real_robot:
    input("Press Enter to move to the real robot experiment...")
    sim.enable_middleware()  # enable the real robot
    ros.switch_mode(subscribe=False, publish=True, teleoperate=True)
    print("Reproduction phase: test policy in reality...")
    # robot.set_home_joint_positions()
    task.test(num_steps=rate*100, signal_from_interface=False)
    print("Reproduction phase: Policy tested!")
