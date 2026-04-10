import torch
import timm
import numpy as np
from PIL import Image
from torchvision import transforms
from app.models.base_detector import BaseDetector, RawDetection
from app.utils.logger import logger

class ImageDetector(BaseDetector):

    TRANSFORM = transforms.Compose([
        transforms.Resize((299, 299)),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
    ])

    def load(self):
        logger.info("Loading image detector (EfficientNet B4)...")
        self.model = timm.create_model(
            "efficientnet_b4",
            pretrained=True,
            num_classes=2
        )
        self.model.eval()
        self.model.to(self.device)
        logger.success("Image detector ready")

    def predict(self, file_path: str) -> RawDetection:
        self.ensure_loaded()
        img = Image.open(file_path).convert("RGB")
        tensor = self.TRANSFORM(img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)
            fake_prob = probs[0][1].item()

        artifacts = self._analyze_artifacts(img)

        return RawDetection(
            confidence=fake_prob,
            frame_scores=[fake_prob],
            artifact_scores=artifacts,
            metadata={
                "width": img.width,
                "height": img.height,
                "mode": img.mode
            }
        )

    def _analyze_artifacts(self, img: Image.Image) -> dict:
        from scipy import ndimage
        gray = np.array(img.convert("L"), dtype=np.float32)
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.log(np.abs(fft_shift) + 1)
        h, w = magnitude.shape
        hf_region = magnitude[h//4:3*h//4, w//4:3*w//4]
        hf_variance = float(np.var(hf_region))
        lap = ndimage.laplace(gray)
        blend_score = float(np.var(lap) / (np.mean(np.abs(lap)) + 1e-6))
        noise = gray - ndimage.gaussian_filter(gray, sigma=1)
        noise_var = float(np.var(noise))
        return {
            "gan_checkerboard": min(hf_variance / 500.0, 1.0),
            "blend_boundary":   min(blend_score / 100.0, 1.0),
            "noise_inconsistency": min(noise_var / 300.0, 1.0),
        }
