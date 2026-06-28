#!/usr/bin/env python3
"""
Spectrogram Steganography Analyzer
====================================
Analyzes a WAV audio file for hidden text, images, QR codes, or clues
embedded in the spectrogram (frequency-domain visual representation).

Usage:
    python spectrogram_stego.py <audio_file.wav>

Requirements:
    pip install numpy scipy matplotlib pillow opencv-python pyzbar
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from scipy.io import wavfile
from scipy.signal import spectrogram as scipy_spectrogram
from PIL import Image
import warnings

warnings.filterwarnings("ignore")

# ── Optional imports (graceful degradation) ──────────────────────────────────
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("[!] opencv-python not installed – QR/barcode detection skipped.")
    print("    Run: pip install opencv-python\n")

try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    print("[!] pyzbar not installed – QR/barcode detection skipped.")
    print("    Run: pip install pyzbar\n")


# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD AUDIO
# ─────────────────────────────────────────────────────────────────────────────
def load_wav(path: str):
    """Load a WAV file and return (sample_rate, mono_float32_samples)."""
    if not os.path.exists(path):
        print(f"[ERROR] File not found: {path}")
        sys.exit(1)

    sample_rate, data = wavfile.read(path)

    # Stereo → mono
    if data.ndim == 2:
        data = data.mean(axis=1)

    # Normalise to [-1, 1]
    data = data.astype(np.float32)
    max_val = np.max(np.abs(data))
    if max_val > 0:
        data /= max_val

    duration = len(data) / sample_rate
    print(f"[+] Loaded  : {path}")
    print(f"    Sample rate : {sample_rate} Hz")
    print(f"    Duration    : {duration:.2f} s  ({len(data)} samples)")
    return sample_rate, data


# ─────────────────────────────────────────────────────────────────────────────
# 2. BUILD SPECTROGRAM
# ─────────────────────────────────────────────────────────────────────────────
def build_spectrogram(sample_rate: int, data: np.ndarray,
                      nperseg: int = 1024, overlap: float = 0.875):
    """
    Compute a power spectrogram.
    overlap=0.875 → 87.5 % window overlap for high time resolution.
    Returns (freqs, times, Sdb) where Sdb is dB-scaled magnitude.
    """
    noverlap = int(nperseg * overlap)
    freqs, times, Sxx = scipy_spectrogram(
        data, fs=sample_rate,
        nperseg=nperseg, noverlap=noverlap,
        window="hann", scaling="spectrum"
    )
    # Convert to dB, avoid log(0)
    Sdb = 10 * np.log10(np.maximum(Sxx, 1e-12))
    return freqs, times, Sdb


# ─────────────────────────────────────────────────────────────────────────────
# 3. SAVE SPECTROGRAM AS IMAGE
# ─────────────────────────────────────────────────────────────────────────────
def save_spectrogram_image(freqs, times, Sdb,
                           out_path: str = "spectrogram_full.png",
                           cmap: str = "inferno",
                           vmin: float = None, vmax: float = None):
    """Save the full spectrogram as a high-resolution image."""
    if vmin is None:
        vmin = np.percentile(Sdb, 5)
    if vmax is None:
        vmax = np.percentile(Sdb, 99.5)

    fig, ax = plt.subplots(figsize=(20, 8), dpi=150)
    img = ax.pcolormesh(times, freqs, Sdb, shading="gouraud",
                        cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_ylabel("Frequency (Hz)")
    ax.set_xlabel("Time (s)")
    ax.set_title("Spectrogram – Full Range")
    fig.colorbar(img, ax=ax, label="Power (dB)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[+] Saved full spectrogram  → {out_path}")
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# 4. FREQUENCY-BAND SLICES  (where hidden content usually lives)
# ─────────────────────────────────────────────────────────────────────────────
BANDS = [
    ("subsonic",    0,    20),
    ("low",         20,   300),
    ("mid",         300,  3000),
    ("high",        3000, 8000),
    ("ultrasonic",  8000, None),   # None = top of available spectrum
]

def save_band_slices(freqs, times, Sdb, out_dir: str = "."):
    """Save a zoomed spectrogram for each frequency band."""
    saved = []
    for name, flo, fhi in BANDS:
        fhi_actual = freqs[-1] if fhi is None else min(fhi, freqs[-1])
        mask = (freqs >= flo) & (freqs <= fhi_actual)
        if not mask.any():
            continue

        slice_db = Sdb[mask, :]
        slice_f  = freqs[mask]

        # Skip near-empty bands
        if slice_db.shape[0] < 2:
            continue

        vmin = np.percentile(slice_db, 5)
        vmax = np.percentile(slice_db, 99.5)

        fig, ax = plt.subplots(figsize=(20, 4), dpi=150)
        ax.pcolormesh(times, slice_f, slice_db, shading="gouraud",
                      cmap="inferno", vmin=vmin, vmax=vmax)
        ax.set_ylabel("Frequency (Hz)")
        ax.set_xlabel("Time (s)")
        ax.set_title(f"Band: {name}  ({flo}–{int(fhi_actual)} Hz)")
        fig.tight_layout()

        path = os.path.join(out_dir, f"spectrogram_band_{name}.png")
        fig.savefig(path, dpi=150)
        plt.close(fig)
        saved.append(path)
        print(f"    Band [{name:12s}] saved → {path}")

    return saved


# ─────────────────────────────────────────────────────────────────────────────
# 5. HIGH-CONTRAST / THRESHOLDED VIEW  (reveals faint hidden patterns)
# ─────────────────────────────────────────────────────────────────────────────
def save_high_contrast(freqs, times, Sdb,
                       out_path: str = "spectrogram_hc.png"):
    """
    Normalise to [0,255] and apply a hard threshold to reveal faint structure.
    Hidden images are often very faint – boosting contrast uncovers them.
    """
    norm = (Sdb - Sdb.min()) / (Sdb.max() - Sdb.min() + 1e-9)
    norm_u8 = (norm * 255).astype(np.uint8)

    # Threshold: keep only pixels above 60th percentile
    thresh = int(np.percentile(norm_u8, 60))
    binary = np.where(norm_u8 >= thresh, norm_u8, 0).astype(np.uint8)

    fig, axes = plt.subplots(1, 2, figsize=(22, 6), dpi=150)
    axes[0].imshow(norm_u8, aspect="auto", origin="lower",
                   cmap="hot", interpolation="nearest")
    axes[0].set_title("Normalised (Hot colormap)")

    axes[1].imshow(binary, aspect="auto", origin="lower",
                   cmap="gray", interpolation="nearest")
    axes[1].set_title(f"Thresholded (≥ {thresh}/255)")

    for ax in axes:
        ax.set_xlabel("Time frames")
        ax.set_ylabel("Frequency bins")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[+] Saved high-contrast view → {out_path}")
    return out_path, norm_u8


# ─────────────────────────────────────────────────────────────────────────────
# 6. QR / BARCODE DETECTION
# ─────────────────────────────────────────────────────────────────────────────
def detect_qr_and_barcodes(norm_u8: np.ndarray, out_path: str = "qr_result.png"):
    """
    Try to decode QR codes / barcodes from the spectrogram image.
    Requires opencv-python and pyzbar.
    """
    if not CV2_AVAILABLE or not PYZBAR_AVAILABLE:
        print("[!] QR detection skipped (missing libraries).")
        return []

    # Flip vertically (spectrograms are drawn bottom-up, images top-down)
    img_bgr = cv2.cvtColor(norm_u8[::-1], cv2.COLOR_GRAY2BGR)

    # Try multiple preprocessing strategies
    attempts = {
        "raw":           norm_u8[::-1],
        "inverted":      255 - norm_u8[::-1],
        "equalized":     cv2.equalizeHist(norm_u8[::-1]),
    }

    found = []
    for label, attempt in attempts.items():
        pil = Image.fromarray(attempt)
        decoded = pyzbar.decode(pil)
        for obj in decoded:
            data = obj.data.decode("utf-8", errors="replace")
            kind = obj.type
            rect = obj.rect
            print(f"    [QR/Barcode] type={kind}  data={data!r}  "
                  f"strategy={label}  rect={rect}")
            found.append({"type": kind, "data": data,
                          "rect": rect, "strategy": label})

            # Draw bounding box on the image
            x, y, w, h = rect
            cv2.rectangle(img_bgr, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(img_bgr, f"{kind}: {data[:30]}",
                        (x, max(y-5, 10)), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 0), 1)

    if found:
        cv2.imwrite(out_path, img_bgr)
        print(f"[+] QR result image saved → {out_path}")
    else:
        print("    No QR codes / barcodes auto-detected in spectrogram.")
        print("    → Try opening spectrogram_full.png / band images visually.")

    return found


# ─────────────────────────────────────────────────────────────────────────────
# 7. STATISTICAL ANOMALY SCAN
# ─────────────────────────────────────────────────────────────────────────────
def anomaly_scan(freqs, times, Sdb):
    """
    Flag time segments and frequency bins that are statistically unusual –
    a simple heuristic for detecting embedded content.
    """
    print("\n[+] Anomaly scan …")

    # Per-time-frame energy
    frame_energy = Sdb.mean(axis=0)
    mu, sigma = frame_energy.mean(), frame_energy.std()
    hot_frames = np.where(frame_energy > mu + 2.5 * sigma)[0]
    if hot_frames.size:
        hot_times = times[hot_frames]
        print(f"    High-energy time windows (±2.5σ): "
              f"{hot_times.round(3).tolist()}")
    else:
        print("    No statistically anomalous time frames detected.")

    # Per-frequency-bin energy
    bin_energy = Sdb.mean(axis=1)
    mu_f, sigma_f = bin_energy.mean(), bin_energy.std()
    hot_bins = np.where(bin_energy > mu_f + 2.5 * sigma_f)[0]
    if hot_bins.size:
        hot_freqs = freqs[hot_bins]
        print(f"    High-energy frequency bins  (±2.5σ): "
              f"{hot_freqs.round(1).tolist()} Hz")
    else:
        print("    No statistically anomalous frequency bins detected.")

    return hot_frames, hot_bins


# ─────────────────────────────────────────────────────────────────────────────
# 8. SUMMARY REPORT
# ─────────────────────────────────────────────────────────────────────────────
def print_summary(wav_path, qr_results, out_dir):
    print("\n" + "="*60)
    print("  SPECTROGRAM STEGANOGRAPHY ANALYSIS – SUMMARY")
    print("="*60)
    print(f"  Source file : {wav_path}")
    print(f"  Output dir  : {os.path.abspath(out_dir)}")
    print()

    if qr_results:
        print(f"  ✅  {len(qr_results)} QR / barcode(s) found:")
        for r in qr_results:
            print(f"       • [{r['type']}] {r['data']}")
    else:
        print("  ℹ️  No QR codes auto-detected.")
        print("       → Inspect the saved PNG images manually.")
        print("       → Look for shapes, text, patterns in the spectrogram.")
        print("       → Hidden images often appear in high or ultrasonic bands.")

    print()
    print("  Saved files:")
    for f in os.listdir(out_dir):
        if f.endswith(".png"):
            print(f"       • {os.path.join(out_dir, f)}")
    print("="*60)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: python spectrogram_stego.py <audio.wav>")
        sys.exit(1)

    wav_path = sys.argv[1]
    out_dir  = os.path.splitext(wav_path)[0] + "_stego_output"
    os.makedirs(out_dir, exist_ok=True)

    print("\n" + "="*60)
    print("  Spectrogram Steganography Analyzer")
    print("="*60 + "\n")

    # 1. Load
    sample_rate, data = load_wav(wav_path)

    # 2. Build spectrogram (high time-resolution)
    print("[+] Computing spectrogram …")
    freqs, times, Sdb = build_spectrogram(sample_rate, data,
                                          nperseg=2048, overlap=0.9)
    print(f"    Shape: {Sdb.shape[0]} freq bins × {Sdb.shape[1]} time frames")

    # 3. Full spectrogram image
    save_spectrogram_image(
        freqs, times, Sdb,
        out_path=os.path.join(out_dir, "spectrogram_full.png")
    )

    # 4. Frequency-band slices
    print("[+] Saving frequency-band slices …")
    save_band_slices(freqs, times, Sdb, out_dir=out_dir)

    # 5. High-contrast view + get normalised pixel array
    _, norm_u8 = save_high_contrast(
        freqs, times, Sdb,
        out_path=os.path.join(out_dir, "spectrogram_hc.png")
    )

    # 6. QR / barcode detection
    print("[+] Attempting QR / barcode detection …")
    qr_results = detect_qr_and_barcodes(
        norm_u8,
        out_path=os.path.join(out_dir, "qr_result.png")
    )

    # 7. Anomaly scan
    anomaly_scan(freqs, times, Sdb)

    # 8. Summary
    print_summary(wav_path, qr_results, out_dir)


if __name__ == "__main__":
    main()
