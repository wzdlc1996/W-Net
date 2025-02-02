import numpy as np
import random
import tensorflow as tf
import os
import gc
import scipy.misc as misc

from tensorflow.python.framework import ops
from tensorflow.python.framework import dtypes
from utilities.utils import image_show

import matplotlib.pyplot as plt
from utilities.utils import shift_and_resize_image

GRAYSCALE_AVG = 127.5
STANDARD_IMAGE_WIDTH = 256

STANDARD_GRAYSCALE_THRESHOLD_VALUE = 240
ALTERNATE_GRAYSCALE_LOW=170
ALTERNATE_GRAYSCALE_HGH=250


class Dataset(object):
    def __init__(self,
                 data_list,
                 label0_label_list,
                 label1_label_list,
                 batch_size,
                 input_width,
                 input_filters,
                 epoch
                 ):
        self.batch_size = batch_size
        self.input_width = input_width
        self.input_filters = input_filters

        self.data_list = data_list
        self.label0_label_list = label0_label_list
        self.label1_label_list = label1_label_list

        self.epoch = epoch


    def shuffle(self):
        old_file_list = self.data_list
        old_label0_label_list = self.label0_label_list
        old_label1_label_list = self.label1_label_list

        self.data_list = []
        self.label0_label_list = []
        self.label1_label_list = []

        indices_shuffled = np.random.permutation(len(old_file_list))
        for ii in indices_shuffled:
            self.data_list.append(old_file_list[ii])
            self.label0_label_list.append(old_label0_label_list[ii])
            self.label1_label_list.append(old_label1_label_list[ii])

    def create_dataset_op(self,sess):

        data_list_tensor = ops.convert_to_tensor(self.data_list, dtype=dtypes.string)
        label0_list_tensor = ops.convert_to_tensor(self.label0_label_list, dtype=dtypes.int32)
        label1_list_tensor = ops.convert_to_tensor(self.label1_label_list, dtype=dtypes.int32)
        self.filename_queue = tf.train.slice_input_producer([data_list_tensor,
                                                             label0_list_tensor,
                                                             label1_list_tensor])

        file_content = tf.read_file(self.filename_queue[0])
        image = tf.image.decode_png(file_content, channels=self.input_filters)
        label0 = self.filename_queue[1]
        label1 = self.filename_queue[2]
        image.set_shape([self.input_width, self.input_width, self.input_filters])
        self.batch_image, \
        self.batch_label0, \
        self.batch_label1 = tf.train.batch([image, label0, label1],
                                           batch_size=self.batch_size)

        tf.local_variables_initializer().run(session=sess)



    def get_next_batch(self,sess,augment,augment_for_flip):


        batch_images, \
        batch_label0_labels, \
        batch_label1_labels, \
            = sess.run([self.batch_image,
                        self.batch_label0,
                        self.batch_label1])

        if augment:
            for ii in range(self.batch_size):
                curt_img = np.squeeze(batch_images[ii,:,:,:])

                crop_size = np.random.randint(low=curt_img.shape[0]*0.75,
                                              high=curt_img.shape[1]+1)
                start_p_h = np.random.randint(low=0, high=curt_img.shape[1]-crop_size+1)
                start_p_v = np.random.randint(low=0, high=curt_img.shape[0]-crop_size+1)

                cropped_img = curt_img[start_p_v:start_p_v+crop_size,
                              start_p_h:start_p_h+crop_size]

                curt_img = misc.imresize(cropped_img, [curt_img.shape[0], curt_img.shape[1]])

                threshold = np.int32(np.random.uniform(low=ALTERNATE_GRAYSCALE_LOW,high=ALTERNATE_GRAYSCALE_HGH))
                curt_img[np.where(curt_img < threshold)] = 0
                curt_img[np.where(curt_img >= threshold)] = 255

                flipier1 = random.uniform(0.00, 1.00)
                flipier2 = random.uniform(0.00, 1.00)
                flipier3 = random.uniform(0.00, 1.00)
                if flipier1>0.5 and augment_for_flip:
                    curt_img = np.flip(curt_img,axis=1)
                if flipier2>0.5 and augment_for_flip:
                    curt_img = np.flip(curt_img,axis=0)
                if flipier3 > 0.5 and augment_for_flip:
                    curt_img = np.transpose(curt_img)

                batch_images[ii,:,:,:] = np.reshape(curt_img,[curt_img.shape[0],curt_img.shape[1],1])
        else:
            for ii in range(self.batch_size):
                curt_img = np.squeeze(batch_images[ii, :, :, :])
                threshold = STANDARD_GRAYSCALE_THRESHOLD_VALUE
                curt_img[np.where(curt_img < threshold)] = 0
                curt_img[np.where(curt_img >= threshold)] = 255
                batch_images[ii, :, :, :] = np.reshape(curt_img, [curt_img.shape[0], curt_img.shape[1], 1])

        batch_images = batch_images.astype(np.float32) / GRAYSCALE_AVG - 1

        return batch_images,batch_label1_labels,batch_label0_labels








class DataProvider(object):
    def __init__(self,image_width,
                 batch_size,
                 data_dir_train_path,
                 data_dir_validation_path,
                 file_list_txt_path_train,
                 file_list_txt_path_validation,
                 input_filters,
                 sess,
                 epoch_num=20,
                 shuffle_data=True,
                 cheat_mode=True):

        self.batch_size=batch_size
        self.input_width=image_width
        self.input_filters=input_filters
        self.data_dir_train_path=data_dir_train_path
        self.data_dir_validation_path = data_dir_validation_path
        train_data_list, \
        train_label0_list, \
        train_label1_list, \
        self.label1_vec, \
        self.label0_vec= \
            self.read_file_list(data_dir=self.data_dir_train_path,
                                txt_path=file_list_txt_path_train)

        validation_data_list, \
        validation_label0_list, \
        validation_label1_list, \
        _, \
        _ = \
            self.read_file_list(data_dir=self.data_dir_validation_path,
                                txt_path=file_list_txt_path_validation)




        if cheat_mode:
            train_data_list.extend(validation_data_list)
            train_label0_list.extend(validation_label0_list)
            train_label1_list.extend(validation_label1_list)


        self.train = Dataset(data_list=train_data_list,
                             label1_label_list=train_label1_list,
                             label0_label_list=train_label0_list,
                             batch_size=self.batch_size,
                             input_width=self.input_width,
                             input_filters=self.input_filters,
                             epoch=epoch_num)

        self.val = Dataset(data_list=validation_data_list,
                           label1_label_list=validation_label1_list,
                           label0_label_list=validation_label0_list,
                           batch_size=self.batch_size,
                           input_width=self.input_width,
                           input_filters=self.input_filters,
                           epoch=epoch_num)




        self.epoch=epoch_num
        self.iters_for_each_epoch = int(np.ceil(len(self.train.data_list) / self.batch_size))
        self.iters = int(self.iters_for_each_epoch * self.epoch)

        if shuffle_data:
            self.train.shuffle()
            self.val.shuffle()



        self.train.create_dataset_op(sess=sess)
        self.val.create_dataset_op(sess=sess)


    def read_file_list(self,
                       data_dir,txt_path):
        label0_list = list()
        label1_list = list()
        data_list = list()
        for ii in range(len(data_dir)):

            file_handle = open(txt_path[ii], 'r')
            lines = file_handle.readlines()


            for line in lines:
                curt_line = line.split('@')
                label0_list.append(int(curt_line[1]))
                label1_list.append(int(curt_line[2]))
                curt_data = curt_line[3].split('\n')[0]
                if curt_data[0] == '/':
                    curt_data = curt_data[1:]
                curt_data_path = os.path.join(data_dir[ii], curt_data)
                data_list.append(curt_data_path)

            file_handle.close()
        label1_vec = np.unique(label1_list)
        label0_vec = np.unique(label0_list)

        return data_list, label0_list, label1_list, label1_vec, label0_vec


    def get_total_epoch_num(self,itr_num=-1,batch_size=-1,tower_num=-1):
        epoch_num = int(np.ceil(itr_num / np.ceil(len(self.train.data_list) / (batch_size * tower_num))))

        print ("Epoch Num:%d, Itr Num:%d" % (epoch_num, itr_num) )
        return epoch_num

    def compute_total_batch_num(self, batch_size,tower_num):
        """Total padded batch num"""
        return int(np.ceil(len(self.train.data_list) / float(batch_size*tower_num)))







