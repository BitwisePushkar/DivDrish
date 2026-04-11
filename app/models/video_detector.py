import torch
import timm
import cv2
import numpy as np
from torchvision import transforms
from PIL import Image
from app.models.base_detector import BaseDetector, RawDetection
from app.utils.logger import logger
from app.config.settings import get_config
from facenet_pytorch import MTCNN

def _get_config():
    return get_config()

class VideoDetector(BaseDetector):
    TRANSFORM = transforms.Compose([
        transforms.Resize((380, 380)),
        transforms.ToTensor(),
        transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
    ])
    def load(self):
        logger.info("Loading video detector (EfficientNet B4)...")
        self.classifier = timm.create_model(
            "efficientnet_b4", pretrained=True, num_classes=2
        )
        self.classifier.eval().to(self.device)
        try:
            self.face_detector = MTCNN(
                keep_all=False, device=self.device,
                margin=20, min_face_size=40
            )
            self.use_face = True
        except Exception as e:
            logger.warning(f"MTCNN unavailable ({e}), using full-frame mode")
            self.face_detector = None
            self.use_face = False
        logger.success("Video detector ready")

    def predict(self, file_path: str) -> RawDetection:
        self.ensure_loaded()
        config = _get_config()
        cap = cv2.VideoCapture(file_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_scores = []
        frame_results = []
        sample_interval = max(1, int(fps / config.FRAMES_PER_SECOND))
        frame_idx = 0
        while len(frame_scores) < config.MAX_FRAMES:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            score, face_found = self._process_frame(frame)
            frame_scores.append(score)
            frame_results.append({
                "frame": frame_idx,
                "ts": round(frame_idx / fps, 2),
                "score": round(score, 4),
                "face": face_found
            })
            frame_idx += sample_interval
        cap.release()
        if not frame_scores:
            return RawDetection(0.5, [], {}, {"duration": duration})
        weights = np.linspace(0.8, 1.0, len(frame_scores))
        confidence = float(np.average(frame_scores, weights=weights))
        artifacts = self._analyze_temporal(frame_scores)
        return RawDetection(
            confidence=confidence,
            frame_scores=frame_scores,
            artifact_scores=artifacts,
            metadata={
                "duration_sec": round(duration, 2),
                "fps": round(fps, 2),
                "frames_analyzed": len(frame_scores),
                "frame_details": frame_results,
                "resolution": f"{width}x{height}"
            }
        )

    def _process_frame(self, frame: np.ndarray):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        if self.use_face and self.face_detector is not None:
            try:
                face = self.face_detector(pil_img)
                if face is None:
                    return 0.3, False
                tensor = face.unsqueeze(0).to(self.device)
                tensor = (tensor - tensor.min()) / (tensor.max() - tensor.min() + 1e-8)
                with torch.no_grad():
                    logits = self.classifier(tensor)
                    prob = torch.softmax(logits, dim=1)[0][1].item()
                return prob, True
            except Exception:
                pass
        tensor = self.TRANSFORM(pil_img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.classifier(tensor)
            prob = torch.softmax(logits, dim=1)[0][1].item()
        return prob, False

    def _analyze_temporal(self, scores: list) -> dict:
        arr = np.array(scores)
        if len(arr) < 3:
            return {}
        diffs = np.abs(np.diff(arr))
        return {
            "temporal_flicker": float(np.mean(diffs)),
            "score_variance":   float(np.var(arr)),
            "spike_count":      float(np.sum(diffs > 0.25)),
        }
