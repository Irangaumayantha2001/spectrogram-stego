# 🎵 Spectrogram Steganography Analyzer

> Uncover hidden text, images, QR codes, and secret clues embedded inside WAV audio files using spectrogram analysis.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## 🔍 What is Spectrogram Steganography?

Steganography is the art of hiding secret information inside ordinary-looking files.  
With **audio steganography**, hidden data is painted directly into the **frequency domain** of a WAV file — invisible to the ear, but visible when the audio is rendered as a **spectrogram** (a visual map of frequency vs. time).

Common things hidden this way:
- 🖼️ Images or artwork
- 📝 Secret text / messages
- 📦 QR codes that decode to URLs or data
- 🔑 Clues embedded in CTF (Capture The Flag) challenges

---

## ✨ Features

| Feature | Description |
|---|---|
| 📊 Full Spectrogram | High-resolution view across all frequencies and time |
| 🎚️ Band Slices | Zoomed views of subsonic / low / mid / high / ultrasonic bands |
| 🔆 High-Contrast Mode | Boosts faint hidden patterns invisible at normal contrast |
| 🔲 QR / Barcode Detection | Auto-detects and decodes embedded QR codes using `pyzbar` |
| 📡 Anomaly Scan | Flags statistically unusual time windows and frequency bins |

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/spectrogram-stego.git
cd spectrogram-stego
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Linux users** also need:
> ```bash
> sudo apt install libzbar0
> ```

> **macOS users:**
> ```bash
> brew install zbar
> ```

### 3. Run the analyzer

```bash
python spectrogram_stego.py your_audio.wav
```

All output files are saved to `your_audio_stego_output/`.

---

## 📂 Output Files

```
your_audio_stego_output/
├── spectrogram_full.png          # Full frequency range spectrogram
├── spectrogram_band_subsonic.png # 0–20 Hz band
├── spectrogram_band_low.png      # 20–300 Hz band
├── spectrogram_band_mid.png      # 300–3000 Hz band
├── spectrogram_band_high.png     # 3000–8000 Hz band
├── spectrogram_band_ultrasonic.png # 8000+ Hz band ← hidden content often here!
├── spectrogram_hc.png            # High-contrast + thresholded view
└── qr_result.png                 # QR detection result (if found)
```

---

## 🧠 Tips for Finding Hidden Content

| What to look for | Where to look |
|---|---|
| Hidden **text or words** | Mid / High band images |
| **QR codes** | Check `qr_result.png` or scan `spectrogram_hc.png` manually |
| **Images / art** | Full spectrogram — zoom into the ultrasonic range |
| **Morse code / pulses** | Anomaly scan output in the console |
| **Faint patterns** | `spectrogram_hc.png` — threshold view reveals invisible details |

---

## 🛠️ Requirements

```
numpy
scipy
matplotlib
pillow
opencv-python
pyzbar
```

The script gracefully degrades if `opencv-python` or `pyzbar` are missing — all other features still work.

---

## 🗂️ Project Structure

```
spectrogram-stego/
├── spectrogram_stego.py    # Main analyzer script
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── LICENSE                 # MIT License
├── samples/                # Place test WAV files here
└── output/                 # Example output images (gitignored)
```

---

## 💡 Example Use Cases

- 🏴 **CTF Challenges** — Many Capture The Flag puzzles hide flags in audio spectrograms
- 🔐 **Digital Forensics** — Investigate audio files for covert data exfiltration
- 🎨 **Audio Art** — Artists like Aphex Twin have hidden images in their music spectrograms
- 🧪 **Security Research** — Study steganographic techniques in audio

---

## 📖 How It Works

1. **Load** the WAV file and convert to mono float32
2. **Compute** a Short-Time Fourier Transform (STFT) via `scipy.signal.spectrogram`
3. **Render** the power spectrum in dB across multiple frequency bands
4. **Enhance** contrast to reveal faint hidden patterns
5. **Scan** for QR codes / barcodes using OpenCV + pyzbar
6. **Flag** statistical anomalies in time and frequency domains

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Pull requests are welcome! Please open an issue first to discuss changes.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## ⭐ Star this repo if it helped you find a hidden flag!
