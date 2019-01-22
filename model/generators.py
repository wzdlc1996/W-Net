
import tensorflow as tf
import sys
sys.path.append('..')


import numpy as np
from utilities.ops import lrelu, relu, batch_norm, layer_norm, instance_norm, adaptive_instance_norm, resblock, global_average_pooling
from utilities.ops import conv2d, deconv2d, fc, dilated_conv2d, dilated_conv_resblock, normal_conv_resblock
from utilities.ops import emd_mixer


import math

print_separater="#########################################################"

eps = 1e-9
generator_dim = 64


def _calculate_batch_diff(input_feature):
    diff = tf.abs(tf.expand_dims(input_feature, 4) -
                  tf.expand_dims(tf.transpose(input_feature, [1, 2, 3, 0]), 0))
    diff = tf.reduce_sum(tf.exp(-diff), 4)
    return tf.reduce_mean(diff)


##############################################################################################
##############################################################################################
##############################################################################################
### Encoders #################################################################################
##############################################################################################
##############################################################################################
##############################################################################################
def encoder_framework(images,
                      is_training,
                      encoder_device,
                      residual_at_layer,
                      residual_connection_mode,
                      scope,initializer,weight_decay,
                      weight_decay_rate,
                      reuse = False,
                      adain_use=False):
    def encoder(x, output_filters, layer):

        act = lrelu(x)
        conv = conv2d(x=act,
                      output_filters=output_filters,
                      scope="layer%d_conv" % layer,
                      parameter_update_device=encoder_device,
                      initializer=initializer,
                      weight_decay=weight_decay,
                      name_prefix=scope,
                      weight_decay_rate=weight_decay_rate)
        if not adain_use:
            enc = batch_norm(conv, is_training, scope="layer%d_bn" % layer,
                             parameter_update_device=encoder_device)
        elif adain_use==True and 'content' in scope:
            enc = instance_norm(x=conv, scope="layer%d_in" % layer,
                                parameter_update_device=encoder_device)
        else:
            enc = conv
        return enc


    return_str = "Encoder %d Layers" % int(np.floor(math.log(int(images.shape[1])) / math.log(2)))
    if not residual_at_layer == -1:
        return_str = return_str + " with residual blocks at layer %d" % residual_at_layer



    residual_input_list = list()
    full_feature_list = list()
    shortcut_list = list()
    batch_size = int(images.shape[0])


    with tf.variable_scope(tf.get_variable_scope()):
        with tf.device(encoder_device):
            with tf.variable_scope(scope):
                if reuse:
                    tf.get_variable_scope().reuse_variables()


                feature_size = int(images.shape[1])
                ii=0
                while not feature_size==1:
                    if ii == 0:
                        encoder_layer = conv2d(x=images,
                                               output_filters=generator_dim,
                                               scope="layer1_conv",
                                               parameter_update_device=encoder_device,
                                               initializer=initializer,
                                               weight_decay=weight_decay,
                                               name_prefix=scope,
                                               weight_decay_rate=weight_decay_rate)
                    else:
                        output_filter_num_expansion = np.min([np.power(2,ii),8])
                        output_filter_num = generator_dim * output_filter_num_expansion
                        encoder_layer = encoder(x=encoder_layer,
                                                output_filters=output_filter_num,
                                                layer=ii+1)
                    full_feature_list.append(encoder_layer)


                    feature_size = int(encoder_layer.shape[1])
                    if feature_size==1:
                        output_final_encoded = encoder_layer

                    residual_condition = (residual_connection_mode == 'Single' and (ii + 1 == residual_at_layer)) \
                                         or (residual_connection_mode == 'Multi' and (ii + 1 <= residual_at_layer))

                    # output for residual blocks
                    if residual_condition:
                        residual_input_list.append(encoder_layer)

                    # output for shortcut
                    if ii+1 > residual_at_layer:
                        shortcut_list.append(encoder_layer)
                    ii+=1

        return output_final_encoded, \
               shortcut_list, residual_input_list, full_feature_list, \
               return_str


def encoder_resemd_framework(images,
                             is_training,
                             encoder_device,
                             scope,initializer,
                             weight_decay,weight_decay_rate,
                             residual_at_layer=-1,
                             residual_connection_mode=None,
                             reuse=False,
                             adain_use=False):
    residual_connection_mode=None
    residual_at_layer=-1
    adain_use=False
    full_feature_list = list()
    with tf.variable_scope(tf.get_variable_scope()):
        with tf.device(encoder_device):
            with tf.variable_scope(scope):
                if reuse:
                    tf.get_variable_scope().reuse_variables()

                conv1 = lrelu(conv2d(x=images,
                                     output_filters=64,
                                     kh=5,kw=5, sh=1, sw=1,
                                     scope="layer%d_conv" % 1,
                                     parameter_update_device=encoder_device,
                                     initializer=initializer,
                                     weight_decay=weight_decay,
                                     name_prefix=scope,
                                     weight_decay_rate=weight_decay_rate))
                full_feature_list.append(conv1)

                conv2 = lrelu(conv2d(x=conv1,
                                     output_filters=128,
                                     kh=3, kw=3, sh=2, sw=2,
                                     scope="layer%d_conv" % 2,
                                     parameter_update_device=encoder_device,
                                     initializer=initializer,
                                     weight_decay=weight_decay,
                                     name_prefix=scope,
                                     weight_decay_rate=weight_decay_rate))
                full_feature_list.append(conv2)

                conv3 = lrelu(conv2d(x=conv2,
                                     output_filters=256,
                                     kh=3, kw=3, sh=2, sw=2,
                                     scope="layer%d_conv" % 3,
                                     parameter_update_device=encoder_device,
                                     initializer=initializer,
                                     weight_decay=weight_decay,
                                     name_prefix=scope,
                                     weight_decay_rate=weight_decay_rate))
                full_feature_list.append(conv3)

                conv4 = lrelu(conv2d(x=conv3,
                                     output_filters=256,
                                     kh=3, kw=3, sh=2, sw=2,
                                     scope="layer%d_conv" % 4,
                                     parameter_update_device=encoder_device,
                                     initializer=initializer,
                                     weight_decay=weight_decay,
                                     name_prefix=scope,
                                     weight_decay_rate=weight_decay_rate))
                full_feature_list.append(conv4)

                res1 = resblock(x=conv4,
                                initializer=initializer,
                                layer=5, kh=3, kw=3, sh=1, sw=1,
                                batch_norm_used=True,is_training=is_training,
                                weight_decay=weight_decay,weight_decay_rate=weight_decay_rate,
                                scope="layer%d_resblock" % 5,
                                parameter_update_devices=encoder_device)
                full_feature_list.append(res1)

                res2 = resblock(x=res1,
                                initializer=initializer,
                                layer=6, kh=3, kw=3, sh=1, sw=1,
                                batch_norm_used=True, is_training=is_training,
                                weight_decay=weight_decay, weight_decay_rate=weight_decay_rate,
                                scope="layer%d_resblock" % 6,
                                parameter_update_devices=encoder_device)
                full_feature_list.append(res2)

                res3 = resblock(x=res2,
                                initializer=initializer,
                                layer=7, kh=3, kw=3, sh=1, sw=1,
                                batch_norm_used=True, is_training=is_training,
                                weight_decay=weight_decay, weight_decay_rate=weight_decay_rate,
                                scope="layer%d_resblock" % 7,
                                parameter_update_devices=encoder_device)
                full_feature_list.append(res3)

                res4 = resblock(x=res3,
                                initializer=initializer,
                                layer=8, kh=3, kw=3, sh=1, sw=1,
                                batch_norm_used=True, is_training=is_training,
                                weight_decay=weight_decay, weight_decay_rate=weight_decay_rate,
                                scope="layer%d_resblock" % 8,
                                parameter_update_devices=encoder_device)
                full_feature_list.append(res4)


                return_str = "ResEmdNet-Encoder %d Layers" % (len(full_feature_list))

    return res4, -1, -1, full_feature_list, return_str


def encoder_adobenet_framework(images,
                               is_training,
                               encoder_device,
                               scope,initializer,
                               weight_decay,weight_decay_rate,
                               residual_at_layer=-1,
                               residual_connection_mode=None,
                               reuse=False,
                               adain_use=False):
    residual_connection_mode = None
    residual_at_layer = -1
    adain_use = False
    full_feature_list = list()

    with tf.variable_scope(tf.get_variable_scope()):
        with tf.device(encoder_device):
            with tf.variable_scope(scope):
                if reuse:
                    tf.get_variable_scope().reuse_variables()
                conv1 = relu(conv2d(x=images,
                                    output_filters=64,
                                    kh=7,kw=7, sh=1, sw=1,
                                    scope="layer%d_conv" % 1,
                                    parameter_update_device=encoder_device,
                                    initializer=initializer,
                                    weight_decay=weight_decay,
                                    name_prefix=scope,
                                    weight_decay_rate=weight_decay_rate))
                full_feature_list.append(conv1)

                return_str = "AdobeNet-Encoder %d Layers" % (len(full_feature_list))

    return conv1, -1, -1, full_feature_list, return_str


##############################################################################################
##############################################################################################
##############################################################################################
### Decoders #################################################################################
##############################################################################################
##############################################################################################
##############################################################################################
def wnet_decoder_framework(encoded_layer_list,
                           decoder_input_org,
                           is_training,
                           output_width,
                           output_filters,
                           batch_size,
                           decoder_device,
                           scope,initializer, weight_decay,weight_decay_rate,
                           adain_use,
                           reuse=False,
                           other_info=None):
    def decoder(x,
                output_width,
                output_filters,
                layer,
                enc_layer,
                do_norm=False,
                dropout=False):
        dec = deconv2d(x=tf.nn.relu(x),
                       output_shape=[batch_size, output_width, output_width, output_filters],
                       scope="layer%d_conv" % layer,
                       parameter_update_device=decoder_device,
                       weight_decay=weight_decay,initializer=initializer,
                       name_prefix=scope,
                       weight_decay_rate=weight_decay_rate)
        if do_norm:
            # IMPORTANT: normalization for last layer
            # Very important, otherwise GAN is unstable
            if not adain_use:
                dec = batch_norm(dec, is_training, scope="layer%d_bn" % layer,
                                 parameter_update_device=decoder_device)
            else:
                dec = layer_norm(x=dec, scope="layer%d_ln" % layer,
                                 parameter_update_device=decoder_device)

        if dropout:
            dec = tf.nn.dropout(dec, 0.5)

        if not enc_layer == None:
            dec = tf.concat([dec, enc_layer], 3)
        return dec

    decoder_input = decoder_input_org
    return_str = "WNet-Decoder %d Layers" % int(np.floor(math.log(output_width) / math.log(2)))
    full_decoded_feature_list = list()

    full_encoder_layer_num = int(np.floor(math.log(output_width) / math.log(2)))
    with tf.variable_scope(tf.get_variable_scope()):
        with tf.device(decoder_device):
            with tf.variable_scope(scope):
                if reuse:
                    tf.get_variable_scope().reuse_variables()

                feature_size = int(decoder_input.shape[1])
                ii=0
                while not feature_size == output_width:
                    power_times = full_encoder_layer_num-2-ii
                    output_feature_size = output_width / np.power(2, full_encoder_layer_num - ii - 1)
                    if ii < full_encoder_layer_num-1:
                        output_filter_num_expansion = np.min([np.power(2,power_times), 8])
                        output_filter_num = generator_dim * output_filter_num_expansion
                        do_norm = True
                        do_drop= True and is_training
                        encoded_respective = encoded_layer_list[ii + 1]

                    else:
                        output_filter_num = output_filters
                        do_norm = False
                        do_drop = False
                        encoded_respective = None

                    decoder_output = decoder(x=decoder_input,
                                             output_width=output_feature_size,
                                             output_filters=output_filter_num,
                                             layer=ii + 1,
                                             enc_layer=encoded_respective,
                                             do_norm=do_norm,
                                             dropout=do_drop)
                    full_decoded_feature_list.append(decoder_output)

                    if ii == full_encoder_layer_num-1:
                        output = tf.nn.tanh(decoder_output)
                    ii+=1
                    decoder_input = decoder_output
                    feature_size = int(decoder_input.shape[1])

        return output, full_decoded_feature_list, return_str

def emdnet_decoder_framework(encoded_layer_list,
                             decoder_input_org,
                             is_training,
                             output_width,
                             output_filters,
                             batch_size,
                             decoder_device,
                             scope,initializer, weight_decay,weight_decay_rate,
                             adain_use,
                             reuse=False,
                             other_info=None):
    def decoder(x,
                output_width,
                output_filters,
                layer,
                do_norm=False,
                dropout=False):
        dec = deconv2d(x=tf.nn.relu(x),
                       output_shape=[batch_size, output_width, output_width, output_filters],
                       scope="layer%d_conv" % layer,
                       parameter_update_device=decoder_device,
                       weight_decay=weight_decay,initializer=initializer,
                       name_prefix=scope,
                       weight_decay_rate=weight_decay_rate)
        if do_norm:
            # IMPORTANT: normalization for last layer
            # Very important, otherwise GAN is unstable
            if not adain_use:
                dec = batch_norm(dec, is_training, scope="layer%d_bn" % layer,
                                 parameter_update_device=decoder_device)
            else:
                dec = layer_norm(x=dec, scope="layer%d_ln" % layer,
                                 parameter_update_device=decoder_device)

        if dropout:
            dec = tf.nn.dropout(dec, 0.5)

        return dec

    decoder_input = decoder_input_org
    return_str = "EmdNet-Decoder %d Layers" % int(np.floor(math.log(output_width) / math.log(2)))
    full_decoded_feature_list = list()

    full_encoder_layer_num = int(np.floor(math.log(output_width) / math.log(2)))
    with tf.variable_scope(tf.get_variable_scope()):
        with tf.device(decoder_device):
            with tf.variable_scope(scope):
                if reuse:
                    tf.get_variable_scope().reuse_variables()

                feature_size = int(decoder_input.shape[1])
                ii=0
                while not feature_size == output_width:
                    power_times = full_encoder_layer_num-2-ii
                    output_feature_size = output_width / np.power(2, full_encoder_layer_num - ii - 1)
                    if ii < full_encoder_layer_num-1:
                        output_filter_num_expansion = np.min([np.power(2,power_times), 8])
                        output_filter_num = generator_dim * output_filter_num_expansion
                        do_norm = True
                        do_drop= True and is_training


                    else:
                        output_filter_num = output_filters
                        do_norm = False
                        do_drop = False

                    encoded_respective = encoded_layer_list[ii]
                    if not encoded_respective == None:
                        decoder_input = tf.concat([decoder_input, encoded_respective], axis=3)

                    decoder_output = decoder(x=decoder_input,
                                             output_width=output_feature_size,
                                             output_filters=output_filter_num,
                                             layer=ii + 1,
                                             do_norm=do_norm,
                                             dropout=do_drop)
                    full_decoded_feature_list.append(decoder_output)

                    if ii == full_encoder_layer_num-1:
                        output = tf.nn.tanh(decoder_output)
                    ii+=1
                    decoder_input = decoder_output
                    feature_size = int(decoder_input.shape[1])

        return output, full_decoded_feature_list, return_str


def decoder_resemdnet_framework(encoded_layer_list,
                                decoder_input_org,
                                is_training,
                                output_width,
                                output_filters,
                                batch_size,
                                decoder_device,
                                scope,initializer, weight_decay,weight_decay_rate,
                                adain_use,
                                reuse=False,
                                other_info=None):

    residual_connection_mode = None
    residual_at_layer = -1
    adain_use = False
    full_feature_list = list()
    with tf.variable_scope(tf.get_variable_scope()):
        with tf.device(decoder_device):
            with tf.variable_scope(scope):
                if reuse:
                    tf.get_variable_scope().reuse_variables()

                res1 = resblock(x=decoder_input_org,
                                initializer=initializer,
                                layer=1, kh=3, kw=3, sh=1, sw=1,
                                batch_norm_used=True, is_training=is_training,
                                weight_decay=weight_decay, weight_decay_rate=weight_decay_rate,
                                scope="layer%d_resblock" % 1,
                                parameter_update_devices=decoder_device)
                full_feature_list.append(res1)

                res2 = resblock(x=res1,
                                initializer=initializer,
                                layer=2, kh=3, kw=3, sh=1, sw=1,
                                batch_norm_used=True, is_training=is_training,
                                weight_decay=weight_decay, weight_decay_rate=weight_decay_rate,
                                scope="layer%d_resblock" % 2,
                                parameter_update_devices=decoder_device)
                full_feature_list.append(res2)

                res3 = resblock(x=res2,
                                initializer=initializer,
                                layer=3, kh=3, kw=3, sh=1, sw=1,
                                batch_norm_used=True, is_training=is_training,
                                weight_decay=weight_decay, weight_decay_rate=weight_decay_rate,
                                scope="layer%d_resblock" % 3,
                                parameter_update_devices=decoder_device)
                full_feature_list.append(res3)

                res4 = resblock(x=res3,
                                initializer=initializer,
                                layer=4, kh=3, kw=3, sh=1, sw=1,
                                batch_norm_used=True, is_training=is_training,
                                weight_decay=weight_decay, weight_decay_rate=weight_decay_rate,
                                scope="layer%d_resblock" % 4,
                                parameter_update_devices=decoder_device)
                full_feature_list.append(res4)

                deconv1 = lrelu(deconv2d(x=res4,
                                         kh=3,kw=3,sh=2,sw=2,
                                         output_shape=[batch_size, int(res4.shape[2])*2,
                                                       int(res4.shape[2])*2, 256],
                                         scope="layer%d_deconv" % 5,
                                         parameter_update_device=decoder_device,
                                         initializer=initializer,
                                         weight_decay=weight_decay,
                                         name_prefix=scope,
                                         weight_decay_rate=weight_decay_rate))
                full_feature_list.append(deconv1)


                if other_info==None:
                    deconv2 = lrelu(deconv2d(x=deconv1,
                                             output_shape=[batch_size, int(deconv1.shape[2]) * 2,
                                                           int(deconv1.shape[2]) * 2, 128],
                                             kh=3, kw=3, sh=2, sw=2,
                                             scope="layer%d_deconv" % 6,
                                             parameter_update_device=decoder_device,
                                             initializer=initializer,
                                             weight_decay=weight_decay,
                                             name_prefix=scope,
                                             weight_decay_rate=weight_decay_rate))
                elif other_info=='NN':
                    deconv2 = lrelu(deconv2d(x=deconv1,
                                             output_shape=[batch_size, int(deconv1.shape[2]),
                                                           int(deconv1.shape[2]), 128],
                                             kh=3, kw=3, sh=1, sw=1,
                                             scope="layer%d_deconv" % 6,
                                             parameter_update_device=decoder_device,
                                             initializer=initializer,
                                             weight_decay=weight_decay,
                                             name_prefix=scope,
                                             weight_decay_rate=weight_decay_rate))

                    deconv2 = tf.image.resize_nearest_neighbor(images=deconv2,
                                                               size=[int(deconv2.shape[2])*2, int(deconv2.shape[2])*2])
                full_feature_list.append(deconv2)

                if other_info == None:
                    deconv3 = lrelu(deconv2d(x=deconv2,
                                             output_shape=[batch_size, int(deconv2.shape[2]) * 2,
                                                           int(deconv2.shape[2]) * 2, 64],
                                             kh=3, kw=3, sh=2, sw=2,
                                             scope="layer%d_deconv" % 7,
                                             parameter_update_device=decoder_device,
                                             initializer=initializer,
                                             weight_decay=weight_decay,
                                             name_prefix=scope,
                                             weight_decay_rate=weight_decay_rate))
                elif other_info=='NN':
                    deconv3 = lrelu(deconv2d(x=deconv2,
                                             output_shape=[batch_size, int(deconv2.shape[2]),
                                                           int(deconv2.shape[2]), 64],
                                             kh=3, kw=3, sh=1, sw=1,
                                             scope="layer%d_deconv" % 7,
                                             parameter_update_device=decoder_device,
                                             initializer=initializer,
                                             weight_decay=weight_decay,
                                             name_prefix=scope,
                                             weight_decay_rate=weight_decay_rate))
                    deconv3 = tf.image.resize_nearest_neighbor(images=deconv3,
                                                               size=[int(deconv3.shape[2]) * 2, int(deconv3.shape[2]) * 2])

                full_feature_list.append(deconv3)

                deconv4 = tf.nn.tanh(deconv2d(x=deconv3,
                                              output_shape=[batch_size,output_width,
                                                            output_width, output_filters],
                                              kh=5, kw=5, sh=1, sw=1,
                                              scope="layer%d_deconv" % 8,
                                              parameter_update_device=decoder_device,
                                              initializer=initializer,
                                              weight_decay=weight_decay,
                                              name_prefix=scope,
                                              weight_decay_rate=weight_decay_rate))
                full_feature_list.append(deconv4)

                return_str = "ResEmdNet-Decoder %d Layers" % len(full_feature_list)

                return deconv4, full_feature_list, return_str


def decoder_adobenet_framework(encoded_layer_list,
                               decoder_input_org,
                               is_training,
                               output_width,
                               output_filters,
                               batch_size,
                               decoder_device,
                               scope,initializer, weight_decay,weight_decay_rate,
                               adain_use,
                               reuse=False,
                               other_info=None):

    residual_connection_mode = None
    residual_at_layer = -1
    adain_use = False
    full_feature_list = list()
    with tf.variable_scope(tf.get_variable_scope()):
        with tf.device(decoder_device):
            with tf.variable_scope(scope):
                if reuse:
                    tf.get_variable_scope().reuse_variables()
                normal_conv_resblock1 = normal_conv_resblock(x=decoder_input_org,
                                                             initializer=initializer,
                                                             is_training=is_training,
                                                             layer=1,
                                                             kh=3, kw=3, sh=1, sw=1,
                                                             batch_norm_used=True,
                                                             weight_decay=weight_decay,
                                                             weight_decay_rate=weight_decay_rate,
                                                             scope="layer%d_normal_resblock" % 1,
                                                             parameter_update_devices=decoder_device)
                full_feature_list.append(normal_conv_resblock1)

                dilated_conv_resblock1 = dilated_conv_resblock(x=normal_conv_resblock1,
                                                               initializer=initializer,
                                                               is_training=is_training,
                                                               layer=2,
                                                               dilation=2, kh=3, kw=3,
                                                               batch_norm_used=True,
                                                               weight_decay=weight_decay,
                                                               weight_decay_rate=weight_decay_rate,
                                                               scope="layer%d_dilated_resblock" % 2,
                                                               parameter_update_devices=decoder_device)
                full_feature_list.append(dilated_conv_resblock1)

                dilated_conv_resblock2 = dilated_conv_resblock(x=dilated_conv_resblock1,
                                                               initializer=initializer,
                                                               is_training=is_training,
                                                               layer=3,
                                                               dilation=4, kh=3, kw=3,
                                                               batch_norm_used=True,
                                                               weight_decay=weight_decay,
                                                               weight_decay_rate=weight_decay_rate,
                                                               scope="layer%d_dilated_resblock" % 3,
                                                               parameter_update_devices=decoder_device)
                full_feature_list.append(dilated_conv_resblock2)

                dilated_conv_1 = relu(batch_norm(x=dilated_conv2d(x=dilated_conv_resblock2,
                                                                  output_filters=128,
                                                                  weight_decay_rate=weight_decay_rate, weight_decay=weight_decay,
                                                                  kh=3, kw=3, dilation=2,
                                                                  initializer=initializer,
                                                                  scope="layer%d_dilated_conv" % 4,
                                                                  parameter_update_device=decoder_device,
                                                                  name_prefix=scope),
                                                 is_training=is_training,
                                                 scope="layer%d_bn"% 4,
                                                 parameter_update_device=decoder_device))


                full_feature_list.append(dilated_conv_1)

                generated_img = tf.nn.tanh(conv2d(x=dilated_conv_1,
                                                  output_filters=1,
                                                  weight_decay_rate=weight_decay_rate, weight_decay=weight_decay,
                                                  kh=3, kw=3, sw=1, sh=1,
                                                  initializer=initializer,
                                                  scope="layer%d_normal_conv" % 5,
                                                  parameter_update_device=decoder_device,
                                                  name_prefix=scope))
                full_feature_list.append(generated_img)

    return_str = "AdobeNet-Decoder %d Layers" % len(full_feature_list)

    return generated_img, full_feature_list, return_str


##############################################################################################
##############################################################################################
##############################################################################################
### Mixers ###################################################################################
##############################################################################################
##############################################################################################
##############################################################################################
def wnet_feature_mixer_framework(generator_device,scope,is_training,reuse,initializer,debug_mode,
                                 weight_decay,weight_decay_rate,style_input_number,
                                 residual_block_num, residual_at_layer,
                                 encoded_style_final_list,
                                 style_short_cut_interface_list,style_residual_interface_list,
                                 content_short_cut_interface, content_residual_interface,
                                 full_style_feature_list,
                                 adain_use,adain_preparation_model):



    # multiple encoded information average calculation for style reference encoder
    with tf.variable_scope(tf.get_variable_scope()):
        with tf.device(generator_device):
            with tf.variable_scope(scope):
                if reuse:
                    tf.get_variable_scope().reuse_variables()
                for ii in range(style_input_number):
                    if ii == 0:
                        encoded_style_final = tf.expand_dims(encoded_style_final_list[ii], axis=0)
                        style_short_cut_interface = list()
                        for jj in range(len(style_short_cut_interface_list[ii])):
                            style_short_cut_interface.append(
                                tf.expand_dims(style_short_cut_interface_list[ii][jj], axis=0))
                        style_residual_interface = list()
                        for jj in range(len(style_residual_interface_list[ii])):
                            style_residual_interface.append(
                                tf.expand_dims(style_residual_interface_list[ii][jj], axis=0))
                    else:
                        encoded_style_final = tf.concat(
                            [encoded_style_final, tf.expand_dims(encoded_style_final_list[ii], axis=0)], axis=0)
                        for jj in range(len(style_short_cut_interface_list[ii])):
                            style_short_cut_interface[jj] = tf.concat([style_short_cut_interface[jj],
                                                                       tf.expand_dims(
                                                                           style_short_cut_interface_list[ii][jj],
                                                                           axis=0)], axis=0)

                        for jj in range(len(style_residual_interface_list[ii])):
                            style_residual_interface[jj] = tf.concat([style_residual_interface[jj], tf.expand_dims(
                                style_residual_interface_list[ii][jj], axis=0)], axis=0)

                encoded_style_final_avg = tf.reduce_mean(encoded_style_final, axis=0)
                encoded_style_final_max = tf.reduce_max(encoded_style_final, axis=0)
                encoded_style_final_min = tf.reduce_min(encoded_style_final, axis=0)
                encoded_style_final = tf.concat([encoded_style_final_avg, encoded_style_final_max, encoded_style_final_min], axis=3)

                style_shortcut_batch_diff = 0
                for ii in range(len(style_short_cut_interface)):
                    style_short_cut_avg = tf.reduce_mean(style_short_cut_interface[ii], axis=0)
                    style_short_cut_max = tf.reduce_max(style_short_cut_interface[ii], axis=0)
                    style_short_cut_min = tf.reduce_min(style_short_cut_interface[ii], axis=0)
                    style_short_cut_interface[ii] = tf.concat(
                        [style_short_cut_avg, style_short_cut_max, style_short_cut_min], axis=3)
                    style_shortcut_batch_diff += _calculate_batch_diff(input_feature=style_short_cut_interface[ii])
                style_shortcut_batch_diff = style_shortcut_batch_diff / len(style_short_cut_interface)

                style_residual_batch_diff = 0
                for ii in range(len(style_residual_interface)):
                    style_residual_avg = tf.reduce_mean(style_residual_interface[ii], axis=0)
                    style_residual_max = tf.reduce_max(style_residual_interface[ii], axis=0)
                    style_residual_min = tf.reduce_min(style_residual_interface[ii], axis=0)
                    style_residual_interface[ii] = tf.concat(
                        [style_residual_avg, style_residual_max, style_residual_min], axis=3)
                    style_residual_batch_diff += _calculate_batch_diff(input_feature=style_residual_interface[ii])
                style_residual_batch_diff = style_residual_batch_diff / len(style_residual_interface)

    # full style feature reformat
    if adain_use:
        full_style_feature_list_reformat = list()
        for ii in range(len(full_style_feature_list)):
            for jj in range(len(full_style_feature_list[ii])):

                current_feature = tf.expand_dims(full_style_feature_list[ii][jj], axis=0)
                if ii == 0:
                    full_style_feature_list_reformat.append(current_feature)
                else:
                    full_style_feature_list_reformat[jj] = tf.concat(
                        [full_style_feature_list_reformat[jj], current_feature], axis=0)
    else:
        full_style_feature_list_reformat = None

    # residual interfaces && short cut interfaces are fused together
    fused_residual_interfaces = list()
    fused_shortcut_interfaces = list()
    for ii in range(len(content_residual_interface)):
        current_content_residual_size = int(content_residual_interface[ii].shape[1])
        output_current_residual = content_residual_interface[ii]
        if adain_use:  # for adaptive instance normalization
            for jj in range(len(full_style_feature_list_reformat)):
                if int(full_style_feature_list_reformat[jj].shape[2]) == int(output_current_residual.shape[1]):
                    break
            output_current_residual = adaptive_instance_norm(content=output_current_residual,
                                                             style=full_style_feature_list_reformat[jj])

        for jj in range(len(style_residual_interface)):
            current_style_residual_size = int(style_residual_interface[jj].shape[1])
            if current_style_residual_size == current_content_residual_size:
                output_current_residual = tf.concat([output_current_residual, style_residual_interface[jj]], axis=3)
        fused_residual_interfaces.append(output_current_residual)
    for ii in range(len(content_short_cut_interface)):
        current_content_shortcut_size = int(content_short_cut_interface[ii].shape[1])
        output_current_shortcut = content_short_cut_interface[ii]

        if adain_use:  # for adaptive instance normalization
            for jj in range(len(full_style_feature_list_reformat)):
                if int(full_style_feature_list_reformat[jj].shape[2]) == int(output_current_shortcut.shape[1]):
                    break
            output_current_shortcut = adaptive_instance_norm(content=output_current_shortcut,
                                                             style=full_style_feature_list_reformat[jj])

        for jj in range(len(style_short_cut_interface)):
            current_style_short_cut_size = int(style_short_cut_interface[jj].shape[1])
            if current_style_short_cut_size == current_content_shortcut_size:
                output_current_shortcut = tf.concat([output_current_shortcut, style_short_cut_interface[jj]],
                                                    axis=3)
        fused_shortcut_interfaces.append(output_current_shortcut)

    # fused resudual interfaces are put into the residual blocks
    if not residual_block_num == 0 or not residual_at_layer == -1:
        residual_output_list, _ = residual_block_implementation(input_list=fused_residual_interfaces,
                                                                residual_num=residual_block_num,
                                                                residual_at_layer=residual_at_layer,
                                                                is_training=is_training,
                                                                residual_device=generator_device,
                                                                scope=scope + '/resblock',
                                                                reuse=reuse,
                                                                initializer=initializer,
                                                                weight_decay=weight_decay,
                                                                weight_decay_rate=weight_decay_rate,
                                                                style_features=full_style_feature_list_reformat,
                                                                adain_use=adain_use,
                                                                adain_preparation_model=adain_preparation_model,
                                                                debug_mode=debug_mode)

    # combination of all the encoder outputs
    fused_shortcut_interfaces.reverse()
    encoded_layer_list = fused_shortcut_interfaces
    encoded_layer_list.extend(residual_output_list)

    return encoded_layer_list, style_shortcut_batch_diff, style_residual_batch_diff, \
           encoded_style_final

def emdnet_mixer_with_adain(generator_device,reuse,scope,initializer,
                            weight_decay,weight_decay_rate,
                            encoded_content_final,content_shortcut_interface,encoded_style_final):

    # mixer
    with tf.variable_scope(tf.get_variable_scope()):
        with tf.device(generator_device):
            with tf.variable_scope(scope):
                if reuse:
                    tf.get_variable_scope().reuse_variables()

                encoded_style_final_expand = tf.expand_dims(encoded_style_final,axis=0)

                mixed_feature = adaptive_instance_norm(content=encoded_content_final,
                                                       style=encoded_style_final_expand)

                valid_encoded_content_shortcut_list = list()
                batch_diff = 0
                batch_diff_count = 0
                for ii in range(len(content_shortcut_interface)):
                    if ii == 0 or ii == len(content_shortcut_interface) - 1:
                        valid_encoded_content_shortcut_list.append(content_shortcut_interface[ii])
                        batch_diff += _calculate_batch_diff(input_feature=content_shortcut_interface[ii])
                        batch_diff_count += 1
                    else:
                        valid_encoded_content_shortcut_list.append(None)
                valid_encoded_content_shortcut_list.reverse()
                batch_diff = batch_diff / batch_diff_count

    return valid_encoded_content_shortcut_list, mixed_feature, batch_diff

def emdnet_mixer_non_adain(generator_device,reuse,scope,initializer,
                           weight_decay,weight_decay_rate,
                           encoded_content_final,content_shortcut_interface,encoded_style_final):




    # mixer
    with tf.variable_scope(tf.get_variable_scope()):
        with tf.device(generator_device):

            with tf.variable_scope(scope):
                if reuse:
                    tf.get_variable_scope().reuse_variables()

                encoded_content_final_squeeze = tf.squeeze(encoded_content_final)
                encoded_style_final_squeeze = tf.squeeze(encoded_style_final)
                encoded_content_fc = lrelu(fc(x=encoded_content_final_squeeze,
                                              output_size=generator_dim,
                                              scope="emd_mixer/content_fc",
                                              parameter_update_device=generator_device,
                                              initializer=initializer,
                                              weight_decay=weight_decay,
                                              name_prefix=scope, weight_decay_rate=weight_decay_rate))
                encoded_style_fc = lrelu(fc(x=encoded_style_final_squeeze,
                                            output_size=generator_dim,
                                            scope="emd_mixer/style_fc",
                                            parameter_update_device=generator_device,
                                            initializer=initializer,
                                            weight_decay=weight_decay,
                                            name_prefix=scope, weight_decay_rate=weight_decay_rate))
                mix_content_style = emd_mixer(content=encoded_content_fc,
                                              style=encoded_style_fc,
                                              initializer=initializer,
                                              device=generator_device)
                mixed_fc = relu(fc(x=mix_content_style,
                                   output_size=int(encoded_content_final.shape[3]),
                                   scope="emd_mixer/mixed_fc",
                                   parameter_update_device=generator_device,
                                   initializer=initializer,
                                   weight_decay=weight_decay,
                                   name_prefix=scope, weight_decay_rate=weight_decay_rate))

                mixed_fc = tf.expand_dims(mixed_fc, axis=1)
                mixed_fc = tf.expand_dims(mixed_fc, axis=1)

                valid_encoded_content_shortcut_list = list()
                batch_diff = 0
                batch_diff_count = 0
                for ii in range(len(content_shortcut_interface)):
                    if ii == 0 or ii == len(content_shortcut_interface) - 1:
                        valid_encoded_content_shortcut_list.append(content_shortcut_interface[ii])
                        batch_diff += _calculate_batch_diff(input_feature=content_shortcut_interface[ii])
                        batch_diff_count += 1
                    else:
                        valid_encoded_content_shortcut_list.append(None)
                valid_encoded_content_shortcut_list.reverse()
                batch_diff = batch_diff / batch_diff_count

    return valid_encoded_content_shortcut_list,mixed_fc,batch_diff


##############################################################################################
##############################################################################################
##############################################################################################
### ResBlocks ################################################################################
##############################################################################################
##############################################################################################
##############################################################################################
def single_resblock(adain_use, is_training, residual_device, initializer,scope,
                    weight_decay, weight_decay_rate,
                    x,layer,style):

    filters = int(x.shape[3])
    if not adain_use:
        norm1 = batch_norm(x=x,
                           is_training=is_training,
                           scope="layer%d_bn1" % layer,
                           parameter_update_device=residual_device)
    else:
        norm1 = adaptive_instance_norm(content=x,
                                       style=style)

    act1 = relu(norm1)
    conv1 = conv2d(x=act1,
                   output_filters=filters,
                   scope="layer%d_conv1" % layer,
                   parameter_update_device=residual_device,
                   kh=3,kw=3,sh=1,sw=1,
                   initializer=initializer,
                   weight_decay=weight_decay,
                   name_prefix=scope,
                   weight_decay_rate=weight_decay_rate)
    if not adain_use:
        norm2 = batch_norm(x=conv1,
                           is_training=is_training,
                           scope="layer%d_bn2" % layer,
                           parameter_update_device=residual_device)
    else:
        norm2 = adaptive_instance_norm(content=conv1,
                                       style=style)
    act2 = relu(norm2)
    conv2 = conv2d(x=act2,
                   output_filters=filters,
                   scope="layer%d_conv2" % layer,
                   parameter_update_device=residual_device,
                   initializer=initializer,
                   weight_decay=weight_decay,name_prefix=scope,
                   weight_decay_rate=weight_decay_rate,
                   kh=3,kw=3,sh=1,sw=1)

    output = x + conv2

    return output

def residual_block_implementation(input_list,
                                  residual_num,
                                  residual_at_layer,
                                  is_training,
                                  residual_device,
                                  reuse,scope,
                                  initializer,
                                  weight_decay,
                                  weight_decay_rate,
                                  style_features,
                                  adain_use=False,
                                  adain_preparation_model=None,
                                  debug_mode=False):


    return_str = "Residual %d Blocks" % residual_num
    input_list.reverse()
    with tf.variable_scope(tf.get_variable_scope()):
        with tf.device(residual_device):
            residual_output_list = list()

            if not reuse:
                print (print_separater)
                print ('Adaptive Instance Normalization for Residual Preparations: %s' % adain_preparation_model)
                print (print_separater)

            for ii in range(len(input_list)):
                current_residual_num = residual_num + 2 * ii
                current_residual_input = input_list[ii]
                current_scope = scope + '_onEncDecLyr%d' % (residual_at_layer - ii)


                if adain_use:
                    with tf.variable_scope(current_scope):
                        for jj in range(len(style_features)):
                            if int(style_features[jj].shape[2]) == int(current_residual_input.shape[1]):
                                break

                        for jj in range(int(style_features[ii].shape[0])):
                            if reuse or jj > 0:
                                tf.get_variable_scope().reuse_variables()

                            batch_size = int(style_features[ii][jj, :, :, :, :].shape[0])
                            if batch_size == 1:
                                current_init_residual_input = style_features[ii][jj, :, :, :, :]
                            else:
                                current_init_residual_input = tf.squeeze(style_features[ii][jj, :, :, :, :])

                            if adain_preparation_model == 'Multi':
                                # multiple cnn layer built to make the style_conv be incorporated with the dimension of the residual blocks
                                log_input = math.log(int(current_init_residual_input.shape[3])) / math.log(2)
                                if math.log(int(current_init_residual_input.shape[3])) < math.log(int(current_residual_input.shape[3])):
                                    if np.floor(log_input) < math.log(int(current_residual_input.shape[3])) / math.log(2):
                                        filter_num_start = int(np.floor(log_input)) + 1
                                    else:
                                        filter_num_start = int(np.floor(log_input))
                                    filter_num_start = int(math.pow(2,filter_num_start))
                                elif math.log(int(current_init_residual_input.shape[3])) > math.log(int(current_residual_input.shape[3])):
                                    if np.ceil(log_input) > math.log(int(current_residual_input.shape[3])) / math.log(2):
                                        filter_num_start = int(np.ceil(log_input)) - 1
                                    else:
                                        filter_num_start = int(np.ceil(log_input))
                                    filter_num_start = int(math.pow(2, filter_num_start))
                                else:
                                    filter_num_start = int(current_residual_input.shape[3])
                                filter_num_end = int(current_residual_input.shape[3])

                                if int(current_init_residual_input.shape[3]) == filter_num_end:
                                    continue_build = False
                                    style_conv = current_init_residual_input
                                else:
                                    continue_build = True


                                current_style_conv_input = current_init_residual_input
                                current_output_filter_num = filter_num_start
                                style_cnn_layer_num = 0
                                while continue_build:
                                    style_conv = conv2d(x=current_style_conv_input,
                                                        output_filters=current_output_filter_num,
                                                        scope="conv0_style_layer%d" % (style_cnn_layer_num+1),
                                                        parameter_update_device=residual_device,
                                                        kh=3, kw=3, sh=1, sw=1,
                                                        initializer=initializer,
                                                        weight_decay=weight_decay,
                                                        name_prefix=scope,
                                                        weight_decay_rate=weight_decay_rate)
                                    if not (reuse or jj > 0):
                                        print (style_conv)
                                    style_conv = relu(style_conv)


                                    current_style_conv_input = style_conv

                                    if filter_num_start < filter_num_end:
                                        current_output_filter_num = current_output_filter_num * 2
                                    else:
                                        current_output_filter_num = current_output_filter_num / 2
                                    style_cnn_layer_num += 1

                                    if current_output_filter_num > filter_num_end and \
                                            math.log(int(current_init_residual_input.shape[3])) < math.log(int(current_residual_input.shape[3])):
                                        current_output_filter_num = filter_num_end
                                    if current_output_filter_num < filter_num_end and \
                                            math.log(int(current_init_residual_input.shape[3])) > math.log(int(current_residual_input.shape[3])):
                                        current_output_filter_num = filter_num_end

                                    if int(style_conv.shape[3]) == filter_num_end:
                                        continue_build = False



                            elif adain_preparation_model == 'Single':
                                if int(current_init_residual_input.shape[3]) == int(current_residual_input.shape[3]):
                                    style_conv = current_init_residual_input
                                else:
                                    style_conv = conv2d(x=current_init_residual_input,
                                                        output_filters=int(current_residual_input.shape[3]),
                                                        scope="conv0_style_layer0",
                                                        parameter_update_device=residual_device,
                                                        kh=3, kw=3, sh=1, sw=1,
                                                        initializer=initializer,
                                                        weight_decay=weight_decay,
                                                        name_prefix=scope,
                                                        weight_decay_rate=weight_decay_rate)
                                    if not (reuse or jj > 0):
                                        print (style_conv)
                                    style_conv = relu(style_conv)



                            if jj == 0:
                                style_features_new = tf.expand_dims(style_conv, axis=0)
                            else:
                                style_features_new = tf.concat([style_features_new,
                                                                tf.expand_dims(style_conv, axis=0)],
                                                               axis=0)

                    if (not reuse) and (not math.log(int(current_init_residual_input.shape[3])) == math.log(int(current_residual_input.shape[3]))):
                        print (print_separater)


                else:
                    style_features_new=None


                with tf.variable_scope(current_scope):
                    if reuse:
                        tf.get_variable_scope().reuse_variables()

                    for jj in range(current_residual_num):
                        if jj == 0:
                            residual_input = current_residual_input
                        else:
                            residual_input = residual_block_output
                        residual_block_output = \
                            single_resblock(adain_use=adain_use,
                                            is_training=is_training,
                                            residual_device=residual_device,
                                            initializer=initializer,
                                            scope=scope,
                                            weight_decay=weight_decay,
                                            weight_decay_rate=weight_decay_rate,
                                            x=residual_input,
                                            layer=jj+1,
                                            style=style_features_new)
                        if jj == current_residual_num-1:
                            residual_output = residual_block_output

                    residual_output_list.append(residual_output)


    if (not reuse) and adain_use and (not debug_mode):
        print(print_separater)
        raw_input("Press enter to continue")
    print(print_separater)

    return residual_output_list, return_str



##############################################################################################
##############################################################################################
##############################################################################################
### GeneratorFrameworks ######################################################################
##############################################################################################
##############################################################################################
##############################################################################################
def EmdNet_Generator(content_prototype,
                     style_reference,
                     is_training,
                     batch_size,
                     generator_device,
                     residual_at_layer,
                     residual_block_num,
                     scope,
                     initializer,
                     weight_decay, weight_decay_rate,
                     reuse=False,
                     adain_use=False,
                     adain_preparation_model=None,
                     debug_mode=True,
                     other_info=None):

    style_input_number = len(style_reference)
    content_prototype_number = int(content_prototype.shape[3])

    # content prototype encoder part
    encoded_content_final, content_shortcut_interface, _, content_full_feature_list, _ = \
        encoder_framework(images=content_prototype,
                          is_training=is_training,
                          encoder_device=generator_device,
                          residual_at_layer=residual_at_layer,
                          residual_connection_mode='Multi',
                          scope=scope + '/content_encoder',
                          reuse=reuse,
                          initializer=initializer,
                          weight_decay=weight_decay,
                          weight_decay_rate=weight_decay_rate,
                          adain_use=adain_use)

    # style reference encoder part
    for ii in range(len(style_reference)):
        if ii == 0:
            style_reference_tensor = style_reference[ii]
        else:
            style_reference_tensor = tf.concat([style_reference_tensor,style_reference[ii]],
                                               axis=3)
    encoded_style_final, _, _, style_full_feature_list, _ = \
        encoder_framework(images=style_reference_tensor,
                          is_training=is_training,
                          encoder_device=generator_device,
                          residual_at_layer=residual_at_layer,
                          residual_connection_mode='Single',
                          scope=scope + '/style_encoder',
                          reuse=reuse,
                          initializer=initializer,
                          weight_decay=weight_decay,
                          weight_decay_rate=weight_decay_rate,
                          adain_use=adain_use)

    # emd network mixer
    if adain_use==0:
        valid_encoded_content_shortcut_list, mixed_fc, batch_diff = \
            emdnet_mixer_non_adain(generator_device=generator_device,
                                   reuse=reuse, scope=scope, initializer=initializer,
                                   weight_decay=weight_decay, weight_decay_rate=weight_decay_rate,
                                   encoded_content_final=encoded_content_final,
                                   content_shortcut_interface=content_shortcut_interface,
                                   encoded_style_final=encoded_style_final)
    else:
        valid_encoded_content_shortcut_list, mixed_fc, batch_diff = \
            emdnet_mixer_with_adain(generator_device=generator_device,
                                    reuse=reuse, scope=scope, initializer=initializer,
                                    weight_decay=weight_decay, weight_decay_rate=weight_decay_rate,
                                    encoded_content_final=encoded_content_final,
                                    content_shortcut_interface=content_shortcut_interface,
                                    encoded_style_final=encoded_style_final)

    # decoder part
    img_width = int(content_prototype.shape[1])
    img_filters = int(int(content_prototype.shape[3]) / content_prototype_number)
    generated_img, decoder_full_feature_list, _ = \
        emdnet_decoder_framework(encoded_layer_list=valid_encoded_content_shortcut_list,
                                 decoder_input_org=mixed_fc,
                                 is_training=is_training,
                                 output_width=img_width,
                                 output_filters=img_filters,
                                 batch_size=batch_size,
                                 decoder_device=generator_device,
                                 scope=scope + '/decoder',
                                 reuse=reuse,
                                 weight_decay=weight_decay,
                                 initializer=initializer,
                                 weight_decay_rate=weight_decay_rate,
                                 adain_use=adain_use)

    return_str = ("Emd-Net-GeneratorEncoderDecoder %d Layers"
                  % (int(np.floor(math.log(int(content_prototype[0].shape[1])) / math.log(2)))))


    return generated_img, encoded_content_final, encoded_style_final, return_str, \
           batch_diff, -1, \
           content_full_feature_list, style_full_feature_list, decoder_full_feature_list

def ResEmd_EmdNet_Generator(content_prototype,
                            style_reference,
                            is_training,
                            batch_size,
                            generator_device,
                            scope,
                            initializer,
                            weight_decay, weight_decay_rate,
                            reuse=False,
                            adain_use=False,
                            residual_at_layer=-1,
                            residual_block_num=-1,
                            adain_preparation_model=None,
                            debug_mode=True,
                            other_info=None):



    residual_at_layer=-1
    residual_block_num=-1
    adain_preparation_model=None
    adain_use=False

    style_input_number = len(style_reference)
    content_prototype_number = int(content_prototype.shape[3])

    # style reference encoder part
    for ii in range(len(style_reference)):
        if ii == 0:
            style_reference_tensor = style_reference[ii]
        else:
            style_reference_tensor = tf.concat([style_reference_tensor, style_reference[ii]], axis=3)
    encoded_style_final, _, _, style_full_feature_list, _ = \
        encoder_resemd_framework(images=style_reference_tensor,
                                 is_training=is_training,
                                 encoder_device=generator_device,
                                 scope=scope + '/style_encoder',
                                 reuse=reuse,
                                 initializer=initializer,
                                 weight_decay=weight_decay,
                                 weight_decay_rate=weight_decay_rate,
                                 adain_use=adain_use)

    # content prototype encoder part
    encoded_content_final, _, _, content_full_feature_list, _ = \
        encoder_resemd_framework(images=content_prototype,
                                 is_training=is_training,
                                 encoder_device=generator_device,
                                 residual_at_layer=residual_at_layer,
                                 scope=scope + '/content_encoder',
                                 reuse=reuse,
                                 initializer=initializer,
                                 weight_decay=weight_decay,
                                 weight_decay_rate=weight_decay_rate,
                                 adain_use=adain_use)

    # res-emd network mixer
    with tf.variable_scope(tf.get_variable_scope()):
        with tf.device(generator_device):
            with tf.variable_scope(scope):
                if reuse:
                    tf.get_variable_scope().reuse_variables()
                mixed_feature = adaptive_instance_norm(content=encoded_content_final,
                                                       style=tf.expand_dims(encoded_style_final, axis=0))

                style_batch_diff = 0
                content_batch_diff = 0
                for ii in range(len(style_full_feature_list)):
                    current_batch_diff = _calculate_batch_diff(style_full_feature_list[ii])
                    style_batch_diff+=current_batch_diff
                style_batch_diff = style_batch_diff / len(style_full_feature_list)
                for ii in range(len(content_full_feature_list)):
                    current_batch_diff = _calculate_batch_diff(content_full_feature_list[ii])
                    content_batch_diff += current_batch_diff
                content_batch_diff = content_batch_diff / len(content_full_feature_list)


    # decoder part
    img_width = int(content_prototype.shape[1])
    img_filters = int(int(content_prototype.shape[3]) / content_prototype_number)
    generated_img, decoder_full_feature_list, _ = \
        decoder_resemdnet_framework(encoded_layer_list=-1,
                                    decoder_input_org=mixed_feature,
                                    is_training=is_training,
                                    output_width=img_width,
                                    output_filters=img_filters,
                                    batch_size=batch_size,
                                    decoder_device=generator_device,
                                    scope=scope + '/decoder',
                                    reuse=reuse,
                                    weight_decay=weight_decay,
                                    initializer=initializer,
                                    weight_decay_rate=weight_decay_rate,
                                    adain_use=adain_use,
                                    other_info=other_info)

    if other_info == None:
        return_str = ("Res-Emd-Net-GeneratorEncoderDecoder %d Layers"
                      % (int(np.floor(math.log(int(content_prototype[0].shape[1])) / math.log(2)))))
    elif other_info== 'NN':
        return_str = ("NN-Res-Emd-Net-GeneratorEncoderDecoder %d Layers"
                      % (int(np.floor(math.log(int(content_prototype[0].shape[1])) / math.log(2)))))


    return generated_img, encoded_content_final, encoded_style_final, return_str, \
           style_batch_diff, content_batch_diff, \
           content_full_feature_list, style_full_feature_list, decoder_full_feature_list


def WNet_Generator(content_prototype,
                   style_reference,
                   is_training,
                   batch_size,
                   generator_device,
                   residual_at_layer,
                   residual_block_num,
                   scope,
                   initializer,
                   weight_decay, weight_decay_rate,
                   reuse=False,
                   adain_use=False,
                   adain_preparation_model=None,
                   debug_mode=True,
                   other_info=None):

    style_input_number = len(style_reference)
    content_prototype_number = int(content_prototype.shape[3])

    # content prototype encoder part
    encoded_content_final, content_short_cut_interface, content_residual_interface, content_full_feature_list, _ = \
        encoder_framework(images=content_prototype,
                          is_training=is_training,
                          encoder_device=generator_device,
                          residual_at_layer=residual_at_layer,
                          residual_connection_mode='Multi',
                          scope=scope + '/content_encoder',
                          reuse=reuse,
                          initializer=initializer,
                          weight_decay=weight_decay,
                          weight_decay_rate=weight_decay_rate,
                          adain_use=adain_use)

    # style reference encoder part
    encoded_style_final_list = list()
    style_short_cut_interface_list = list()
    style_residual_interface_list = list()
    full_style_feature_list = list()
    for ii in range(style_input_number):
        if ii==0:
            curt_reuse=reuse
            current_weight_decay = weight_decay
        else:
            curt_reuse=True
            current_weight_decay = False

        encoded_style_final, current_style_short_cut_interface, current_style_residual_interface, current_full_feature_list, _ = \
            encoder_framework(images=style_reference[ii],
                              is_training=is_training,
                              encoder_device=generator_device,
                              residual_at_layer=residual_at_layer,
                              residual_connection_mode='Single',
                              scope=scope + '/style_encoder',
                              reuse=curt_reuse,
                              initializer=initializer,
                              weight_decay=current_weight_decay,
                              weight_decay_rate=weight_decay_rate,
                              adain_use=adain_use)
        encoded_style_final_list.append(encoded_style_final)
        style_short_cut_interface_list.append(current_style_short_cut_interface)
        style_residual_interface_list.append(current_style_residual_interface)
        full_style_feature_list.append(current_full_feature_list)

    encoded_layer_list, style_shortcut_batch_diff, style_residual_batch_diff,encoded_style_final = \
        wnet_feature_mixer_framework(generator_device=generator_device,
                                     scope=scope,
                                     is_training=is_training,
                                     reuse=reuse,
                                     initializer=initializer,
                                     debug_mode=debug_mode,
                                     weight_decay=weight_decay,
                                     weight_decay_rate=weight_decay_rate,
                                     style_input_number=style_input_number,
                                     residual_block_num=residual_block_num,
                                     residual_at_layer=residual_at_layer,
                                     encoded_style_final_list=encoded_style_final_list,
                                     style_short_cut_interface_list=style_short_cut_interface_list,
                                     style_residual_interface_list=style_residual_interface_list,
                                     content_short_cut_interface=content_short_cut_interface,
                                     content_residual_interface=content_residual_interface,
                                     full_style_feature_list=full_style_feature_list,
                                     adain_use=adain_use,
                                     adain_preparation_model=adain_preparation_model)


    return_str = ("W-Net-GeneratorEncoderDecoder %d Layers with %d ResidualBlocks connecting %d-th layer"
                  % (int(np.floor(math.log(int(content_prototype[0].shape[1])) / math.log(2))),
                     residual_block_num,
                     residual_at_layer))

    # decoder part
    img_width = int(content_prototype.shape[1])
    img_filters = int(int(content_prototype.shape[3]) / content_prototype_number)
    generated_img,decoder_full_feature_list, _ = \
        wnet_decoder_framework(encoded_layer_list=encoded_layer_list,
                               decoder_input_org=encoded_layer_list[0],
                               is_training=is_training,
                               output_width=img_width,
                               output_filters=img_filters,
                               batch_size=batch_size,
                               decoder_device=generator_device,
                               scope=scope+'/decoder',
                               reuse=reuse,
                               weight_decay=weight_decay,
                               initializer=initializer,
                               weight_decay_rate=weight_decay_rate,
                               adain_use=adain_use)

    return generated_img, encoded_content_final, encoded_style_final, return_str, \
           style_shortcut_batch_diff, style_residual_batch_diff, \
           content_full_feature_list, full_style_feature_list, decoder_full_feature_list


def AdobeNet_Generator(content_prototype,
                       style_reference,
                       is_training,
                       batch_size,
                       generator_device,
                       residual_at_layer,
                       residual_block_num,
                       scope,
                       initializer,
                       weight_decay, weight_decay_rate,
                       reuse=False,
                       adain_use=False,
                       adain_preparation_model=None,
                       debug_mode=True,
                       other_info=None):
    style_input_number = len(style_reference)
    content_prototype_number = int(content_prototype.shape[3])

    # style reference encoder part
    for ii in range(len(style_reference)):
        if ii == 0:
            style_reference_tensor = style_reference[ii]
        else:
            style_reference_tensor = tf.concat([style_reference_tensor, style_reference[ii]], axis=3)

    encoded_style_final, _, _, style_full_feature_list, _ = \
        encoder_adobenet_framework(images=style_reference_tensor,
                                   is_training=is_training,
                                   encoder_device=generator_device,
                                   scope=scope + '/style_encoder',
                                   reuse=reuse,
                                   initializer=initializer,
                                   weight_decay=weight_decay,
                                   weight_decay_rate=weight_decay_rate,
                                   adain_use=adain_use)

    # content prototype encoder part
    encoded_content_final, _, _, content_full_feature_list, _ = \
        encoder_adobenet_framework(images=content_prototype,
                                   is_training=is_training,
                                   encoder_device=generator_device,
                                   residual_at_layer=residual_at_layer,
                                   scope=scope + '/content_encoder',
                                   reuse=reuse,
                                   initializer=initializer,
                                   weight_decay=weight_decay,
                                   weight_decay_rate=weight_decay_rate,
                                   adain_use=adain_use)

    # mixer
    mixed_feature = tf.concat([encoded_content_final,encoded_style_final], axis=3)
    style_batch_diff=0
    content_batch_diff=0
    for ii in range(len(content_full_feature_list)):
        content_batch_diff+=_calculate_batch_diff(content_full_feature_list[ii])
    content_batch_diff=content_batch_diff/len(content_full_feature_list)
    for ii in range(len(style_full_feature_list)):
        style_batch_diff+=_calculate_batch_diff(style_full_feature_list[ii])
    style_batch_diff=style_batch_diff/len(style_full_feature_list)

    # decoder
    img_width = int(content_prototype.shape[1])
    img_filters = int(int(content_prototype.shape[3]) / content_prototype_number)
    generated_img, decoder_full_feature_list, _ = \
        decoder_adobenet_framework(encoded_layer_list=-1,
                                   decoder_input_org=mixed_feature,
                                   is_training=is_training,
                                   output_width=img_width,
                                   output_filters=img_filters,
                                   batch_size=batch_size,
                                   decoder_device=generator_device,
                                   scope=scope + '/decoder',
                                   reuse=reuse,
                                   weight_decay=weight_decay,
                                   initializer=initializer,
                                   weight_decay_rate=weight_decay_rate,
                                   adain_use=adain_use,
                                   other_info=other_info)

    return_str = ("Adobe-Net-GeneratorEncoderDecoder")

    return generated_img, encoded_content_final, encoded_style_final, return_str, \
           style_batch_diff, content_batch_diff, \
           content_full_feature_list, style_full_feature_list, decoder_full_feature_list



