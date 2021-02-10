from __future__ import absolute_import, division, print_function, unicode_literals

import matplotlib.pylab as plt
import tensorflow_hub as hub

# from tensorflow.keras import layers
import tensorflow as tf
import numpy as np
import PIL.Image as Image

# tf.enable_eager_execution()
tf.compat.v1.enable_eager_execution()


print("1:分類器をダウンロードする")
classifier_url ="https://tfhub.dev/google/tf2-preview/mobilenet_v2/classification/2" #@param {type:"string"}

IMAGE_SHAPE = (224, 224)

classifier = tf.keras.Sequential([
    hub.KerasLayer(classifier_url, input_shape=IMAGE_SHAPE+(3,))
])

print("2:モデルを試すために単一の画像をダウンロード")

grace_hopper = tf.keras.utils.get_file('image.jpg','https://storage.googleapis.com/download.tensorflow.org/example_images/grace_hopper.jpg')
grace_hopper = Image.open(grace_hopper).resize(IMAGE_SHAPE)
grace_hopper

print("3")
grace_hopper = np.array(grace_hopper)/255.0
grace_hopper.shape

print("4:バッチ次元を一つ追加し、画像をモデルに渡し")
result = classifier.predict(grace_hopper[np.newaxis, ...])
result.shape

print("5")
predicted_class = np.argmax(result[0], axis=-1)
predicted_class

print("6:予測されたクラスの ID を ImageNet のラベルと突き合わせて、予測結果をデコード")
labels_path = tf.keras.utils.get_file('ImageNetLabels.txt','https://storage.googleapis.com/download.tensorflow.org/data/ImageNetLabels.txt')
imagenet_labels = np.array(open(labels_path).read().splitlines())

print("7")
plt.imshow(grace_hopper)
plt.axis('off')
predicted_class_name = imagenet_labels[predicted_class]
_ = plt.title("Prediction: " + predicted_class_name.title())

print("8:TensorFlow の花データセットを使用")
data_root = tf.keras.utils.get_file(
  'flower_photos','https://storage.googleapis.com/download.tensorflow.org/example_images/flower_photos.tgz', untar=True)

print("9")
image_generator = tf.keras.preprocessing.image.ImageDataGenerator(rescale=1/255)
image_data = image_generator.flow_from_directory(str(data_root), target_size=IMAGE_SHAPE)

print("10")
for image_batch, label_batch in image_data:
  print("Image batch shape: ", image_batch.shape)
  print("Label batch shape: ", label_batch.shape)
  break

print("11")
result_batch = classifier.predict(image_batch)
var = result_batch.shape

print("12")
predicted_class_names = imagenet_labels[np.argmax(result_batch, axis=-1)]
predicted_class_names

print("13")
plt.figure(figsize=(10,9))
plt.subplots_adjust(hspace=0.5)
for n in range(30):
  plt.subplot(6,5,n+1)
  plt.imshow(image_batch[n])
  plt.title(predicted_class_names[n])
  plt.axis('off')
_ = plt.suptitle("ImageNet predictions")
