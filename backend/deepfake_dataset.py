"""
Dataset loader for the deepfake (and, later, AI-image) CNN.

Expects a manifest CSV with columns: image_path,label
(produced by prepare_deepfake_manifest.py)
"""

import pandas as pd
from PIL import Image
import torchvision.transforms as T
from torch.utils.data import Dataset

IMG_SIZE = 128  # must match what the CNN and training script use


def build_transforms(train: bool):
    """
    Basic preprocessing + light augmentation for the training split only.
    Augmentation helps a small from-scratch CNN generalize better on a
    modest-sized dataset — validation/test data is NOT augmented, since
    we want a clean, honest measure of real performance.
    """
    if train:
        return T.Compose([
            T.Resize((IMG_SIZE, IMG_SIZE)),
            T.RandomHorizontalFlip(p=0.5),
            T.ColorJitter(brightness=0.15, contrast=0.15),
            T.ToTensor(),
            T.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
        ])
    else:
        return T.Compose([
            T.Resize((IMG_SIZE, IMG_SIZE)),
            T.ToTensor(),
            T.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
        ])


class DeepfakeImageDataset(Dataset):
    def __init__(self, df: pd.DataFrame, train: bool):
        self.paths = df["image_path"].tolist()
        self.labels = df["label"].astype(int).tolist()
        self.transform = build_transforms(train)

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        path = self.paths[idx]
        try:
            image = Image.open(path).convert("RGB")
        except (FileNotFoundError, OSError) as e:
            raise RuntimeError(
                f"Could not load image at {path}. Check that the manifest CSV "
                f"paths are correct relative to where you're running the "
                f"training script from."
            ) from e

        image = self.transform(image)
        return image, self.labels[idx]
