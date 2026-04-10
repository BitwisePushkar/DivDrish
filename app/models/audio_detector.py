import torch
import torch.nn as nn
import numpy as np
import librosa
from app.models.base_detector import BaseDetector, RawDetection
from app.utils.logger import logger

class LightCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.AdaptiveAvgPool2d((8, 8)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 64, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, 2)
        )
    def forward(self, x):
        return self.classifier(self.features(x))

class AudioDetector(BaseDetector):
    SR = 16000
    N_MELS = 80
    HOP = 160

    def load(self):
        logger.info("Loading audio detector (LCNN)...")
        self.model = LightCNN()
        self.model.eval().to(self.device)
        logger.success("Audio detector ready")

    def predict(self, file_path: str) -> RawDetection:
        self.ensure_loaded()
        y, sr = librosa.load(file_path, sr=self.SR, mono=True)
        chunk_size = self.SR * 3
        chunks = [
            y[i:i+chunk_size]
            for i in range(0, len(y), chunk_size)
            if len(y[i:i+chunk_size]) == chunk_size
        ]
        if not chunks:
            chunks = [librosa.util.fix_length(y, size=chunk_size)]

        chunk_scores = []
        for chunk in chunks[:20]:
            mel = librosa.feature.melspectrogram(
                y=chunk, sr=self.SR, n_mels=self.N_MELS, hop_length=self.HOP
            )
            mel_db = librosa.power_to_db(mel, ref=np.max)
            tensor = torch.tensor(
                mel_db, dtype=torch.float32
            ).unsqueeze(0).unsqueeze(0).to(self.device)
            with torch.no_grad():
                logits = self.model(tensor)
                prob = torch.softmax(logits, dim=1)[0][1].item()
            chunk_scores.append(prob)

        confidence = float(np.mean(chunk_scores))
        artifacts = self._analyze_audio(y, sr)

        return RawDetection(
            confidence=confidence,
            frame_scores=chunk_scores,
            artifact_scores=artifacts,
            metadata={
                "duration_sec": round(len(y) / sr, 2),
                "sample_rate": sr
            }
        )

    def _analyze_audio(self, y: np.ndarray, sr: int) -> dict:
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        active = pitches[magnitudes > np.max(magnitudes) * 0.1]
        pitch_variance = float(np.var(active)) if len(active) > 0 else 0.0
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_anomaly = float(np.mean(np.abs(np.diff(mfccs, axis=1))))
        silence = float(np.mean(np.abs(y) < 0.01))
        return {
            "pitch_unnaturalness": min(1.0 / (pitch_variance + 1e-4), 1.0),
            "mfcc_discontinuity":  min(mfcc_anomaly / 5.0, 1.0),
            "unnatural_silence":   silence,
        }
