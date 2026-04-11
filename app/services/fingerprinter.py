from typing import Optional

FINGERPRINTS = {
    "FaceSwap":     {"blend_boundary": (0.6,1.0), "noise_inconsistency": (0.5,1.0)},
    "DeepFaceLab":  {"blend_boundary": (0.4,0.8), "temporal_flicker":    (0.1,0.4)},
    "DALL-E":       {"gan_checkerboard":(0.0,0.2), "noise_inconsistency": (0.3,0.7)},
    "Stable Diff.": {"gan_checkerboard":(0.3,0.8), "blend_boundary":      (0.0,0.3)},
    "ElevenLabs":   {"pitch_unnaturalness":(0.6,1.0),"unnatural_silence": (0.5,1.0)},
    "VITS TTS":     {"mfcc_discontinuity":(0.5,1.0),"pitch_unnaturalness":(0.4,0.9)},
    "GAN Generic":  {"gan_checkerboard": (0.5,1.0)},
    "Midjourney":   {"gan_checkerboard":(0.1,0.4), "noise_inconsistency": (0.2,0.5)},
}
def fingerprint_model(artifact_scores: dict) -> Optional[str]:
    best_match, best_score = None, 0.0
    for model_name, signatures in FINGERPRINTS.items():
        match_scores = []
        for key, (lo, hi) in signatures.items():
            val = artifact_scores.get(key, -1)
            if val < 0:
                continue
            if lo <= val <= hi:
                mid = (lo + hi) / 2
                half = (hi - lo) / 2 + 1e-6
                match_scores.append(1.0 - abs(val - mid) / half)
            else:
                match_scores.append(0.0)
        if match_scores:
            avg = sum(match_scores) / len(match_scores)
            if avg > best_score:
                best_score, best_match = avg, model_name
    return best_match if best_score > 0.4 else "Unknown GAN"