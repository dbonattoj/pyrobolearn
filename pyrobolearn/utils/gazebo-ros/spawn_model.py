# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2013 Open Source Robotics Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Desc: helper script for spawning models in gazebo
# Author: John Hsu, Dave Coleman
#

import rospy, sys, os, time
import string
import warnings
import re

from gazebo_ros import gazebo_interface

from gazebo_msgs.msg import *
from gazebo_msgs.srv import *
from std_srvs.srv import Empty
from geometry_msgs.msg import Point, Pose, Quaternion, Twist, Wrench
import tf.transformations as tft

model_database_template = """<sdf version="1.4">
  <world name="default">
    <include>
      <uri>model://MODEL_NAME</uri>
    </include>
  </world>
</sdf>"""

def usage():
    print('''Commands:
    -[urdf|sdf|trimesh|gazebo] - specify incoming xml is urdf, sdf or trimesh format. gazebo arg is deprecated in ROS Hydro
    -[file|param|database] [<file_name>|<param_name>|<model_name>] - source of the model xml or the trimesh file
    -model <model_name> - name of the model to be spawned.
    -reference_frame <entity_name> - optinal: name of the model/body where initial pose is defined.
                                     If left empty or specified as "world", gazebo world frame is used.
    -gazebo_namespace <gazebo ros_namespace> - optional: ROS namespace of gazebo offered ROS interfaces.  Defaults to /gazebo/ (e.g. /gazebo/spawn_model).
    -robot_namespace <robot ros_namespace> - optional: change ROS namespace of gazebo-plugins.
    -unpause - optional: !!!Experimental!!! unpause physics after spawning model
    -wait - optional: !!!Experimental!!! wait for model to exist
    -trimesh_mass <mass in kg> - required if -trimesh is used: linear mass
    -trimesh_ixx <moment of inertia in kg*m^2> - required if -trimesh is used: moment of inertia about x-axis
    -trimesh_iyy <moment of inertia in kg*m^2> - required if -trimesh is used: moment of inertia about y-axis
    -trimesh_izz <moment of inertia in kg*m^2> - required if -trimesh is used: moment of inertia about z-axis
    -trimesh_gravity <bool> - required if -trimesh is used: gravity turned on for this trimesh model
    -trimesh_material <material name as a string> - required if -trimesh is used: E.g. Gazebo/Blue
    -trimesh_name <link name as a string> - required if -trimesh is used: name of the link containing the trimesh
    -x <x in meters> - optional: initial pose, use 0 if left out
    -y <y in meters> - optional: initial pose, use 0 if left out
    -z <z in meters> - optional: initial pose, use 0 if left out
    -R <roll in radians> - optional: initial pose, use 0 if left out
    -P <pitch in radians> - optional: initial pose, use 0 if left out
    -Y <yaw in radians> - optional: initial pose, use 0 if left out
    -J <joint_name joint_position> - optional: initialize the specified joint at the specified value
    -package_to_model - optional: convert urdf <mesh filename="package://..." to <mesh filename="model://..."
    -b - optional: bond to gazebo and delete the model when this program is interrupted
    ''')
    sys.exit(1)

class SpawnModel():
    def __init__(self):
        self.initial_xyz             = [0,0,0]
        self.initial_rpy             = [0,0,0]
        self.initial_q               = [0,0,0,1]
        self.file_name               = ""
        self.param_name              = ""
        self.database_name           = ""
        self.model_name              = ""
        self.robot_namespace         = rospy.get_namespace()
        self.gazebo_namespace        = "/gazebo"
        self.reference_frame         = ""
        self.unpause_physics         = False
        self.wait_for_model          = ""
        self.wait_for_model_exists   = False
        self.urdf_format             = False
        self.sdf_format              = False
        self.joint_names             = []
        self.joint_positions         = []
        self.package_to_model        = False
        self.bond                    = False

    def parseUserInputs(self):
        # get goal from commandline
        for i in range(0,len(sys.argv)):
          if sys.argv[i] == '-h' or sys.argv[i] == '--help' or sys.argv[i] == '-help':
            usage()
            sys.exit(1)
          if sys.argv[i] == '-unpause':
            self.unpause_physics = True
          if sys.argv[i] == '-urdf':
            if self.sdf_format == True:
                rospy.logerr("Error: you cannot specify both urdf and sdf format xml, must pick one")
                sys.exit(0)
            else:
              self.urdf_format = True;
          if sys.argv[i] == '-sdf' or sys.argv[i] == '-gazebo':
            if self.urdf_format == True:
                rospy.logerr("Error: you cannot specify both urdf and sdf format xml, must pick one")
                sys.exit(0)
            else:
                if sys.argv[i] == '-gazebo':
                    rospy.logwarn("Deprecated: the -gazebo tag is now -sdf")
                    warnings.warn("Deprecated: the -gazebo tag is now -sdf", DeprecationWarning)
                self.sdf_format = True;
          if sys.argv[i] == '-J':
            if len(sys.argv) > i+2:
              self.joint_names.append(sys.argv[i+1])
              self.joint_positions.append(float(sys.argv[i+2]))
            else:
              rospy.logerr("Error: must specify a joint name and joint value pair")
              sys.exit(0)
          if sys.argv[i] == '-param':
            if len(sys.argv) > i+1:
              if self.file_name != "" or self.database_name != "":
                rospy.logerr("Error: you cannot specify file name if parameter or database name is given, must pick one source of model xml")
                sys.exit(0)
              else:
                self.param_name = sys.argv[i+1]
          if sys.argv[i] == '-file':
            if len(sys.argv) > i+1:
              if self.param_name != "" or self.database_name != "":
                rospy.logerr("Error: you cannot specify parameter if file or database name is given, must pick one source of model xml")
                sys.exit(0)
              else:
                self.file_name = sys.argv[i+1]
          if sys.argv[i] == '-database':
            if len(sys.argv) > i+1:
              if self.param_name != "" or self.file_name != "":
                rospy.logerr("Error: you cannot specify parameter if file or parameter name is given, must pick one source of model xml")
                sys.exit(0)
              else:
                self.database_name = sys.argv[i+1]
          if sys.argv[i] == '-model':
            if len(sys.argv) > i+1:
              self.model_name = sys.argv[i+1]
          if sys.argv[i] == '-wait':
            if len(sys.argv) > i+1:
              self.wait_for_model = sys.argv[i+1]
          if sys.argv[i] == '-reference_frame':
            if len(sys.argv) > i+1:
              self.reference_frame = sys.argv[i+1]
          if sys.argv[i] == '-robot_namespace':
            if len(sys.argv) > i+1:
              self.robot_namespace = sys.argv[i+1]
          if sys.argv[i] == '-namespace':
            if len(sys.argv) > i+1:
              self.robot_namespace = sys.argv[i+1]
          if sys.argv[i] == '-gazebo_namespace':
            if len(sys.argv) > i+1:
              self.gazebo_namespace = sys.argv[i+1]
          if sys.argv[i] == '-x':
            if len(sys.argv) > i+1:
              self.initial_xyz[0] = float(sys.argv[i+1])
          if sys.argv[i] == '-y':
            if len(sys.argv) > i+1:
              self.initial_xyz[1] = float(sys.argv[i+1])
          if sys.argv[i] == '-z':
            if len(sys.argv) > i+1:
              self.initial_xyz[2] = float(sys.argv[i+1])
          if sys.argv[i] == '-R':
            if len(sys.argv) > i+1:
              self.initial_rpy[0] = float(sys.argv[i+1])
          if sys.argv[i] == '-P':
            if len(sys.argv) > i+1:
              self.initial_rpy[1] = float(sys.argv[i+1])
          if sys.argv[i] == '-Y':
            if len(sys.argv) > i+1:
              self.initial_rpy[2] = float(sys.argv[i+1])
          if sys.argv[i] == '-package_to_model':
              self.package_to_model = True;
          if sys.argv[i] == '-b':
            self.bond = True

        if not self.sdf_format and not self.urdf_format:
          rospy.logerr("Error: you must specify incoming format as either urdf or sdf format xml")
          sys.exit(0)
        if self.model_name == "":
          rospy.logerr("Error: you must specify model name")
          sys.exit(0)

    def checkForModel(self,model):
        for n in model.name:
          if n == self.wait_for_model:
            self.wait_for_model_exists = True


    # Generate a blank SDF file with an include for the model from the model database
    def createDatabaseCode(self, database_name):
        return model_database_template.replace("MODEL_NAME", database_name);

    def callSpawnService(self):

        # wait for model to exist
        rospy.init_node('spawn_model')

        if not self.wait_for_model == "":
          rospy.Subscriber("%s/model_states"%(self.gazebo_namespace), ModelStates, self.checkForModel)
          r= rospy.Rate(10)
          while not rospy.is_shutdown() and not self.wait_for_model_exists:
            r.sleep()

        if rospy.is_shutdown():
          sys.exit(0)

        if self.file_name != "":
          rospy.loginfo("Loading model XML from file")
          if os.path.exists(self.file_name):
            if os.path.isdir(self.file_name):
              rospy.logerr("Error: file name is a path? %s", self.file_name)
              sys.exit(0)
            if not os.path.isfile(self.file_name):
              rospy.logerr("Error: unable to open file %s", self.file_name)
              sys.exit(0)
          else:
            rospy.logerr("Error: file does not exist %s", self.file_name)
            sys.exit(0)
          # load file
          f = open(self.file_name,'r')
          model_xml = f.read()
          if model_xml == "":
            rospy.logerr("Error: file is empty %s", self.file_name)
            sys.exit(0)

        # ROS Parameter
        elif self.param_name != "":
          rospy.loginfo( "Loading model XML from ros parameter")
          model_xml = rospy.get_param(self.param_name)
          if model_xml == "":
            rospy.logerr("Error: param does not exist or is empty")
            sys.exit(0)

        # Gazebo Model Database
        elif self.database_name != "":
          rospy.loginfo( "Loading model XML from Gazebo Model Database")
          model_xml = self.createDatabaseCode(self.database_name)
          if model_xml == "":
            rospy.logerr("Error: an error occured generating the SDF file")
            sys.exit(0)
        else:
          rospy.logerr("Error: user specified param or filename is an empty string")
          sys.exit(0)

        if self.package_to_model:
            model_xml = re.sub("<\s*mesh\s+filename\s*=\s*([\"|'])package://","<mesh filename=\g<1>model://", model_xml)

        # setting initial pose
        initial_pose = Pose()
        initial_pose.position.x = self.initial_xyz[0]
        initial_pose.position.y = self.initial_xyz[1]
        initial_pose.position.z = self.initial_xyz[2]
        # convert rpy to quaternion for Pose message
        tmpq = tft.quaternion_from_euler(self.initial_rpy[0],self.initial_rpy[1],self.initial_rpy[2])
        q = Quaternion(tmpq[0],tmpq[1],tmpq[2],tmpq[3])
        initial_pose.orientation = q;

        # spawn model
        if self.urdf_format:
          success = gazebo_interface.spawn_urdf_model_client(self.model_name, model_xml, self.robot_namespace,
                                                             initial_pose, self.reference_frame, self.gazebo_namespace)
        elif self.sdf_format:
          success = gazebo_interface.spawn_sdf_model_client(self.model_name, model_xml, self.robot_namespace,
                                                            initial_pose, self.reference_frame, self.gazebo_namespace)
        else:
          rospy.logerr("Error: should not be here in spawner helper script, there is a bug")
          sys.exit(0)

        # set model configuration before unpause if user requested
        if len(self.joint_names) != 0:
          try:
            success = gazebo_interface.set_model_configuration_client(self.model_name, self.param_name,
                                                                      self.joint_names, self.joint_positions, self.gazebo_namespace)
          except rospy.ServiceException as e:
            rospy.logerr("Set model configuration service call failed: %s", e)

        # unpause physics if user requested
        if self.unpause_physics:
          rospy.wait_for_service('%s/unpause_physics'%(self.gazebo_namespace))
          try:
            unpause_physics = rospy.ServiceProxy('%s/unpause_physics'%(self.gazebo_namespace), Empty)
            unpause_physics()
          except rospy.ServiceException as e:
            rospy.logerr("Unpause physics service call failed: %s", e)

        return


    def callDeleteService(self):
        try:
            delete_model = rospy.ServiceProxy('%s/delete_model'%(self.gazebo_namespace), DeleteModel)
            delete_model(model_name=self.model_name)
        except rospy.ServiceException as e:
            rospy.logerr("Delete model service call failed: %s", e)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(usage())
    else:
        print("SpawnModel script started") # make this a print incase roscore has not been started
        sm = SpawnModel()
        sm.parseUserInputs()
        sm.callSpawnService()

        if sm.bond:
            rospy.on_shutdown(sm.callDeleteService)
            rospy.spin()
