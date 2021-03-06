import pandas as pd  
import tensorflow as tf
import itertools
import random
import csv
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import OneHotEncoder

INPUT_NODE = 1390
OUTPUT_NODE = 24

LAYER1_NODE = 50
BATCH_SIZE = 100

LEARNING_RATE_BASE = 0.8
LEARNING_DECAY_BASE = 0.99
REGULARIZATION_RATE = 0.0001
TRAINING_STEPS = 5000
MOVING_AVERAGE_DECAY = 0.99

globala = 0

df = pd.read_csv("tmp/sample.csv", header=None)
print(df.values.size)

compare_str = df.values[:, :2]

total_data = df.values[:, 2:]
total_dict = df.values[:, 2:-24]
total_dict_list = list(itertools.chain.from_iterable(total_dict))
print("step0 finish")
le = LabelEncoder()
le.fit(total_dict_list)
le_total_dict_list = le.transform(total_dict_list)
le_total_dict = np.array(le_total_dict_list).reshape(112978 + 2287,25)
print("step1 finish")
ohe = OneHotEncoder()
ohe.fit(le_total_dict)
ohe_total_data = ohe.transform(le_total_dict).toarray()
# r = np.random.permutation(len(ohe_total_data))
# ohe_total_data = ohe_total_data[r,:]

print("step2 finish")
train_data = ohe_total_data[:112978, :]
print(train_data)
train_label = total_data[:112978, -24:]
valid_data = ohe_total_data[112978:113178, :]
valid_label = total_data[112978:113178, -24:]
# test_data = ohe_total_data[113978:, :]
# test_label = total_data[113978:, -24:]
oracle_train_data = ohe_total_data[-2087:-287, :]
oracle_test_data = total_data[-2087:-287, -24:]

test_data = ohe_total_data[-287:, :]
print(test_data)
test_label = total_data[-287:, -24:]

print("step3 finish")
# 先按序 以后再拼接random 获取相同行的随机data和feature
def nextbatch():
	global globala
	global oracle_train_data
	global oracle_test_data
	a = globala % 350
	parta, partb = train_data[a* 300: (a+1) *  300, :], train_label[a* 300: (a+1) *  300, :]
	globala = globala + 1
	return np.row_stack([parta,oracle_train_data]), np.row_stack([partb, oracle_test_data])

	

def check_accuracy():
	df1 = pd.read_csv("tmp/csvFile3.csv", header=None)
	prediction = df1.values
	with tf.Session() as sess:
		k = 0.4
		while k < 1:
			hah = []
			for i in range(prediction.shape[0]):
				# print("=====" + str(i))			
				# a = tf.greater(prediction[i], k);
				# b = tf.cast(a, tf.float32)	
				hah.append(cal_accuray(i+114978,prediction[i],k))
			# print(hah)
			correct_prediction = tf.reduce_mean(tf.cast(hah, tf.float32))
			print(k)
			print(correct_prediction.eval())
			k = k + 0.1

def cal_accuray(i, prediction, threshold):
	originString = compare_str[i][0]
	# print(originString)
	correctString = compare_str[i][1]
	# print(correctString)
	offset = 0
	j = 0
	for i in range(len(prediction)):
		j = i + offset
		if(prediction[i] <= threshold):
			continue
		else:
			originString = originString[:j+1] + '-' + originString[j+1:]
			offset = offset + 1		
	if threshold==0.4 and originString != correctString:
	# if originString == correctString:
		print(originString+"== == =="+correctString)
	return (originString == correctString)

def inference(input_tensor, avg_class, reuse = False): 
	with tf.variable_scope('layer1', reuse=reuse):
		weights = tf.get_variable("weights", [INPUT_NODE, LAYER1_NODE], initializer=tf.truncated_normal_initializer(stddev=0.1))
		biases = tf.get_variable("biases", [LAYER1_NODE], initializer=tf.constant_initializer(0.0))
		if avg_class == None:
			layer1 = tf.nn.relu(tf.matmul(input_tensor, weights) + biases)
		else:
			layer1 = tf.nn.relu(tf.matmul(input_tensor,avg_class.average(weights)) + avg_class.average(biases))

	with tf.variable_scope('layer2', reuse=reuse):
		weights = tf.get_variable("weights", [LAYER1_NODE, OUTPUT_NODE], initializer=tf.truncated_normal_initializer(stddev=0.1))
		biases = tf.get_variable("biases", [OUTPUT_NODE], initializer=tf.constant_initializer(0.0))
		if avg_class == None:
			layer2 = tf.nn.sigmoid(tf.matmul(layer1, weights) + biases)
		else:
			layer2 = tf.nn.sigmoid(tf.matmul(layer1, avg_class.average(weights)) + avg_class.average(biases))
	return layer2
def train():
	x = tf.placeholder(tf.float32, [None, INPUT_NODE], name='x-input')
	y_ = tf.placeholder(tf.int32, [None, OUTPUT_NODE], name='y-input')

	# 生成隐藏层的参数
	with tf.variable_scope("layer1"):
		weights = tf.Variable(tf.truncated_normal([INPUT_NODE, LAYER1_NODE], stddev=0.1))
		biases = tf.Variable(tf.constant(0.1, shape=[LAYER1_NODE]))

	with tf.variable_scope("layer2"):
		weights = tf.Variable(tf.truncated_normal([LAYER1_NODE, OUTPUT_NODE], stddev=0.1))
		biases = tf.Variable(tf.constant(0.1, shape=[OUTPUT_NODE]))

	y = inference(x, None)

	# 每个位置只有两种可能0,1 故是一个softmax 两分类回归问题
	with tf.variable_scope("softmax"):
		weights = tf.get_variable("weight", [OUTPUT_NODE, 2])
		bias = tf.get_variable("bias", [2])
		y = tf.matmul(y, weights) + bias

	global_step = tf.Variable(0, trainable=False)

	variable_averages = tf.train.ExponentialMovingAverage(MOVING_AVERAGE_DECAY, global_step)

	variable_averages_op = variable_averages.apply(tf.trainable_variables())

	average_y = inference(x, variable_averages, True)

	# cross_entroy = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=y, labels=y_)
	# d_norm = tf.sqrt(tf.reduce_sum(tf.square(y),reduction_indices=[1]))
	# e_norm = tf.sqrt(tf.reduce_sum(tf.square(y_),reduction_indices=[1])) + 1e-10
	# de = tf.reduce_sum(tf.multiply(y,y_),reduction_indices=[1])
	# cosin = de / (d_norm * e_norm)
	# loss = tf.reduce_sum(1-cosin)
	loss = tf.contrib.legacy_seq2seq.sequence_loss_by_example(
		[y], [tf.reshape(y_, [-1])],
		[tf.ones([2100 * 1390], dtype=tf.float32)])
	cost = tf.reduce_sum(loss) / 2100
	# cross_entropy = -tf.reduce_mean(y_ * tf.log(tf.clip_by_value(y, 1e-10, 1.0)))
	# loss = tf.reduce_sum(tf.square(y - y_),
 #                     reduction_indices=[0,1])
	# cross_entroy_mean = tf.reduce_mean(cross_entropy)

	regularizer = tf.contrib.layers.l2_regularizer(REGULARIZATION_RATE)
	weights1 = tf.get_variable("layer1", [INPUT_NODE, LAYER1_NODE])
	weights2 = tf.get_variable("layer2", [LAYER1_NODE, OUTPUT_NODE])
	regularization = regularizer(weights1) + regularizer(weights2)
	# loss = 0
	# loss = loss + regularization

	learning_rate = 0.005

	train_step = tf.train.GradientDescentOptimizer(learning_rate).minimize(cost, global_step=global_step)

	with tf.control_dependencies([train_step, variable_averages_op]):
		train_op = tf.no_op(name='train')
	
	# correct_prediction = tf.reduce_all(tf.equal(prediction_2, y_),1)
	#应该实现按行比较 一行完全相同则为true
	# accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
	# correct_prediction = tf.equal(tf.argmax(average_y,1), tf.argmax(y_, 1))

	# accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

	with tf.Session() as sess:
		tf.initialize_all_variables().run()
		validate_feed = {x: valid_data, y_: valid_label}
		test_feed = {x: test_data, y_: test_label}
		for i in range(TRAINING_STEPS):
			print(i)
			if i % 50 == 0:
				myloss = sess.run(loss, feed_dict = validate_feed)
				print("After %d training steps, loss using average model is %g" % (i, myloss))
				# validate_acc = sess.run(accuracy, feed_dict=validate_feed)
				# print("After %d training steps, validation accuracy using average model is %g" % (i, validate_acc))
			xs, ys = nextbatch()
			# xs, ys = train_data, train_label
			sess.run(train_op, feed_dict={x: xs, y_: ys})
		# test_acc = sess.run(accuracy, feed_dict=test_feed)
		# print("After %d training steps, test accuracy on average model is %g" % (i, test_acc))
		myprediction = sess.run(y, feed_dict=test_feed)
		# myprediction = sess.run(y, feed_dict={x: train_data, y_:train_label})
		csvFile3 = open('tmp/csvFile3.csv','w', newline='') # 设置newline，否则两行之间会空一行
		writer = csv.writer(csvFile3)
		writer.writerows(myprediction)

def main(argv=None):
	# mnist = input_data.read_data_sets("/Users/lijiechu/MNIST_data/", one_hot = True)
	train()
	# check_accuracy()

if __name__ == '__main__':
	tf.app.run()
