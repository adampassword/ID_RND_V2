import glob
import os
import sys
import numpy as np
import cv2
import torch
from albumentations import (
    RandomRotate90,
    Flip, OneOf, Compose
)
from torch.utils.data import Dataset
import matplotlib.pyplot as plt
from utils.face_detection.face_detection import get_face

sys.path.append('..')


class IDRND_dataset(Dataset):
    def __init__(self, path='../data', mode='train', add_idrnd_v1_dataset=False, use_face_detection=False):
        self.path_to_data = path
        self.mode = mode
        self.use_face_detection = use_face_detection
        self.masks = glob.glob(os.path.join(self.path_to_data, mode, '2dmask/*/*.png'))
        self.printed = glob.glob(os.path.join(self.path_to_data, mode, 'printed/*/*.png'))
        self.replay = glob.glob(os.path.join(self.path_to_data, mode, 'replay/*/*.png'))
        self.real = glob.glob(os.path.join(self.path_to_data, mode, 'real/*/*.png'))

        self.aug = self.get_aug()
        self.images = self.masks + self.printed + self.replay + self.real
        self.labels = [1] * len(self.masks + self.printed + self.replay) + [0] * len(self.real)

        if add_idrnd_v1_dataset:
            self.idrnd_v1_images = glob.glob("../data/idrnd_v1/*/*.png")
            self.idrnd_v1_labels = [0 if 'real' in i else 0 for i in self.idrnd_v1_images]

            self.images += self.idrnd_v1_images
            self.labels += self.idrnd_v1_labels

        self.images = np.asarray(self.images)
        self.labels = np.asarray(self.labels)

        self.count_data()

    def count_data(self):
        print(f'Mask images - {len(self.masks)}\n' +
              f'Printed images - {len(self.printed)}\n' +
              f'Replay images - {len(self.replay)}\n' +
              f'Real images - {len(self.real)}')

        print(f'Spoof images - {self.labels.sum()}\n' +
              f'Real images - {self.__len__() - self.labels.sum()}')

    @staticmethod
    def get_aug(p=.9):
        return Compose([
            OneOf([
                # RandomRotate90(),
                Flip()
            ]),
            # OneOf([
            #     IAAAdditiveGaussianNoise(),
            #     GaussNoise(),
            # ], p = 0.0),
            # OneOf([
            #     MotionBlur(p = .2),
            #     MedianBlur(blur_limit = 3, p = 0.1),
            #     Blur(blur_limit = 3, p = 0.0),
            # ], p = 0.1),
            # ShiftScaleRotate(shift_limit = 0.0625, scale_limit = 0.1, rotate_limit = 45, p = 0.0),
            # OneOf([
            #     OpticalDistortion(p = 0.1),
            #     GridDistortion(p = .1),
            #     IAAPiecewiseAffine(p = 0.3),
            # ], p = 0.0),
            # OneOf([
            #     CLAHE(clip_limit = 2),
            #     IAASharpen(),
            #     IAAEmboss(),
            #     RandomBrightnessContrast(),
            # ], p = 0.0)
        ], p=p)

    def __len__(self):
        return self.labels.shape[0]

    def __getitem__(self, idx):
        image = cv2.imread(self.images[idx])
        label = self.labels[idx]

        # if self.use_face_detection:
        #     image = get_face(image)

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        image = cv2.resize(image, (224, 224))
        image = self.aug(image=image)['image'] / 255.
        image = np.moveaxis(image, -1, 0)
        return {"image": torch.tensor(image, dtype=torch.float), "label": torch.tensor(label, dtype=torch.float)}


class TestAntispoofDataset(Dataset):
    def __init__(self, paths, use_face_detection=False):
        self.paths = paths
        self.use_face_detection = use_face_detection

    def __getitem__(self, index):
        image_info = self.paths[index]
        img = cv2.imread(image_info['path'])

        if self.use_face_detection:
            img = get_face(img)

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (224, 224)) / 255.
        img = np.moveaxis(img, -1, 0)
        return image_info['id'], image_info['frame'], torch.tensor(img, dtype=torch.float)

    def __len__(self):
        return len(self.paths)


def make_weights_for_balanced_classes(dataset: Dataset):
    weight_per_class = dict()
    N = dataset.__len__()
    for i in range(len(np.unique(dataset.labels))):
        cnt_element_in_class = len([j for j in dataset.labels if i == j])
        weight_per_class[i] = cnt_element_in_class / N

    weight = list(map(lambda x: weight_per_class[x], dataset.labels))
    return weight


class IDRND_3D_dataset(Dataset):
    def __init__(self, path='../data', mode='train', use_face_detection=False):
        self.path_to_data = os.path.join(path, mode)
        self.mode = mode
        self.use_face_detection = use_face_detection
        self.masks = glob.glob(os.path.join(self.path_to_data, '2dmask/*'))
        self.printed = glob.glob(os.path.join(self.path_to_data, 'printed/*'))
        self.replay = glob.glob(os.path.join(self.path_to_data, 'replay/*'))
        self.real = glob.glob(os.path.join(self.path_to_data, 'real/*'))

        self.aug = self.get_aug()
        self.users = self.masks + self.printed + self.replay + self.real
        self.labels = [1] * len(self.masks + self.printed + self.replay) + [0] * len(self.real)

        self.users = np.asarray(self.users)
        self.labels = np.asarray(self.labels)

        self.count_data()

    def count_data(self):
        print(f'Mask images - {len(self.masks)}\n' +
              f'Printed images - {len(self.printed)}\n' +
              f'Replay images - {len(self.replay)}\n' +
              f'Real images - {len(self.real)}')

        print(f'Spoof images - {self.labels.sum()}\n' +
              f'Real images - {self.__len__() - self.labels.sum()}')

    @staticmethod
    def get_aug(p=.9):
        return Compose([
            OneOf([
                # RandomRotate90(),
                Flip()
            ]),
        ], p=p)

    def __len__(self):
        return self.labels.shape[0]

    def __getitem__(self, idx):
        out_image = np.zeros((5, 3, 224, 224), dtype=np.float)  # 5-images; 3-channels; 720-width;720-height;
        images = glob.glob(os.path.join(self.users[idx], '*.png'))
        for i, image_path in enumerate(images):
            im = cv2.imread(image_path)
            im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            im = cv2.resize(im, (224, 224)) / 255.
            im = np.moveaxis(im, -1, 0)
            out_image[i] = im

        out_image = np.moveaxis(out_image, 0, 1)
        label = self.labels[idx]
        # if self.use_face_detection:
        #     image = get_face(image)

        return {"image": torch.tensor(out_image, dtype=torch.float), "label": torch.tensor(label, dtype=torch.float)}


if __name__ == '__main__':
    dataset = IDRND_dataset(mode='val')
    batch = dataset.__getitem__(1)

    dataset = IDRND_3D_dataset(mode='val')
    batch = dataset.__getitem__(1)

    i = batch['image']
    i = i.numpy()
    i = i[4]
    i = np.moveaxis(i, 0, -1)
    plt.imshow(i)
    plt.show()
