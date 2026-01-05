import os
import os.path as osp
import cv2
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
import json


class KeyFramesDataset(Dataset):
    """Dataset for swing event spotting from a single-swing clip.

    This implementation is intentionally simplified:
    - Supports CSV only (your key_frames_combined.csv style)
    - Requires a per-row video path and 9 keyframe columns (or an explicit 'events' column)
    - Builds events as [start(0), 9 keyframes, end(video_frames-1)]
    """

    DEFAULT_KEYFRAME_COLS = [
        '脚尖抬起',
        '起摆动作',
        '上杆',
        '顶点',
        '上下转换',
        '击球前',
        '击球瞬间',
        '送杆',
        # '随势挥杆',
    ]

    def __init__(self, data_file, seq_length, transform=None, train=True, keyframe_cols=None):
        self.data_file = data_file
        self.csv_dir = osp.dirname(osp.abspath(str(data_file)))
        self.df = self._load_csv(data_file, keyframe_cols=keyframe_cols)
        self.seq_length = seq_length
        self.transform = transform
        self.train = train

    @staticmethod
    def _parse_events_cell(value):
        """Parse an 'events' cell from CSV.

        Accepts:
        - JSON list string: "[0, 12, 34, ...]"
        - Comma-separated: "0,12,34,..."
        """
        if isinstance(value, (list, tuple, np.ndarray)):
            return np.asarray(value, dtype=np.float32)
        if pd.isna(value):
            raise ValueError('events is missing')
        if not isinstance(value, str):
            return np.asarray(value, dtype=np.float32)
        s = value.strip()
        if s.startswith('[') and s.endswith(']'):
            return np.asarray(json.loads(s), dtype=np.float32)
        return np.asarray([float(x) for x in s.split(',') if x.strip() != ''], dtype=np.float32)

    def _load_csv(self, csv_path, keyframe_cols=None):
        if not str(csv_path).lower().endswith('.csv'):
            raise ValueError('This dataloader supports CSV only.')

        df = pd.read_csv(csv_path)

        if 'video_path' not in df.columns:
            raise ValueError("CSV must contain a 'video_path' column")
        df['video_path'] = df['video_path'].astype(str)

        cols = keyframe_cols or self.DEFAULT_KEYFRAME_COLS
        if 'events' in df.columns:
            df['events'] = df['events'].apply(self._parse_events_cell)
        else:
            missing = [c for c in cols if c not in df.columns]
            if missing:
                raise ValueError(
                    "CSV missing required keyframe columns: {}".format(missing)
                )

            def _row_to_events(row):
                keyframes = [row[c] for c in cols]
                # start=0, end will be filled from video length at runtime
                return np.asarray([0] + keyframes + [np.nan], dtype=np.float32)

            df['events'] = df.apply(_row_to_events, axis=1)

        return df.reset_index(drop=True)

    def _resolve_video_path(self, video_path: str) -> str:
        # Resolve relative paths against the CSV directory.
        if osp.isabs(video_path):
            return video_path
        return osp.abspath(osp.join(self.csv_dir, video_path))

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        a = self.df.loc[idx, :]
        video_path = self._resolve_video_path(a['video_path'])
        events = a['events']

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f'Cannot open video: {video_path}')

        # Fill missing start/end if needed.
        if len(events) < 3:
            cap.release()
            raise ValueError('events must include at least [start, event1, end]')

        if not np.isfinite(events[0]):
            events[0] = 0
        if (not np.isfinite(events[-1])) or (events[-1] < 0):
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            events[-1] = max(total_frames - 1, 0)

        # Convert to integer frame indices.
        events = np.rint(events).astype(int)
        events -= events[0]  # now frame #s correspond to frames in the clip

        # Infer number of event classes from annotation: events[1:-1] are swing events.
        num_events = len(events[1:-1])

        images, labels = [], []

        if self.train:
            # random starting position, sample 'seq_length' frames
            start_frame = np.random.randint(events[-1] + 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            pos = start_frame
            while len(images) < self.seq_length:
                ret, img = cap.read()
                if ret:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    images.append(img)
                    if pos in events[1:-1]:
                        labels.append(np.where(events[1:-1] == pos)[0][0])
                    else:
                        labels.append(num_events)
                    pos += 1
                else:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    pos = 0
            cap.release()
        else:
            # full clip
            for pos in range(int(cap.get(cv2.CAP_PROP_FRAME_COUNT))):
                _, img = cap.read()
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                images.append(img)
                if pos in events[1:-1]:
                    labels.append(np.where(events[1:-1] == pos)[0][0])
                else:
                    labels.append(num_events)
            cap.release()

        sample = {'images':np.asarray(images), 'labels':np.asarray(labels)}
        if self.transform:
            sample = self.transform(sample)
        return sample


class ResizePad(object):
    """Resize frames to fit inside (target_h, target_w) and pad to exact size.

    - Preserves aspect ratio (no distortion).
    - Pads with ImageNet mean color (RGB) by default.

    Expects sample['images'] as np.ndarray shaped (T, H, W, 3) in RGB.
    """

    def __init__(self, target_h: int, target_w: int, pad_value_rgb=None, interpolation=cv2.INTER_LINEAR):
        self.target_h = int(target_h)
        self.target_w = int(target_w)
        if pad_value_rgb is None:
            pad_value_rgb = [0.485 * 255, 0.456 * 255, 0.406 * 255]
        self.pad_value_rgb = [float(x) for x in pad_value_rgb]
        self.interpolation = interpolation

    def __call__(self, sample):
        images, labels = sample['images'], sample['labels']
        if images is None:
            return sample

        out = []
        th, tw = self.target_h, self.target_w
        for img in images:
            if img is None:
                continue
            h, w = img.shape[:2]
            if h == th and w == tw:
                out.append(img)
                continue

            scale = min(tw / max(w, 1), th / max(h, 1))
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))

            resized = cv2.resize(img, (new_w, new_h), interpolation=self.interpolation)
            canvas = np.empty((th, tw, 3), dtype=resized.dtype)
            canvas[:, :, 0] = self.pad_value_rgb[0]
            canvas[:, :, 1] = self.pad_value_rgb[1]
            canvas[:, :, 2] = self.pad_value_rgb[2]

            top = (th - new_h) // 2
            left = (tw - new_w) // 2
            canvas[top:top + new_h, left:left + new_w] = resized
            out.append(canvas)

        return {'images': np.asarray(out), 'labels': labels}


class ToTensor(object):
    """Convert ndarrays in sample to Tensors."""
    def __call__(self, sample):
        images, labels = sample['images'], sample['labels']
        # Ensure images is a numeric array of shape (T, H, W, C)
        if isinstance(images, np.ndarray) and images.dtype == object:
            try:
                images = np.stack(list(images), axis=0)
            except Exception as e:
                raise ValueError(f"Failed to stack image list; frames may have inconsistent shapes. Got dtype=object, shape={images.shape}") from e

        if not isinstance(images, np.ndarray):
            images = np.asarray(images)

        if images.ndim == 3:
            images = images[None, ...]

        if images.ndim != 4:
            raise ValueError(f"Expected images with shape (T,H,W,C); got shape={getattr(images, 'shape', None)}")

        # Handle grayscale frames: (T,H,W,1) -> (T,H,W,3)
        if images.shape[-1] == 1:
            images = np.repeat(images, 3, axis=-1)

        images = images.transpose((0, 3, 1, 2))
        return {'images': torch.from_numpy(images).float().div(255.),
                'labels': torch.from_numpy(labels).long()}


class Normalize(object):
    def __init__(self, mean, std):
        self.mean = torch.tensor(mean, dtype=torch.float32)
        self.std = torch.tensor(std, dtype=torch.float32)

    def __call__(self, sample):
        images, labels = sample['images'], sample['labels']
        images.sub_(self.mean[None, :, None, None]).div_(self.std[None, :, None, None])
        return {'images': images, 'labels': labels}


if __name__ == '__main__':

    norm = Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])  # ImageNet mean and std (RGB)

    dataset = KeyFramesDataset(data_file='data/key_frames_combined.csv',
                     seq_length=64,
                     transform=transforms.Compose([ToTensor(), norm]),
                     train=False)

    data_loader = DataLoader(dataset, batch_size=1, shuffle=False, num_workers=6, drop_last=False)

    for i, sample in enumerate(data_loader):
        images, labels = sample['images'], sample['labels']
        no_event_class = int(labels.max().item())
        events = np.where(labels.squeeze() < no_event_class)[0]
        print('{} events: {}'.format(len(events), events))




    





       

