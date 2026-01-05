import argparse
import cv2
import os
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from dataloader import ToTensor, Normalize
from model import EventDetector
import numpy as np
import torch.nn.functional as F
from pathlib import Path

EVENT_NAMES_8 = {
    0: 'Address',
    1: 'Toe-up',
    2: 'Mid-backswing (arm parallel)',
    3: 'Top',
    4: 'Mid-downswing (arm parallel)',
    5: 'Impact',
    6: 'Mid-follow-through (shaft parallel)',
    7: 'Finish',
}

# 你的CSV里9个关键帧列（9事件）
EVENT_NAMES_9 = {
    0: '脚尖抬起',
    1: '起摆动作',
    2: '上杆',
    3: '顶点',
    4: '上下转换',
    5: '击球前',
    6: '击球瞬间',
    7: '送杆',
    8: '随势挥杆',
}


def _torch_load(path, map_location=None):
    # PyTorch新版本建议weights_only=True；旧版本不支持该参数，所以做兼容。
    try:
        return torch.load(path, map_location=map_location, weights_only=True)
    except TypeError:
        return torch.load(path, map_location=map_location)


def decode_events_independent(probs: np.ndarray, num_events: int) -> np.ndarray:
    """Pick each event frame independently: argmax_t P(class=i|t)."""
    return np.asarray([int(np.argmax(probs[:, i])) for i in range(num_events)], dtype=np.int32)


def decode_events_ordered(probs: np.ndarray, num_events: int, eps: float = 1e-9) -> np.ndarray:
    """Decode event frames with an ordering constraint.

    Finds frames f_0 <= f_1 <= ... <= f_{E-1} maximizing sum log P(class=i | f_i).
    This avoids "later event happens before earlier event" artifacts.
    """
    logp = np.log(np.clip(probs[:, :num_events], eps, 1.0)).astype(np.float64)
    T = logp.shape[0]
    E = num_events

    dp = np.full((E, T), -1e18, dtype=np.float64)
    ptr = np.full((E, T), -1, dtype=np.int32)

    dp[0, :] = logp[:, 0]
    for e in range(1, E):
        best_val = np.empty(T, dtype=np.float64)
        best_idx = np.empty(T, dtype=np.int32)
        cur_val = -1e18
        cur_idx = 0
        for t in range(T):
            if dp[e - 1, t] > cur_val:
                cur_val = dp[e - 1, t]
                cur_idx = t
            best_val[t] = cur_val
            best_idx[t] = cur_idx
        dp[e, :] = logp[:, e] + best_val
        ptr[e, :] = best_idx

    t = int(np.argmax(dp[E - 1, :]))
    frames = np.empty(E, dtype=np.int32)
    for e in range(E - 1, -1, -1):
        frames[e] = t
        if e > 0:
            t = int(ptr[e, t])
    return frames


class SampleVideo(Dataset):
    def __init__(self, path, target_h=380, target_w=678, transform=None):
        self.path = path
        self.target_h = int(target_h)
        self.target_w = int(target_w)
        self.transform = transform

    def __len__(self):
        return 1

    def __getitem__(self, idx):
        cap = cv2.VideoCapture(self.path)
        if not cap.isOpened():
            raise FileNotFoundError(f'Cannot open video: {self.path}')
        frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        th, tw = self.target_h, self.target_w

        scale = min(tw / max(frame_w, 1), th / max(frame_h, 1))
        new_w = max(1, int(round(frame_w * scale)))
        new_h = max(1, int(round(frame_h * scale)))
        delta_w = tw - new_w
        delta_h = th - new_h
        top, bottom = delta_h // 2, delta_h - (delta_h // 2)
        left, right = delta_w // 2, delta_w - (delta_w // 2)

        # preprocess and return frames
        images = []
        for pos in range(int(cap.get(cv2.CAP_PROP_FRAME_COUNT))):
            ret, img = cap.read()
            if not ret or img is None:
                break
            resized = cv2.resize(img, (new_w, new_h))
            b_img = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT,
                                       value=[0.406 * 255, 0.456 * 255, 0.485 * 255])  # ImageNet means (BGR)

            if b_img.shape[0] != th or b_img.shape[1] != tw:
                b_img = cv2.resize(b_img, (tw, th))

            b_img_rgb = cv2.cvtColor(b_img, cv2.COLOR_BGR2RGB)
            images.append(b_img_rgb)
        cap.release()

        if len(images) == 0:
            raise ValueError('No frames were read from the video (empty decode).')

        labels = np.zeros(len(images)) # only for compatibility with transforms
        sample = {'images': np.stack(images, axis=0), 'labels': np.asarray(labels)}
        if self.transform:
            sample = self.transform(sample)
        return sample


def extract_key_frames(
    video_path: str,
    weights: str,
    seq_length: int = 64,
    num_events: int | None = 8,
    decode: str = "ordered",
    height: int = 224,
    width: int = 224,
    output_root: str | None = None,
):
    """Extract swing event keyframes from a video.

    Returns a dict with:
      - out_dir: str
      - events: np.ndarray
      - confidence: list[float]
      - device: str
      - num_events: int
    """
    if output_root is None:
        output_root = str(Path(__file__).resolve().parent / "output")

    if decode not in {"ordered", "independent"}:
        raise ValueError("decode must be 'ordered' or 'independent'")

    ds = SampleVideo(
        video_path,
        target_h=height,
        target_w=width,
        transform=transforms.Compose([
            ToTensor(),
            Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]),
    )
    dl = DataLoader(ds, batch_size=1, shuffle=False, drop_last=False)

    try:
        save_dict = _torch_load(weights, map_location="cpu")
    except Exception as e:
        raise FileNotFoundError(
            f"Model weights not found: {weights}. Pass --weights to point to a valid checkpoint."
        ) from e

    inferred_num_events = None
    try:
        inferred_num_classes = int(save_dict["model_state_dict"]["lin.weight"].shape[0])
        inferred_num_events = inferred_num_classes - 1
    except Exception:
        pass

    effective_num_events = num_events if num_events is not None else inferred_num_events
    if effective_num_events is None:
        effective_num_events = 8

    model = EventDetector(
        pretrain=True,
        width_mult=1.0,
        lstm_layers=1,
        lstm_hidden=256,
        bidirectional=True,
        dropout=False,
        num_events=effective_num_events,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.load_state_dict(save_dict["model_state_dict"])
    model.to(device)
    model.eval()

    with torch.inference_mode():
        probs = None
        for sample in dl:
            images = sample["images"]
            batch = 0
            while batch * seq_length < images.shape[1]:
                if (batch + 1) * seq_length > images.shape[1]:
                    image_batch = images[:, batch * seq_length:, :, :, :]
                else:
                    image_batch = images[:, batch * seq_length:(batch + 1) * seq_length, :, :, :]
                logits = model(image_batch.to(device))
                p = F.softmax(logits, dim=1).cpu().numpy()
                probs = p if probs is None else np.append(probs, p, 0)
                batch += 1

    if probs is None:
        raise ValueError("Failed to compute event probabilities (empty video?).")

    if decode == "ordered":
        events = decode_events_ordered(probs, num_events=effective_num_events)
    else:
        events = decode_events_independent(probs, num_events=effective_num_events)

    confidence = [float(probs[int(e), i]) for i, e in enumerate(events)]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    from datetime import datetime

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = str(Path(output_root) / ts)
    os.makedirs(out_dir, exist_ok=True)

    try:
        for i, e in enumerate(events):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(e))
            ret, img = cap.read()
            if not ret or img is None:
                continue

            cv2.putText(
                img,
                f"{confidence[i]:.3f}",
                (20, 40),
                cv2.FONT_HERSHEY_DUPLEX,
                0.75,
                (0, 0, 255),
                2,
            )

            cv2.imwrite(str(Path(out_dir) / f"event_{i:03d}_frame_{int(e)}.jpg"), img)
    finally:
        cap.release()

    return {
        "out_dir": out_dir,
        "events": events,
        "confidence": confidence,
        "device": str(device),
        "num_events": int(effective_num_events),
    }


if __name__ == '__main__':
    import sys
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    import config

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', help='Path to video that you want to test', required=True)
    parser.add_argument('-s', '--seq-length', type=int, help='Number of frames to use per forward pass', default=config.KEYFRAME_CONFIG['SEQ_LENGTH'])
    parser.add_argument('-e', '--num-events', type=int, help='Number of swing events (excluding no-event). If omitted, infer from checkpoint.', default=config.KEYFRAME_CONFIG['NUM_EVENTS'])
    parser.add_argument('-w', '--weights', type=str, help='Path to model checkpoint (.pth.tar)', default=config.KEYFRAME_CONFIG['WEIGHTS_PATH'])
    parser.add_argument('--decode', choices=['ordered', 'independent'], default=config.KEYFRAME_CONFIG['DECODE_METHOD'], help='How to pick event frames from per-frame probabilities')
    parser.add_argument('--height', type=int, default=config.KEYFRAME_CONFIG['INPUT_SIZE'][0], help='Model input height (after resize/pad)')
    parser.add_argument('--width', type=int, default=config.KEYFRAME_CONFIG['INPUT_SIZE'][1], help='Model input width (after resize/pad)')
    args = parser.parse_args()
    result = extract_key_frames(
        video_path=args.path,
        weights=args.weights,
        seq_length=args.seq_length,
        num_events=args.num_events,
        decode=args.decode,
        height=args.height,
        width=args.width,
        output_root=None,
    )
    print(f"Using device: {result['device']}")
    print(f"Predicted event frames: {result['events']}")
    print(f"Confidence: {[round(c, 3) for c in result['confidence']]}")
    print(f"Saved keyframes to: {result['out_dir']}")