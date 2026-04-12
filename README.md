---

# DivyaDrishti

A minimalist AI-powered system to detect **Deepfake** and **AI-generated content** from images, audio, and video.
Built for reliability, explainability, and real-world deployment.

---

## Tech Stack

`Flask : PyTorch : CNN (LightCNN / ResNet / Xception) : OpenCV : Librosa : Redis : Celery : PostgreSQL : AWS S3 : Docker`

---

## Core Functionality

## Pipelines

### Image Pipeline (Face)

Find Face · Detect and crop the face from the image

Preprocess · Resize, normalize, enhance artifacts

CNN + Attention · Deep CNN (Xception / ResNet) with attention to detect texture & edge anomalies

Score · Generate a “real vs fake” confidence score

Explain · Highlight suspicious regions (eyes, neck, ears)

---

### Video Pipeline

Extract Frames · Sample multiple frames (20–30 frames)

Detect Faces · Run face detection on each frame

Image-style Check · Apply image model on each face → per-frame scores

LSTM / Transformer · Analyze temporal inconsistencies (blinking, lip sync, motion)

Video Score · Aggregate into final verdict + highlight suspicious segments

---

### Audio Pipeline (Voice)

Load Audio · Normalize input voice signal

Spectrogram / MFCC · Convert audio into 2D representation (mel-spectrogram / MFCC)

CNN · Detect abnormal frequency patterns

LSTM · Analyze temporal rhythm, prosody, unnatural smoothness

Final Score · Classify as real or deepfake voice + highlight suspicious time segments

---

## Setup (Local)

```bash id="o6i9rj"
git clone <repo>
cd DivyaDrishti

python -m venv venv
source venv/bin/activate   # windows: venv\Scripts\activate

pip install -r requirements.txt

python app.py
```

App → `http://localhost:5000`

---

## Setup (Docker)

```bash id="l3x7qn"
docker-compose up --build
```

---