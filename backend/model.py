"""
Small transformer text classifier, trained fully from scratch.

Sized to fit comfortably on a 6-8GB laptop GPU (RTX 3050/3060 class):
- embedding dim 256, 4 layers, 4 heads -> a few million parameters,
  compared to BERT-base's 110M+ pretrained parameters.

Use this same architecture for BOTH the fake-news classifier and the
AI-generated-text classifier -- just point train_text_classifier.py at
a different CSV and a different --run-name.
"""

import math
import torch
import torch.nn as nn


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 512):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return x + self.pe[:, : x.size(1)]


class ScratchTransformerClassifier(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        num_classes: int = 2,
        d_model: int = 256,
        nhead: int = 4,
        num_layers: int = 4,
        dim_feedforward: int = 512,
        max_len: int = 256,
        dropout: float = 0.1,
        pad_idx: int = 0,
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model, padding_idx=pad_idx)
        self.pos_encoding = PositionalEncoding(d_model, max_len=max_len)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(d_model, num_classes)
        self.pad_idx = pad_idx

    def forward(self, input_ids: torch.Tensor):
        # input_ids: (batch, seq_len)
        pad_mask = input_ids == self.pad_idx  # True where padded

        x = self.embedding(input_ids)
        x = self.pos_encoding(x)
        x = self.encoder(x, src_key_padding_mask=pad_mask)

        # mean-pool over non-padded tokens
        mask = (~pad_mask).unsqueeze(-1).float()
        summed = (x * mask).sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1e-6)
        pooled = summed / counts

        pooled = self.dropout(pooled)
        logits = self.classifier(pooled)
        return logits

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
