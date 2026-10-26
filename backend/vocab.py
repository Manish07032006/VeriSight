"""
Simple from-scratch vocabulary and tokenizer.

This intentionally avoids any pretrained tokenizer (like BERT's WordPiece)
so that the embedding layer trained on top of it is genuinely learned
from scratch on your own dataset, not inherited from a pretrained model.
"""

import re
import json
from collections import Counter

PAD_TOKEN = "<pad>"
UNK_TOKEN = "<unk>"


def simple_tokenize(text: str):
    """Lowercase + basic word tokenization. No external tokenizer library."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    tokens = text.split()
    return tokens


class Vocab:
    def __init__(self, min_freq: int = 2, max_size: int = 30000):
        self.min_freq = min_freq
        self.max_size = max_size
        self.token2idx = {PAD_TOKEN: 0, UNK_TOKEN: 1}
        self.idx2token = {0: PAD_TOKEN, 1: UNK_TOKEN}

    def build(self, texts):
        counter = Counter()
        for text in texts:
            counter.update(simple_tokenize(text))

        most_common = [
            tok for tok, freq in counter.most_common(self.max_size)
            if freq >= self.min_freq
        ]

        for tok in most_common:
            if tok not in self.token2idx:
                idx = len(self.token2idx)
                self.token2idx[tok] = idx
                self.idx2token[idx] = tok

        print(f"Vocab built: {len(self.token2idx)} tokens "
              f"(from {len(counter)} unique raw tokens)")

    def encode(self, text: str, max_len: int = 256):
        tokens = simple_tokenize(text)[:max_len]
        ids = [self.token2idx.get(tok, self.token2idx[UNK_TOKEN]) for tok in tokens]
        return ids

    def __len__(self):
        return len(self.token2idx)

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.token2idx, f)

    def load(self, path: str):
        with open(path) as f:
            self.token2idx = json.load(f)
        self.idx2token = {int(v): k for k, v in self.token2idx.items()}
        return self
