import tensorflow as tf
import tensorflow.contrib.slim as slim
import argparse
import os
import sys
from posenet import Posenet
from image_reader import ImageReader
import numpy as np
import math

def l2_distance(x, y):
	if type(x) is not np.ndarray:
		x = np.asarray(x)
	if type(y) is not np.ndarray:
		y = np.asarray(y)
	return np.linalg.norm(x-y)

def quaternion_distance(q1, q2):
	"""Returns an angle that rotates q1 into q2"""
	if type(q1) is not np.ndarray:
		q1 = np.asarray(q1)
	if type(q2) is not np.ndarray:
		q2 = np.asarray(q2)
	cos = 2*(q1.dot(q2))**2 - 1
	cos = max(min(cos, 1), -1) # To combat numerical imprecisions
	return math.acos(cos)


parser = argparse.ArgumentParser()
parser.add_argument('--model', action='store', required=True)
parser.add_argument('--dataset', action='store', required=True)
parser.add_argument('--save_output', action='store')
args = parser.parse_args()

if not os.path.isfile(args.model) or os.path.isdir(args.model):
	print '{} does not exist or is a directory'.format(args.model)
	sys.exit()

if not os.path.isfile(args.dataset) or os.path.isdir(args.dataset):
	print '{} does not exist or is a directory'.format(args.dataset)
	sys.exit()

n_input = 224
test_reader = ImageReader(args.dataset, 1, [n_input, n_input], False, False)

# tf Graph input
x = tf.placeholder(tf.float32, [None, n_input, n_input, 3], name="InputData")

# Define the network
poseNet = Posenet()
output = poseNet.create_testable(x)

saver = tf.train.Saver()
init = tf.initialize_all_variables()

if args.save_output:
	f = open(args.save_output, 'w')
	f.write('Prediction for {}\n'.format(args.dataset))
	f.write('ImageFile, Predicted Camera Position [X Y Z W P Q R]\n\n')

with tf.Session() as sess:
	sess.run(init)

	# Load the model
	saver.restore(sess, os.path.abspath(args.model))

	n_images = test_reader.total_images()
	angle = 0
	distance = 0
	for i in range(n_images):
		images_feed, labels_feed = test_reader.next_batch()
		predicted = sess.run([output], feed_dict={x: images_feed})
		predicted = [round(v, 6) for v in predicted[0]['x'][0].tolist() + predicted[0]['q'][0].tolist()]
		gt = labels_feed[0]
		print "----{}----".format(i)
		print "Predicted: ", predicted
		print "Correct:   ", gt
		dx = l2_distance(gt[0:3], predicted[0:3])
		dq = quaternion_distance(gt[3:7], predicted[3:7])*180/math.pi
		distance += dx
		angle += dq
		print('Distance error: {}'.format(dx))
		print('Angle error:    {}'.format(dq))
		if args.save_output:
			x1, x2, x3 = predicted[0:3]
			q1, q2, q3, q4 = predicted[3:7]
			f.write('{0} {1:.6f} {2:.6f} {3:.6f} {4:.6f} {5:.6f} {6:.6f} {7:.6f}\n'.format(test_reader.images[i], x1, x2, x3, q1, q2, q3, q4))
	angle /= n_images
	distance /= n_images
	print('\n-----------SUMMARY------------')
	print('Distance error: {}'.format(distance))
	print('Angle error:    {}'.format(angle))

if args.save_output:
	f.close()