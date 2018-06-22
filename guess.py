from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from datetime import datetime
import math
import time
from data import inputs
import numpy as np
import tensorflow as tf
from model import select_model, get_checkpoint
from utils import *
import os
import json
import csv
import cv2

RESIZE_FINAL = 227
GENDER_LIST =['Male','Female']
AGE_LIST = ['(0, 2)','(4, 6)','(8, 12)','(15, 20)','(25, 32)','(38, 43)','(48, 53)','(60, 100)']
MAX_BATCH_SZ = 128

tf.app.flags.DEFINE_string('model_dir_age', 'C:/Users/user/Desktop/intern/inception/22801', 'Model directory (where training data for AGE lives)')
tf.app.flags.DEFINE_string('model_dir_gender', 'C:/Users/user/Desktop/intern/inception/21936', 'Model directory (where training data for GENDER lives)')

tf.app.flags.DEFINE_string('filename', 'F:/pMP/PMP/YLAN6884.jpg', 'File (Image) or File list (Text/No header TSV) to process')

tf.app.flags.DEFINE_string('device_id', '/cpu:0', 'What processing unit to execute inference on')

tf.app.flags.DEFINE_string('checkpoint', 'checkpoint', 'Checkpoint basename')

tf.app.flags.DEFINE_string('model_type', 'inception', 'Type of convnet')

tf.app.flags.DEFINE_boolean('single_look', False, 'single look at the image or multiple crops')

FLAGS = tf.app.flags.FLAGS

def resolve_file(fname):
    if os.path.exists(fname): return fname
    for suffix in ('.jpg', '.png', '.JPG', '.PNG', '.jpeg'):
        cand = fname + suffix
        if os.path.exists(cand):
            return cand
    return None

def classify_one_multi_crop(sess, label_list, softmax_output, coder, images, image_file):
    try:
                
        if FLAGS.single_look:
            image_batch = make_single_crop_batch(image_file, coder)
        else:
            image_batch = make_multi_crop_batch(image_file, coder)
        
        batch_results = sess.run(softmax_output, feed_dict = {images:image_batch})
                
        output = batch_results[0]
        batch_sz = batch_results.shape[0]
    
        for i in range(1, batch_sz):
            output = output + batch_results[i]

        output /= batch_sz
        best = np.argmax(output)
        best_choice = (label_list[best], output[best])
                
        print('%s, prob = %.2f' % best_choice)
    
        nlabels = len(label_list)
        if nlabels > 2:
            output[best] = 0
            second_best = np.argmax(output)
            print('%s, prob = %.2f' % (label_list[second_best], output[second_best]))
                
    except Exception as e:
        print(e)
        print('Failed to run image %s ' % image_file)

def model_init(sess, model_path, label_list): 
    
    model_checkpoint_path, global_step = get_checkpoint(model_path, None, FLAGS.checkpoint)

    nlabels = len(label_list)
    model_fn = select_model(FLAGS.model_type)
    images_placeholder = tf.placeholder(tf.float32, [None, RESIZE_FINAL, RESIZE_FINAL, 3])
    
    with tf.device(FLAGS.device_id):
            
        logits = model_fn(nlabels, images_placeholder, 1, False)
            
        init = tf.global_variables_initializer()
                           
        saver = tf.train.Saver()
        saver.restore(sess, model_checkpoint_path)
                            
        softmax_output = tf.nn.softmax(logits)
                        
        return softmax_output, images_placeholder  

def main():

    files = []

    if (os.path.isdir(FLAGS.filename)):
        for relpath in os.listdir(FLAGS.filename):
            abspath = os.path.join(FLAGS.filename, relpath)
            
            if os.path.isfile(abspath) and any([abspath.endswith('.' + ty) for ty in ('jpg', 'png', 'JPG', 'PNG', 'jpeg')]):
                print(abspath)
                files.append(abspath)
    else:
        files.append(FLAGS.filename)
        # If it happens to be a list file, read the list and clobber the files
        if any([FLAGS.filename.endswith('.' + ty) for ty in ('csv', 'tsv', 'txt')]):
            files = list_images(FLAGS.filename)
    
    config = tf.ConfigProto(allow_soft_placement = True)
    config.gpu_options.allow_growth = True

    #initializes checkpoints and creates graph for age model
    with tf.Graph().as_default() as age_graph:
        sess = tf.Session(graph = age_graph, config=config)       
        age_softmax, age_image = model_init(sess, FLAGS.model_dir_age, AGE_LIST)
    #initializes checkpoints and creates graph for gender model    
    with tf.Graph().as_default() as gen_graph:
        sess1 = tf.Session(graph = gen_graph, config=config)
        gender_softmax, gender_image = model_init(sess1, FLAGS.model_dir_gender, GENDER_LIST)
    
    coder_age = ImageCoder()
    coder_gender = ImageCoder()

    image_files = list(filter(lambda x: x is not None, [resolve_file(f) for f in files]))
    
    for image_file in image_files:
        classify_one_multi_crop(sess, AGE_LIST, age_softmax, coder_age, age_image, image_file)
        classify_one_multi_crop(sess1, GENDER_LIST, gender_softmax, coder_gender, gender_image, image_file)
                            
    sess.close()
    sess1.close()
    
main()
