#!/usr/bin/env python3

import rospy
from sensor_msgs.msg import Image, PointCloud2
import detectron2
from detectron2.utils.logger import setup_logger
setup_logger()
# import some common libraries
import numpy as np
import cv2
from cv_bridge import CvBridge
# import some common detectron2 utilities
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog, DatasetCatalog

class Detector(object):
    def __init__(self):
        # self.height = rospy.get_param('camera/realsense2_camera/color_height', 720) # it takes a value of -1 (???)
        # self.width = rospy.get_param('camera/realsense2_camera/color_width', 1280)
        self.height = rospy.get_param('image/height', 720)
        self.width = rospy.get_param('image/width', 1280)
        self.depth = rospy.get_param('image/depth', 3)
        camera_topic = rospy.get_param('camera_topic/topic', "/camera/color/image_raw")
        self.image_sub = rospy.Subscriber('/camera/color/image_raw', Image, self.im_callback)
        self.model = rospy.get_param('model/name', "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
        self.weights = rospy.get_param('model/weights', "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
        self.im = np.zeros((self.height,self.width,self.depth), np.uint8) # create empty image
        self.all_classes = rospy.get_param('visualization/all_classes', True)
        self.target_object = rospy.get_param('visualization/target', 0) # default persone class
        self.n_object = 0
        self.bbox_coordinates = []
        self.bbox_centers = []

    def im_callback(self, im_data):
        bridge = CvBridge()
        self.im = bridge.imgmsg_to_cv2(im_data, "bgr8")

    def detect(self):
        # empty lists
        self.bbox_centers = []
        self.bbox_coordinates = [] 
        print("Detecting..")
        cfg = get_cfg()
        cfg.merge_from_file(model_zoo.get_config_file(self.model))
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.7  # set threshold for this model
        cfg.MODEL.DEVICE = "cpu" # Remove this line if you use GPU
        cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url(self.weights)
        predictor = DefaultPredictor(cfg)
        outputs = predictor(self.im)
        num_obj = len(outputs["instances"].pred_classes)
        print(num_obj, "objects have been detected!")

        # extract class labels
        pred_classes = outputs['instances'].pred_classes.cpu().tolist()
        class_names = MetadataCatalog.get(cfg.DATASETS.TRAIN[0]).thing_classes
        pred_class_names = list(map(lambda x: class_names[x], pred_classes))
        # print results by labels
        self.print_labels(pred_class_names)
        self.clean_output(outputs)

        ################# VISUALIZATION #############
        v = Visualizer(self.im[:, :, ::-1], MetadataCatalog.get(cfg.DATASETS.TRAIN[0]), scale=1)
        if self.all_classes:
            out = v.draw_instance_predictions(outputs["instances"].to("cpu"))
        else:
            out = v.draw_instance_predictions(outputs['instances'][outputs['instances'].pred_classes == self.target_object].to("cpu"))
        cv2.imshow("result", out.get_image()[:, :, ::-1])
        print("PRESS ANY BUTTON TO ADVANCE..")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        print("Process terminated!")

########## HELPER FUNCTIONS ###################################################################################################################################

    def remove_duplicates(self,l):
        return list(dict.fromkeys(l))

    def count_classes(self, classes):
        result = []
        count = 0
        objects = self.remove_duplicates(classes)
        for object in objects:
            for elem in classes:
                if object == elem:
                    count += 1
            result.append([count, object])
            count = 0
        return result

    def print_labels(self,input):
        print("\n========= OBJECTS: =========")
        for obj in self.count_classes(input):
            print(obj[0], obj[1])
        print("============================\n")

    def clean_output(self, data):
        pred_classes = data['instances'].pred_classes.cpu().tolist()
        boxes = data['instances'].pred_boxes.tensor.tolist()
        count = 0
        if self.all_classes:
            for i in range(len(pred_classes)):
                    count += 1
                    self.bbox_centers.append(data['instances'].get('pred_boxes')[i].get_centers().tolist()[0])
                    self.bbox_coordinates.append(boxes[i])
        else:
            for i in range(len(pred_classes)):
                if pred_classes[i] == self.target_object:
                    count += 1
                    self.bbox_centers.append(data['instances'].get('pred_boxes')[i].get_centers().tolist()[0])
                    self.bbox_coordinates.append(boxes[i])
        print("========= INFO: ============")
        print("number of target objects: ", count)
        print("\n boxes coordinates: \n", self.bbox_coordinates)
        print("\n centers coordinates: \n", self.bbox_centers)
        print("============================\n")

################################################################################################################################################################

def main():
    rospy.init_node('detectron2_node', anonymous=True)
    print("Vision node started!")
    d = Detector()
    while not rospy.is_shutdown():
        d.detect()
    print("Vision node ended!")
    #rospy.spin()

if __name__ == '__main__':
    main()



