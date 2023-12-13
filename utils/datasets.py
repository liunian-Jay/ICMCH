import os
import random
import sys
import h5py
import numpy as np
import scipy.io as sio
from scipy import sparse
from utils import util
import math


def load_data(config, train_dir=False):
    data_name = config['dataset']
    X_list = []
    Y_list = []
    main_dir = sys.path[0]
    if train_dir:
        main_dir = os.path.join(main_dir, '../')

    if data_name in ['Scene-15']:
        mat = sio.loadmat(os.path.join(main_dir, 'data', 'Scene-15.mat'))
        X = mat['X'][0]
        X_list.append(X[2].astype('float32'))  # 40
        X_list.append(X[1].astype('float32'))  # 59
        Y_list.append(np.squeeze(mat['Y']))
        Y_list.append(np.squeeze(mat['Y']))
    elif data_name in ['LandUse-21']:
        mat = sio.loadmat(os.path.join(main_dir, 'data', 'LandUse-21.mat'))
        train_x = []
        train_x.append(sparse.csr_matrix(mat['X'][0, 0]).A)  # 20
        train_x.append(sparse.csr_matrix(mat['X'][0, 1]).A)  # 59
        train_x.append(sparse.csr_matrix(mat['X'][0, 2]).A)  # 40
        index = random.sample(range(train_x[0].shape[0]), 2100)  # 30000
        for view in [1, 2]:
            x = train_x[view][index].astype('float32')
            y = np.squeeze(mat['Y']).astype('int')[index]
            X_list.append(x)
            Y_list.append(y)
    elif data_name in ['handwritten']:
        mat = sio.loadmat(os.path.join(main_dir, 'data', data_name + '.mat'))
        X = mat['X'][0]
        for view in [1, 4]:
            X_list.append(X[view].astype('float32'))
            Y_list.append(np.squeeze(mat['truth']))
    elif data_name in ['MSRC_v1']:
        mat = sio.loadmat(os.path.join(main_dir, 'data', data_name + '.mat'))
        for view in ['msr2', 'msr3']:
            X_list.append(mat[view].astype('float32'))
            Y_list.append(np.squeeze(mat['truth']))
    elif data_name in ['NoisyMNIST']:
        data = sio.loadmat(os.path.join(main_dir, 'data', data_name + '.mat'))
        # train = DataSet_NoisyMNIST(data['X1'], data['X2'], data['trainLabel'])
        tune = DataSet_NoisyMNIST(data['XV1'], data['XV2'], data['tuneLabel'])
        test = DataSet_NoisyMNIST(data['XTe1'], data['XTe2'], data['testLabel'])
        X_list.append(np.concatenate([tune.images1, test.images1], axis=0))
        X_list.append(np.concatenate([tune.images2, test.images2], axis=0))
        Y_list.append(np.concatenate([np.squeeze(tune.labels[:, 0]), np.squeeze(test.labels[:, 0])]))
        Y_list.append(np.concatenate([np.squeeze(tune.labels[:, 0]), np.squeeze(test.labels[:, 0])]))
    else:
        raise Exception('Undefined data_name')
    return X_list, Y_list


def next_batch(X1, X2, batch_size):
    # generate next batch, just two views
    tot = X1.shape[0]
    total = math.ceil(tot / batch_size) - 1  # fix the last batch
    if tot % batch_size == 0:
        total += 1

    for i in range(int(total)):
        start_idx = i * batch_size
        end_idx = (i + 1) * batch_size
        end_idx = min(tot, end_idx)
        batch_x1 = X1[start_idx: end_idx, ...]
        batch_x2 = X2[start_idx: end_idx, ...]
        yield batch_x1, batch_x2, (i + 1)


def next_batch_gt(X1, X2, gt, batch_size):
    # generate next batch with label
    tot = X1.shape[0]
    total = math.ceil(tot / batch_size) - 1  # fix the last batch
    for i in range(int(total) - 1):
        start_idx = i * batch_size
        end_idx = (i + 1) * batch_size
        end_idx = min(tot, end_idx)
        batch_x1 = X1[start_idx: end_idx, ...]
        batch_x2 = X2[start_idx: end_idx, ...]
        gt_now = gt[start_idx: end_idx, ...]
        yield batch_x1, batch_x2, gt_now, (i + 1)


def next_batch_list(X, batch_size):
    # generate next batch list and X is a list
    tot = X[0].shape[0]
    total = math.ceil(tot / batch_size) - 1  # fix the last batch
    for i in range(int(total)):
        start_idx = i * batch_size
        end_idx = (i + 1) * batch_size
        end_idx = min(tot, end_idx)
        batch_x_list = []
        for k in X.shape[0]:
            batch_x = X[k][start_idx: end_idx, ...]
            batch_x_list.append(batch_x)
        yield batch_x_list, (i + 1)


class DataSet_NoisyMNIST(object):

    def __init__(self, images1, images2, labels, fake_data=False, one_hot=False, dtype=np.float32):
        """Construct a DataSet.
        one_hot arg is used only if fake_data is true.  `dtype` can be either
        `uint8` to leave the input as `[0, 255]`, or `float32` to rescale into `[0, 1]`.
        """
        t = 2
        if dtype not in (np.uint8, np.float32):
            raise TypeError('Invalid image dtype %r, expected uint8 or float32' % dtype)
        if fake_data:
            self._num_examples = 10000
            self.one_hot = one_hot
        else:
            assert images1.shape[0] == labels.shape[0], (
                    'images1.shape: %s labels.shape: %s' % (images1.shape, labels.shape))
            assert images2.shape[0] == labels.shape[0], (
                    'images2.shape: %s labels.shape: %s' % (images2.shape, labels.shape))
            self._num_examples = images1.shape[0] // t

            if dtype == np.float32 and images1.dtype != np.float32:
                # Convert from [0, 255] -> [0.0, 1.0].
                # print("type conversion view 1")
                images1 = images1.astype(np.float32)

            if dtype == np.float32 and images2.dtype != np.float32:
                # print("type conversion view 2")
                images2 = images2.astype(np.float32)

        self._images1 = images1[::t]
        self._images2 = images2[::t]
        self._labels = labels[::t]
        self._epochs_completed = 0
        self._index_in_epoch = 0

    @property
    def images1(self):
        return self._images1

    @property
    def images2(self):
        return self._images2

    @property
    def labels(self):
        return self._labels

    @property
    def num_examples(self):
        return self._num_examples

    @property
    def epochs_completed(self):
        return self._epochs_completed

    def next_batch(self, batch_size, fake_data=False):
        """Return the next `batch_size` examples from this data set."""
        if fake_data:
            fake_image = [1] * 784
            if self.one_hot:
                fake_label = [1] + [0] * 9
            else:
                fake_label = 0
            return [fake_image for _ in range(batch_size)], [fake_image for _ in range(batch_size)], [fake_label for _
                                                                                                      in range(
                    batch_size)]

        start = self._index_in_epoch
        self._index_in_epoch += batch_size
        if self._index_in_epoch > self._num_examples:
            # Finished epoch
            self._epochs_completed += 1
            # Shuffle the data
            perm = np.arange(self._num_examples)
            np.random.shuffle(perm)
            self._images1 = self._images1[perm]
            self._images2 = self._images2[perm]
            self._labels = self._labels[perm]
            # Start next epoch
            start = 0
            self._index_in_epoch = batch_size
            assert batch_size <= self._num_examples

        end = self._index_in_epoch
        return self._images1[start:end], self._images2[start:end], self._labels[start:end]
