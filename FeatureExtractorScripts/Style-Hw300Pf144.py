from __future__ import print_function
from __future__ import absolute_import
import sys
sys.path.append('..')
import os
import tensorflow as tf
import argparse
from model.feature_extractor_training import train_procedures

data_path_root = '/Data_SSD/Harric/ChineseCharacterExp/'
model_log_path_root = '/Data_HDD/Harric/ChineseCharacterExp/'
# exp_root_path = '/Users/harric/Downloads/WNet_Exp/'

input_args = [

    #'--training_from_model_dir',
    #'/Data_HDD/Harric/ChineseCharacterExp/tfModels_FeatureExtractor/checkpoint/Exp20181226_FeatureExtractor_Style_HW300Pf80_vgg16net/variables',

    '--data_dir_train_path',
    'CASIA_Dataset/HandWritingData_OrgGrayScale/CASIA-HWDB1.1/,'
    'CASIA_Dataset/PrintedData_64Fonts/Simplified/GB2312_L1/,'
    'CASIA_Dataset/PrintedData/GB2312_L1/',

    '--data_dir_validation_path',
    'CASIA_Dataset/HandWritingData_OrgGrayScale/CASIA-HWDB2.1/,'
    'CASIA_Dataset/PrintedData_64Fonts/Simplified/GB2312_L1/,'
    'CASIA_Dataset/PrintedData/GB2312_L1/',

    '--file_list_txt_train',
    '../FileList/HandWritingData/Char_0_3754_Writer_1001_1300_Isolated.txt,'
    '../FileList/PrintedData/Char_0_3754_64PrintedFonts_GB2312L1_Simplified.txt,'
    '../FileList/PrintedData/Char_0_3754_Font_0_79_GB2312L1.txt',


    '--file_list_txt_validation',
    '../FileList/HandWritingData/Char_0_3754_Writer_1001_1300_Cursive.txt,'
    '../FileList/PrintedData/Char_0_3754_64PrintedFonts_GB2312L1_Simplified.txt,'
    '../FileList/PrintedData/Char_0_3754_Font_0_79_GB2312L1.txt',

    '--experiment_dir',
    'tfModels_FeatureExtractor/',

    '--log_dir',
    'tfLogs_FeatureExtractor/',

    '--image_filters','1',
    '--experiment_id','20190119_FeatureExtractor_Style_HW300Pf144',
    '--train_resume_mode','1',

    '--batch_size','16',
    '--image_size','64',
    '--epoch_num', '2500',
    '--network', 'vgg16net',
    '--init_lr','0.0001',
    '--label0_loss','0',
    '--label1_loss','1',
    '--center_loss_penalty_rate','0',

    '--augment','1',
    '--augnemt_for_flip','1',

    '--debug_mode','0',
    '--cheat_mode','1']


parser = argparse.ArgumentParser(description='Train')
parser.add_argument('--data_dir_train_path', dest='data_dir_train_path',type=str,required=True)
parser.add_argument('--data_dir_validation_path', dest='data_dir_validation_path',type=str,required=True)



parser.add_argument('--experiment_dir', dest='experiment_dir',type=str,required=True)
parser.add_argument('--log_dir', dest='log_dir',type=str,required=True)
parser.add_argument('--experiment_id', dest='experiment_id',type=str,required=True)
parser.add_argument('--training_from_model_dir', dest='training_from_model_dir', default=None)



parser.add_argument('--file_list_txt_train',dest='file_list_txt_train',type=str,required=True)
parser.add_argument('--file_list_txt_validation',dest='file_list_txt_validation',type=str,required=True)


parser.add_argument('--init_lr', dest='init_lr',type=float,required=True)




parser.add_argument('--batch_size', dest='batch_size',type=int,required=True)
parser.add_argument('--image_size', dest='image_size',type=int,required=True)

parser.add_argument('--epoch_num', dest='epoch_num',type=int,required=True)
parser.add_argument('--network', dest='network',type=str,required=True)

parser.add_argument('--label0_loss', dest='label0_loss',type=float,required=True)
parser.add_argument('--label1_loss', dest='label1_loss',type=float,required=True)
parser.add_argument('--center_loss_penalty_rate', dest='center_loss_penalty_rate',type=float,required=True)



parser.add_argument('--debug_mode', dest='debug_mode',type=int,required=True)
parser.add_argument('--cheat_mode', dest='cheat_mode',type=int,required=True)
parser.add_argument('--augment', dest='augment',type=int,required=True)
parser.add_argument('--augnemt_for_flip', dest='augnemt_for_flip',type=int,required=True)



parser.add_argument('--image_filters', dest='image_filters',type=int,required=True)
parser.add_argument('--train_resume_mode', dest='train_resume_mode',type=int,required=True)











def main(_):

    train_procedures(args_input=args)






args = parser.parse_args(input_args)
args.experiment_dir = os.path.join(model_log_path_root,args.experiment_dir)
args.data_dir_train_path=args.data_dir_train_path.split(',')
args.data_dir_validation_path=args.data_dir_validation_path.split(',')
args.file_list_txt_train=args.file_list_txt_train.split(',')
args.file_list_txt_validation=args.file_list_txt_validation.split(',')
for ii in range(len(args.data_dir_train_path)):
    args.data_dir_train_path[ii] = os.path.join(data_path_root,args.data_dir_train_path[ii])
for ii in range(len(args.data_dir_validation_path)):
    args.data_dir_validation_path[ii] = os.path.join(data_path_root,args.data_dir_validation_path[ii])
args.log_dir = os.path.join(model_log_path_root,args.log_dir)
if __name__ == '__main__':
    tf.app.run()
