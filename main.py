# coding: utf-8

import os

import tensorflow as tf
from tensorflow.python.keras.preprocessing.image import ImageDataGenerator
from tensorflow.python.keras.callbacks import ReduceLROnPlateau, EarlyStopping, TensorBoard
from tensorflow.python.keras.utils import plot_model
import numpy as np

from alexnet import alexnet


flags = tf.flags
flags.DEFINE_string('phase',       'train',  "train or test")
flags.DEFINE_string('data_dir',    'data',   "Data directory")
flags.DEFINE_string('model_dir',   'models', "Directory to output the result")
flags.DEFINE_integer('epoch',      200,      "Number of epochs")
flags.DEFINE_integer('batch_size', 32,       "Number of batch size")
FLAGS = flags.FLAGS


def main(_):
    # input image dimensions
    img_rows, img_cols = 400, 400
    # Images are RGB.
    img_channels = 1

    # channel last -> (~/.keras/keras.json)
    model = alexnet((img_rows, img_cols, img_channels), 5)  # Binary classification
    # plot_model(model, to_file='model.png', show_shapes=True)
    model.compile(loss='categorical_crossentropy',  # when multiclass classification, loss is categorical_crossentropy
                  optimizer='adam',
                  metrics=['accuracy'])

    callbacks = list()
    callbacks.append(ReduceLROnPlateau(factor=np.sqrt(0.1), cooldown=0, patience=5, min_lr=0.5e-6))
    callbacks.append(EarlyStopping(min_delta=0.001, patience=10))
    callbacks.append(TensorBoard(histogram_freq=0,
                                 write_graph=False,
                                 write_grads=True,
                                 write_images=True,
                                 batch_size=FLAGS.batch_size))

    print('Using real-time data augmentation.')
    # This will do preprocessing and realtime data augmentation:
    train_datagen = ImageDataGenerator(
        featurewise_center=False,  # set input mean to 0 over the dataset
        samplewise_center=False,  # set each sample mean to 0
        featurewise_std_normalization=False,  # divide inputs by std of the dataset
        samplewise_std_normalization=False,  # divide each input by its std
        zca_whitening=False,  # apply ZCA whitening
        rotation_range=180,  # randomly rotate images in the range (degrees, 0 to 180)
        width_shift_range=0.1,  # randomly shift images horizontally (fraction of total width)
        height_shift_range=0.1,  # randomly shift images vertically (fraction of total height)
        horizontal_flip=True,  # randomly flip images
        vertical_flip=True,  # randomly flip images
        validation_split=0.2)

    # Compute quantities required for featurewise normalization
    # (std, mean, and principal components if ZCA whitening is applied).
    train_data_dir = "../multiclass-25k-binarize"
    train_generator = train_datagen.flow_from_directory(
        train_data_dir,
        target_size=(img_rows, img_cols),
        color_mode='grayscale',
        class_mode='categorical',
        batch_size=FLAGS.batch_size,
        subset='training')
    validation_generator = train_datagen.flow_from_directory(
        train_data_dir,
        target_size=(img_rows, img_cols),
        color_mode='grayscale',
        class_mode='categorical',
        batch_size=FLAGS.batch_size,
        subset='validation')

    # Fit the model on the batches generated by datagen.flow().
    steps_per_epoch = train_generator.n // FLAGS.batch_size
    validation_steps = validation_generator.n // FLAGS.batch_size
    model.fit_generator(train_generator,
                        steps_per_epoch=steps_per_epoch,
                        validation_data=validation_generator,
                        validation_steps=validation_steps,
                        epochs=FLAGS.epoch, verbose=1,
                        callbacks=callbacks)

    # cf. https://medium.com/@vijayabhaskar96/
    # tutorial-image-classification-with-keras-flow-from-directory-and-generators-95f75ebe5720
    test_generator = train_datagen.flow_from_directory(
        "../pipe-screenshot-test-binarize",
        target_size=(img_rows, img_cols),
        color_mode='grayscale',
        class_mode=None,
        batch_size=1,
        shuffle=False)
    # Need to reset the test_generator before
    #  whenever you call the predict_generator.
    # This is important, if you forget to reset
    #  the test_generator you will get outputs in a weird order.
    test_generator.reset()
    pred = model.predict_generator(test_generator, verbose=1)
    predicted_class_indices = np.argmax(pred, axis=1)

    # Now predicted_class_indices has the predicted labels,
    #  but you can’t simply tell what the predictions are,
    #   because all you can see is numbers like 0,1,4,1,0,6…
    # and most importantly you need to map the predicted
    #  labels with their unique ids such as filenames to
    #   find out what you predicted for which image.
    labels = train_generator.class_indices
    labels = dict((v, k) for k, v in labels.items())
    predictions = [labels[k] for k in predicted_class_indices]
    filenames = test_generator.filenames
    print("filenames:", filenames)
    print("predictions:", predictions)

    try:
        os.makedirs(FLAGS.model_dir)
    except:
        pass
    model.save(os.path.join(FLAGS.model_dir, str(FLAGS.epoch) + '.h5'))


if __name__ == '__main__':
    tf.app.run()
