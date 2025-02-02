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

from model.wnet_forInferring import WNet as WNET

#exp_root_path = '/Users/harric/ChineseCharacterExp/'
exp_root_path = '/DataA/Harric/ChineseCharacterExp/'

print_separater = "#################################################################"




input_args = [
    '--targeted_content_input_txt',
    '../ContentTxt/StyleChars_Paintings_20.txt',
    '--save_mode','1:20',


    '--known_style_img_path',
    # '../StyleExamples/Brush1.png',         # input a image with multiple written chars
    # '../FontFiles/DroidSansFallback.ttf', # input a ttf / otf file to generate printed chars
    '../StyleExamples/PrintedSamples', # input a image directory with multiple single chars

    ####################################################################
    ####################################################################
    #################### DO NOT TOUCH BELOW ############################
    ####################################################################
    ####################################################################



    '--save_path',
    '../../GeneratedChars/'+ time.strftime('%Y-%m-%d@%H:%M:%S', time.localtime())+'/',

    '--style_input_number','4',

    '--content_data_dir', # standard data location
    # 'CASIA_Dataset/Sources/PrintedSources/64_FoundContentPrototypeTtfOtfs/Simplified/',
    'CASIA_Dataset/PrintedData_64Fonts/Simplified/GB2312_L1/',

    '--file_list_txt_content',  # file list of the standard data
    '../FileList/PrintedData/Char_0_3754_64PrintedFonts_GB2312L1_Simplified.txt',



    '--generator_residual_at_layer','3',
    '--generator_residual_blocks','7',

    '--generator_device','/device:GPU:0',

    '--model_dir',
    'TrainedModels_WNet/Exp20181225-WNet-NonAdaIN_StylePf80_ContentPf32_GenEncDec6-Res6@Lyr3_DisMdy6conv/',

    ]

parser = argparse.ArgumentParser(description='Train')
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


parser.add_argument('--generator_device', dest='generator_device',type=str,required=True, help='Devices for generator')

# input data setting
parser.add_argument('--content_data_dir',dest='content_data_dir',type=str,required=True)
parser.add_argument('--file_list_txt_content',dest='file_list_txt_content',type=str,required=True)





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

    experiment_id_list = args.model_dir.split('/')
    for experiment_id in experiment_id_list:
        if 'Exp' in experiment_id:
            break

    model = WNET(style_input_number=args.style_input_number,
                 experiment_id=experiment_id,

                 targeted_content_input_txt=args.targeted_content_input_txt,
                 save_path=args.save_path,
                 save_mode=args.save_mode,

                 content_data_dir=content_data_dir,
                 file_list_txt_content=args.file_list_txt_content.split(','),


                 generator_residual_at_layer=args.generator_residual_at_layer,
                 generator_residual_blocks=args.generator_residual_blocks,
                 generator_devices=args.generator_device,

                 model_dir=os.path.join(exp_root_path,args.model_dir),
                 known_style_img_path=args.known_style_img_path)

    model.character_generation()


#input_args = []
args = parser.parse_args(input_args)


if __name__ == '__main__':
    tf.app.run()
