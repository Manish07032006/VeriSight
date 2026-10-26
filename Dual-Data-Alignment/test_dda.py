import sys
from pathlib import Path

import torch
from PIL import Image, ImageOps
from torchvision import transforms

PROJECT_DIR = Path(__file__).resolve().parent
INFERENCE_DIR = PROJECT_DIR / "Inference"
CHECKPOINT_PATH = PROJECT_DIR / "pretrained" / "DDA_ckpt.pth"

sys.path.insert(0, str(INFERENCE_DIR))

from models.dinov2_models_lora import DINOv2ModelWithLoRA


def main():
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable.")

    if not CHECKPOINT_PATH.exists():
        raise FileNotFoundError(
            f"DDA checkpoint not found: {CHECKPOINT_PATH}"
        )

    if len(sys.argv) < 2:
        print('Usage: python test_dda.py "D:\\path\\to\\image.jpg"')
        return

    image_path = Path(sys.argv[1])

    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    device = torch.device("cuda:0")

    print("GPU:", torch.cuda.get_device_name(0))

    free_memory, total_memory = torch.cuda.mem_get_info()
    print(f"Free VRAM: {free_memory / 1024**3:.2f} GiB")
    print(f"Total VRAM: {total_memory / 1024**3:.2f} GiB")

    print("\nLoading DINOv2 ViT-L/14 and DDA...")

    model = DINOv2ModelWithLoRA(
        name="dinov2_vitl14",
        lora_rank=8,
        lora_alpha=1,
        lora_targets=None,
    )

    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location="cpu",
        weights_only=True,
    )

    model.load_state_dict(checkpoint["model"], strict=True)
    del checkpoint

    model = model.to(device)
    model.eval()

    print("DDA checkpoint loaded successfully.")

    transform = transforms.Compose([
        transforms.CenterCrop(336),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.48145466, 0.4578275, 0.40821073],
            std=[0.26862954, 0.26130258, 0.27577711],
        ),
    ])

    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")

    image_tensor = transform(image).unsqueeze(0).to(device)

    print("Image:", image_path)
    print("Input shape:", tuple(image_tensor.shape))
    print("\nRunning inference...")

    with torch.inference_mode():
        output = model(image_tensor).sigmoid().flatten()

    score = output.item()

    print("\n--- DDA Test Result ---")
    print(f"Raw sigmoid score: {score:.6f}")
    print(f"Score as percentage: {score * 100:.2f}%")
    print("Inference completed successfully.")

    print(
        "\nNOTE: This score is not necessarily a calibrated probability. "
        "Verify the official label mapping and threshold before "
        "classifying the image as REAL or AI-GENERATED."
    )


if __name__ == "__main__":
    main()