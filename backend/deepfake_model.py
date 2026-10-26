"""
Small CNN for deepfake face classification, trained fully from scratch
(no pretrained ImageNet weights, no pretrained backbone like ResNet/Xception).

Sized to fit comfortably on a 6GB laptop GPU (RTX 3050 class) at 128x128
input resolution and batch size 32 — a few million parameters, compared
to Xception's 20M+ pretrained parameters.

Use this same architecture for BOTH the deepfake classifier and the
AI-image classifier (Module 11) later — just point train_deepfake_classifier.py
at a different manifest CSV and a different --run-name.
"""

import torch
import torch.nn as nn


class ConvBlock(nn.Module):
    """Conv -> BatchNorm -> ReLU -> MaxPool, one building block of the CNN."""

    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
        )

    def forward(self, x):
        return self.block(x)


class ScratchCNNClassifier(nn.Module):
    def __init__(self, num_classes: int = 2, in_channels: int = 3, dropout: float = 0.3):
        super().__init__()

        # Input: 128x128 -> after 5 pooling stages -> 4x4
        self.features = nn.Sequential(
            ConvBlock(in_channels, 32),   # 128 -> 64
            ConvBlock(32, 64),            # 64 -> 32
            ConvBlock(64, 128),           # 32 -> 16
            ConvBlock(128, 256),          # 16 -> 8
            ConvBlock(256, 256),          # 8 -> 4
        )

        self.global_pool = nn.AdaptiveAvgPool2d(1)  # 4x4 -> 1x1, robust to slight input-size variation
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(256, num_classes)

    def forward(self, x: torch.Tensor):
        x = self.features(x)
        x = self.global_pool(x)
        x = torch.flatten(x, 1)
        x = self.dropout(x)
        return self.classifier(x)

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
