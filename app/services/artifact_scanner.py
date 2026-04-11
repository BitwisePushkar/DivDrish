from typing import List

ARTIFACT_META = {
    "gan_checkerboard":    ("GAN checkerboard pattern",  "High-freq grid artifacts from upsampling layers"),
    "blend_boundary":      ("Facial blend seams",         "Visible boundary between swapped face region"),
    "noise_inconsistency": ("Noise inconsistency",        "Mismatched sensor noise between regions"),
    "temporal_flicker":    ("Temporal flicker",           "Frame-to-frame confidence spikes in video"),
    "score_variance":      ("Score variance",             "High variance in per-frame deepfake scores"),
    "pitch_unnaturalness": ("Unnatural pitch pattern",    "TTS-generated flat or robotic pitch contour"),
    "mfcc_discontinuity":  ("MFCC discontinuity",         "Spectral feature jumps indicating audio splicing"),
    "unnatural_silence":   ("Unnatural silence",          "Overly clean silence typical of synthesized audio"),
}

def build_artifact_list(scores: dict) -> list[dict]:
    results = []
    for key, severity in scores.items():
        if key not in ARTIFACT_META:
            continue
        name, desc = ARTIFACT_META[key]
        results.append({
            "name": name,
            "detected": severity > 0.4,
            "severity": round(severity, 3),
            "description": desc,
        })
    return sorted(results, key=lambda x: x["severity"], reverse=True)