import six.moves
from datetime import datetime
import sys
import math
import time
import numpy as np
import tensorflow as tf
import re

RESIZE_AOI = 256
RESIZE_FINAL = 227


# Read image files            
class ImageCoder(object):
    
    def __init__(self):
        config = tf.ConfigProto(allow_soft_placement=True)
        self._sess = tf.Session(config=config)

        # Initializes function that decodes RGB JPEG data.
        self._decode_jpeg_data = tf.placeholder(dtype=tf.string)
        self._decode_jpeg = tf.image.decode_jpeg(self._decode_jpeg_data, channels=3)
        self.crop = tf.image.resize_images(self._decode_jpeg, (RESIZE_FINAL, RESIZE_FINAL))
        
        ''' Added to handle memory leak-single look '''
        self.crop_image = tf.image.resize_images(self.crop, (RESIZE_FINAL, RESIZE_FINAL))
        self.image_standradisation = tf.image.per_image_standardization(self.crop_image)
        self.images = tf.placeholder(dtype=tf.float32, shape=(1, 227, 227, 3))
        self.image_batch = tf.stack(self.images)
        
        '''Added to handle memory leak-multi look'''                
        self.standardize_image_holder = tf.placeholder(dtype=tf.float32, shape=(227, 227, 3))
        self.flipped_image_holder = tf.placeholder(dtype=tf.float32, shape=(227, 227, 3))

        self.image_standradisation_multi = tf.image.per_image_standardization(self.standardize_image_holder)
        self.flipped_img_multi = tf.image.flip_left_right(self.flipped_image_holder)
        
        self.ch = tf.placeholder(tf.int32)
        self.cw = tf.placeholder(tf.int32)
        
        self.cropped_boundingbox = tf.image.crop_to_bounding_box(self.crop, self.ch, self.cw, RESIZE_FINAL, RESIZE_FINAL)
        
        self.images_multi = tf.placeholder(dtype=tf.float32, shape=(12, 227, 227, 3))
        self.image_batch_mult = tf.stack(self.images_multi)
    
        
    def decode_jpeg(self, image_data, look):
        
            image = self._sess.run(self.crop, feed_dict={self._decode_jpeg_data: image_data})
            crops = []
            h = image.shape[0]
            w = image.shape[1]
            hl = h - RESIZE_FINAL
            wl = w - RESIZE_FINAL

            crop = self._sess.run(self.crop_image, feed_dict={self._decode_jpeg_data: image_data})
            standardizeImage = self._sess.run(self.image_standradisation_multi, feed_dict={self.standardize_image_holder: crop})
            crops.append(standardizeImage)
            flippedImage = self._sess.run(self.flipped_img_multi, feed_dict={self.flipped_image_holder: crop})
            crops.append(flippedImage)

            corners = [ (0, 0), (0, wl), (hl, 0), (hl, wl), (int(hl/2), int(wl/2))]
            for corner in corners:
                ch, cw = corner
                cropped = self._sess.run(self.cropped_boundingbox, feed_dict={self._decode_jpeg_data: image_data, self.ch: ch, self.cw: cw})
                standardizeImage_2 = self._sess.run(self.image_standradisation_multi, feed_dict={self.standardize_image_holder: cropped})
                crops.append(standardizeImage_2)
                flippedImage_2 = self._sess.run(self.flipped_img_multi, feed_dict={self.flipped_image_holder: cropped})
                crops.append(flippedImage_2)

            IMAGES_B = self._sess.run(self.image_batch_mult, feed_dict={self.images_multi: crops})
            return IMAGES_B

            assert len(image.shape) == 3
            assert image.shape[2] == 3
            return image        

        

def make_multi_crop_batch(filename, coder):
    """Process a single image file.
    Args:
    filename: string, path to an image file e.g., '/path/to/example.JPG'.
    coder: instance of ImageCoder to provide TensorFlow image coding utils.
    Returns:
    image_buffer: string, JPEG encoding of RGB image.
    """
    # Read the image file.
    with tf.gfile.FastGFile(filename, 'rb') as f:
        image_data = f.read()

    # Convert any PNG to JPEG's for consistency.
    
    image = coder.decode_jpeg(image_data, 'multi')

    return image   

