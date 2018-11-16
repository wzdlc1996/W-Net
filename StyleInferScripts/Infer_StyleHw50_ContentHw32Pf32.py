# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import

import tensorflow as tf
from tensorflow.python.client import device_lib
import argparse
import sys
sys.path.append('..')
import os
import time


from model.wnet import WNet as WNET

#exp_root_path = '/Users/harric/ChineseCharacterExp/'
exp_root_path = '/DataA/Harric/ChineseCharacterExp/'

print_separater = "#################################################################"




input_args = ['--debug_mode','0',
              '--style_input_number','4',
              '--targeted_content_input_txt',
    '../FontAndChars/滚滚长江东逝水_简体.txt',

              '--save_path',
    '../../GeneratedChars/'+ time.strftime('%Y-%m-%d@%H:%M:%S', time.localtime())+'/',


              '--known_style_img_path',
    '../StyleExampleChars/CY.jpg',         # input a image with multiple written chars
    #'../StyleExampleChars/TTTGB-Medium.ttf', # input a ttf / otf file to generate printed chars
    #'../StyleExampleChars/PrintedSamples', # input a image directory with multiple single chars

              '--save_mode','8:8',

              '--content_data_dir', # standard data location
    'CASIA_Dataset/HandWritingData_OrgGrayScale/CASIA-HWDB1.1/,'
    'CASIA_Dataset/HandWritingData_OrgGrayScale/CASIA-HWDB2.1/,'
    'CASIA_Dataset/PrintedData/',

              '--file_list_txt_content',  # file list of the standard data
    '../FileList/HandWritingData/Char_0_3754_Writer_1001_1032_Isolated.txt,'
    '../FileList/HandWritingData/Char_0_3754_Writer_1001_1032_Cursive.txt,'
    '../FileList/PrintedData/Char_0_3754_Writer_Selected32_Printed_Fonts_GB2312L1.txt',
              

              '--channels','1',
              '--img_width', '64',

              '--generator_residual_at_layer','3',
              '--generator_residual_blocks','5',

              '--generator_device','/device:GPU:0',

              '--model_dir',
    '/home/harric/Desktop/TrainedModels/Exp20181017_StyleHw50_ContentPf32+Hw32_GenEncDec6-Res5@Lyr3_DisMdy6conv/generator/',

              ]

parser = argparse.ArgumentParser(description='Train')
parser.add_argument('--debug_mode', dest='debug_mode',type=int,required=True)
parser.add_argument('--style_input_number', dest='style_input_number', type=int,required=True)

# directories setting
parser.add_argument('--targeted_content_input_txt', dest='targeted_content_input_txt', type=str,required=True)
parser.add_argument('--save_path', dest='save_path', type=str,required=True)
parser.add_argument('--save_mode', dest='save_mode', type=str,required=True)



# network settings
parser.add_argument('--model_dir', dest='model_dir', required=True, type=str)
parser.add_argument('--known_style_img_path', dest='known_style_img_path', required=True, type=str)
parser.add_argument('--generator_residual_at_layer', dest='generator_residual_at_layer', type=int, required=True)
parser.add_argument('--generator_residual_blocks', dest='generator_residual_blocks', type=int, required=True)


parser.add_argument('--generator_device', dest='generator_device',type=str,required=True,
                    help='Devices for generator')

# input data setting
parser.add_argument('--content_data_dir',dest='content_data_dir',type=str,required=True)
parser.add_argument('--file_list_txt_content',dest='file_list_txt_content',type=str,required=True)


parser.add_argument('--channels',dest='channels',type=int,required=True)
parser.add_argument('--img_width',dest='img_width',type=int,required=True)

# training param setting


def get_available_gpus():
    local_device_protos = device_lib.list_local_devices()
    cpu_device=[x.name for x in local_device_protos if x.device_type == 'CPU']
    gpu_device=[x.name for x in local_device_protos if x.device_type == 'GPU']
    print("Available CPU:%s with number:%d" % (cpu_device, len(cpu_device)))
    print("Available GPU:%s with number:%d" % (gpu_device, len(gpu_device)))
    return cpu_device, gpu_device,len(cpu_device),len(gpu_device)



def main(_):
    print(print_separater)
    avalialbe_cpu, available_gpu, available_cpu_num, available_gpu_num = get_available_gpus()

    if available_gpu_num==0:
        args.generator_device = '/device:CPU:0'

    content_data_dir = args.content_data_dir.split(',')
    for ii in range(len(content_data_dir)):
        content_data_dir[ii] = os.path.join(exp_root_path, content_data_dir[ii])

    model = WNET(debug_mode=args.debug_mode,
                 style_input_number=args.style_input_number,

                 targeted_content_input_txt=args.targeted_content_input_txt,
                 save_path=args.save_path,
                 save_mode=args.save_mode,

                 content_data_dir=content_data_dir,
                 file_list_txt_content=args.file_list_txt_content.split(','),

                 channels=args.channels,
                 img_width=args.img_width,

                 generator_residual_at_layer=args.generator_residual_at_layer,
                 generator_residual_blocks=args.generator_residual_blocks,
                 generator_devices=args.generator_device,

                 model_dir=args.model_dir,
                 known_style_img_path=args.known_style_img_path)

    model.character_generation()


#input_args = []
args = parser.parse_args(input_args)


if __name__ == '__main__':
    tf.app.run()
