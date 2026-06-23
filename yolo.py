from __future__ import annotations

import argparse
import os
import threading
import tempfile
import subprocess
import shutil
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None
try:
    import sounddevice as sd
    import soundfile as sf
except ImportError:
    sd = None
    sf = None

try:
    from ultralytics import YOLO
except ImportError as exc:
    raise ImportError(
        "Missing dependency: install ultralytics with `python -m pip install ultralytics`"
    ) from exc

from server_encryption import ServerEncryption


class YOLOObjectDetector:
    def __init__(
        self,
        model: str = 'yolov8n.pt',
        device: str = 'cpu',
        conf: float = 0.25,
        iou: float = 0.45,
        imgsz: int = 640,
    ):
        # Try to use local model in AI folder first
        ai_folder = os.path.dirname(os.path.abspath(__file__))
        local_model = os.path.join(ai_folder, 'yolov8n.pt')
        if os.path.exists(local_model):
            self.model_path = local_model
        else:
            self.model_path = model
        
        self.device = device
        self.conf = conf
        self.iou = iou
        self.imgsz = imgsz
        self.model = YOLO(self.model_path)
        self.names = self.model.names

    def detect(self, image: np.ndarray, max_det: int = 100):
        """Detect objects in a single image and return structured results."""
        results = self.model(
            image,
            imgsz=self.imgsz,
            conf=self.conf,
            iou=self.iou,
            max_det=max_det,
            verbose=False,
        )

        if len(results) == 0:
            return []

        result = results[0]
        detections = []
        if result.boxes is None:
            return []

        boxes = result.boxes.xyxy.cpu().numpy()
        scores = result.boxes.conf.cpu().numpy()
        class_ids = result.boxes.cls.cpu().numpy().astype(int)

        for box, score, class_id in zip(boxes, scores, class_ids):
            detections.append(
                {
                    'box': box.tolist(),
                    'score': float(score),
                    'class_id': int(class_id),
                    'label': self.names[int(class_id)],
                }
            )

        return detections

    def annotate(self, image: np.ndarray, detections: List[Dict[str, Any]], line_thickness: int = 2):
        """Draw bounding boxes and labels on an image."""
        annotated = image.copy()

        for detection in detections:
            x1, y1, x2, y2 = map(int, detection['box'])
            label = f"{detection['label']} {detection['score']:.2f}"
            color = (0, 255, 0)

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, line_thickness)
            text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            text_w, text_h = text_size
            cv2.rectangle(
                annotated,
                (x1, y1 - text_h - 6),
                (x1 + text_w + 6, y1),
                color,
                cv2.FILLED,
            )
            cv2.putText(
                annotated,
                label,
                (x1 + 3, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

        return annotated

    def _estimate_fps(self, frame_intervals: deque[float], capture: cv2.VideoCapture) -> float:
        if frame_intervals:
            average_interval = sum(frame_intervals) / len(frame_intervals)
            fps = 1.0 / average_interval if average_interval > 0 else 30.0
        else:
            fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        return max(5.0, min(30.0, fps))

    def _get_person_frame_percentage(self, detections: List[Dict[str, Any]], frame_height: int, frame_width: int) -> float:
        """Calculate the percentage of frame occupied by the largest person detection."""
        person_detections = [d for d in detections if d['label'] == 'person']
        if not person_detections:
            return 0.0
        
        # Find the largest person bounding box
        max_area = 0
        frame_area = frame_height * frame_width
        
        for detection in person_detections:
            x1, y1, x2, y2 = detection['box']
            box_area = (x2 - x1) * (y2 - y1)
            if box_area > max_area:
                max_area = box_area
        
        percentage = (max_area / frame_area) * 100 if frame_area > 0 else 0.0
        return percentage

    def _finalize_recording(
        self,
        writer: Optional[cv2.VideoWriter],
        audio_recorder: Optional[AudioRecorder],
        video_temp_path: Optional[str],
        audio_temp_path: Optional[str],
        recording_filename: Optional[str],
        duration: Optional[float] = None,
    ) -> None:
        if audio_recorder:
            audio_recorder.stop()
            audio_recorder.join(timeout=5)

        if writer:
            writer.release()
            writer = None

        if audio_recorder and audio_recorder.exception:
            print(f"Audio recorder failed: {audio_recorder.exception}")

        if video_temp_path and recording_filename:
            if audio_temp_path and os.path.exists(audio_temp_path) and get_ffmpeg_executable() is not None:
                try:
                    combine_video_audio(video_temp_path, audio_temp_path, recording_filename, duration)
                    print(f"Recording saved with audio: {recording_filename}")
                except Exception as exc:
                    print(f"Could not merge audio/video: {exc}")
                    os.replace(video_temp_path, recording_filename)
                    print(f"Saved video only to {recording_filename}")
                finally:
                    if os.path.exists(video_temp_path):
                        os.remove(video_temp_path)
                    if os.path.exists(audio_temp_path):
                        os.remove(audio_temp_path)
            else:
                os.replace(video_temp_path, recording_filename)
                print(f"Saved video only to {recording_filename}")
                if os.path.exists(video_temp_path):
                    os.remove(video_temp_path)

    def _finalize_recording_timestamped(
        self,
        audio_recorder: Optional[AudioRecorder],
        frame_paths: List[str],
        frame_timestamps: List[float],
        audio_temp_path: Optional[str],
        recording_filename: Optional[str],
        audio_offset: float = 0.0,
    ) -> None:
        if audio_recorder:
            audio_recorder.stop()
            audio_recorder.join(timeout=5)

        if audio_recorder and audio_recorder.exception:
            print(f"Audio recorder failed: {audio_recorder.exception}")

        if not recording_filename or not frame_paths or len(frame_paths) != len(frame_timestamps):
            return

        ffmpeg_path = get_ffmpeg_executable()
        if not ffmpeg_path:
            raise RuntimeError(
                "ffmpeg not found. Install ffmpeg or install the Python package imageio-ffmpeg."
            )

        # Build an ffconcat file with per-frame durations so the resulting video timeline
        # matches real wall-clock time. This eliminates audio/video drift caused by
        # variable YOLO processing time while writing a constant-FPS video.
        concat_path = os.path.join(tempfile.gettempdir(), f"frames_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.ffconcat")
        try:
            with open(concat_path, "w", encoding="utf-8") as f:
                f.write("ffconcat version 1.0\n")
                for i, frame_path in enumerate(frame_paths):
                    # Durations are between consecutive timestamps. For the last frame, reuse the previous delta.
                    if i + 1 < len(frame_timestamps):
                        duration = max(0.001, frame_timestamps[i + 1] - frame_timestamps[i])
                    elif len(frame_timestamps) >= 2:
                        duration = max(0.001, frame_timestamps[-1] - frame_timestamps[-2])
                    else:
                        duration = 0.033

                    # ffconcat expects forward slashes, and paths need quoting.
                    safe_path = frame_path.replace("\\", "/")
                    f.write(f"file '{safe_path}'\n")
                    f.write(f"duration {duration:.6f}\n")

                # Some ffmpeg versions need the last file repeated to honor the last duration.
                safe_last = frame_paths[-1].replace("\\", "/")
                f.write(f"file '{safe_last}'\n")

            video_only_path = os.path.join(tempfile.gettempdir(), f"video_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.mp4")
            cmd_video = [
                ffmpeg_path,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_path,
                "-vsync",
                "vfr",
                "-pix_fmt",
                "yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                video_only_path,
            ]
            subprocess.run(cmd_video, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

            # Mux audio with the timestamped video. No -async: keep original audio clock.
            if audio_temp_path and os.path.exists(audio_temp_path):
                cmd_mux = [
                    ffmpeg_path,
                    "-y",
                    "-i",
                    video_only_path,
                ]
                if audio_offset > 0:
                    cmd_mux.extend(["-itsoffset", f"{audio_offset:.3f}"])
                cmd_mux.extend([
                    "-i",
                    audio_temp_path,
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-ar",
                    "44100",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-shortest",
                    recording_filename,
                ])
                subprocess.run(cmd_mux, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                print(f"Recording saved with audio: {recording_filename}")
            else:
                os.replace(video_only_path, recording_filename)
                print(f"Saved video only to {recording_filename}")
            
            # Encrypt the recorded video
            try:
                encryptor = ServerEncryption()
                encrypted_path = encryptor.encrypt_file(recording_filename)
                print(f"🔒 Video encrypted: {encrypted_path}")
                # Delete original unencrypted file - keep only encrypted version
                try:
                    if os.path.exists(recording_filename):
                        os.remove(recording_filename)
                        print(f"✅ Original file deleted: {recording_filename}")
                except Exception as e:
                    print(f"⚠️  Warning: Could not delete original file: {e}")
            except Exception as e:
                print(f"⚠️  Encryption warning: {e}")

        finally:
            try:
                if os.path.exists(concat_path):
                    os.remove(concat_path)
            except Exception:
                pass
            try:
                if "video_only_path" in locals() and os.path.exists(video_only_path):
                    os.remove(video_only_path)
            except Exception:
                pass

            # Clean up temp frames.
            for p in frame_paths:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
            if audio_temp_path:
                try:
                    if os.path.exists(audio_temp_path):
                        os.remove(audio_temp_path)
                except Exception:
                    pass

    def infer_image(self, image_path: str, output_path: Optional[str] = None):
        """Run detection on an image file and optionally save the annotated result."""
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Unable to read image: {image_path}")

        detections = self.detect(image)
        annotated = self.annotate(image, detections)

        if output_path:
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            cv2.imwrite(output_path, annotated)

        return annotated, detections

    def infer_video(self, source: str = '0', output_path: Optional[str] = None):
        """Run detection on a video file or webcam source."""
        capture = cv2.VideoCapture(0 if source == '0' else source)
        if not capture.isOpened():
            raise ValueError(f"Unable to open video source: {source}")

        # Create videos folder in the AI directory
        ai_folder = os.path.dirname(os.path.abspath(__file__))
        video_folder = os.path.join(ai_folder, "videos")
        os.makedirs(video_folder, exist_ok=True)

        # Check audio availability
        audio_available = sd is not None and sf is not None
        ffmpeg_available = get_ffmpeg_executable() is not None
        if not audio_available:
            print("Warning: Audio recording not available. Install sounddevice and soundfile.")
        if not ffmpeg_available:
            print("Warning: ffmpeg not available. Install ffmpeg or imageio-ffmpeg for audio merging.")

        writer = None
        is_recording = False
        recording_start_time = None
        recording_filename = output_path
        video_temp_path = None
        audio_temp_path = None
        audio_recorder = None
        audio_offset = 0.0
        frame_dir = None
        frame_paths: List[str] = []
        frame_timestamps: List[float] = []

        frame_intervals = deque(maxlen=30)
        previous_frame_time = time.time()

        while True:
            current_time = time.time()
            interval = current_time - previous_frame_time
            if interval > 0:
                frame_intervals.append(interval)
            previous_frame_time = current_time

            ret, frame = capture.read()
            frame_capture_time = time.time()
            if not ret:
                break

            detections = self.detect(frame)
            annotated = self.annotate(frame, detections)

            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            person_percentage = self._get_person_frame_percentage(detections, height, width)
            person_large_enough = person_percentage > 25.0
            status_text = f"PERSON: {person_percentage:.1f}%" if person_percentage > 0 else "SEARCHING FOR PERSON"

            if person_large_enough and not is_recording:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                if not recording_filename:
                    recording_filename = os.path.join(
                        video_folder, f"recording_{timestamp}.mp4"
                    )
                video_temp_path = os.path.join(tempfile.gettempdir(), f"video_{timestamp}.mp4")
                audio_temp_path = os.path.join(tempfile.gettempdir(), f"audio_{timestamp}.wav")

                # Timestamped recording: write frames as images + real timestamps, then encode
                # a variable-frame-rate video. This avoids drift when inference slows frames.
                frame_dir = os.path.join(tempfile.gettempdir(), f"frames_{timestamp}")
                os.makedirs(frame_dir, exist_ok=True)
                frame_paths = []
                frame_timestamps = []
                writer = None

                if audio_available:
                    audio_recorder = AudioRecorder(audio_temp_path)
                    audio_recorder.start()
                    audio_offset = time.time() - frame_capture_time
                    print(f"Recording (timestamped). Audio: {audio_temp_path} (offset: {audio_offset:.3f}s)")
                else:
                    audio_offset = 0.0
                    print("Starting timestamped video recording without audio.")
                is_recording = True
                recording_start_time = time.time()
                status_text = f"RECORDING: {Path(recording_filename).name}"
                print(f"Person detected. Recording started: {recording_filename}")

            if is_recording and recording_start_time:
                elapsed = int(time.time() - recording_start_time)
                status_text = f"RECORDING ({elapsed}s)"

            if is_recording and frame_dir is not None:
                # Save annotated frames with wall-clock timestamps.
                frame_index = len(frame_paths)
                frame_path = os.path.join(frame_dir, f"frame_{frame_index:06d}.png")
                cv2.imwrite(frame_path, annotated)
                frame_paths.append(frame_path)
                frame_timestamps.append(time.time())

            if is_recording and recording_start_time and time.time() - recording_start_time > 30:
                is_recording = False
                self._finalize_recording_timestamped(
                    audio_recorder=audio_recorder,
                    frame_paths=frame_paths,
                    frame_timestamps=frame_timestamps,
                    audio_temp_path=audio_temp_path,
                    recording_filename=recording_filename,
                    audio_offset=audio_offset,
                )
                recording_filename = None
                video_temp_path = None
                audio_temp_path = None
                audio_recorder = None
                recording_start_time = None
                frame_dir = None
                frame_paths = []
                frame_timestamps = []
                status_text = "SEARCHING FOR PERSON"

            cv2.putText(
                annotated,
                status_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255) if is_recording else (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow('YOLO Object Detector', annotated)
            key = cv2.waitKey(1)
            if key == 27 or key == ord('q'):
                if is_recording:
                    print("Quitting while recording. Saving partial recording...")
                    self._finalize_recording_timestamped(
                        audio_recorder=audio_recorder,
                        frame_paths=frame_paths,
                        frame_timestamps=frame_timestamps,
                        audio_temp_path=audio_temp_path,
                        recording_filename=recording_filename,
                        audio_offset=audio_offset,
                    )
                    # Prevent double-stop/double-cleanup after leaving the loop.
                    is_recording = False
                    audio_recorder = None
                    recording_start_time = None
                    recording_filename = None
                    audio_temp_path = None
                    frame_dir = None
                    frame_paths = []
                    frame_timestamps = []
                break

        capture.release()
        if writer:
            writer.release()
        if audio_recorder:
            audio_recorder.stop()
            audio_recorder.join(timeout=5)
        cv2.destroyAllWindows()


def get_ffmpeg_executable() -> Optional[str]:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path
    if imageio_ffmpeg is not None:
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return None
    return None


def combine_video_audio(video_path: str, audio_path: str, output_path: str, duration: Optional[float] = None) -> None:
    ffmpeg_path = get_ffmpeg_executable()
    if not ffmpeg_path:
        raise RuntimeError(
            "ffmpeg not found. Install ffmpeg or install the Python package imageio-ffmpeg."
        )
    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        video_path,
        "-i",
        audio_path,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "44100",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-async",
        "1",
        "-shortest",
    ]
    if duration is not None:
        cmd.extend(["-t", str(duration)])
    cmd.append(output_path)
    subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


class AudioRecorder(threading.Thread):
    def __init__(self, file_path: str, samplerate: int = 44100, channels: int = 1):
        super().__init__(daemon=True)
        self.file_path = file_path
        self.samplerate = samplerate
        self.channels = channels
        self.frames: List[np.ndarray] = []
        self.stop_event = threading.Event()
        self.exception: Optional[Exception] = None
        self.start_time = time.time()

    def callback(self, indata, frames, time_info, status):
        if status:
            print(f"Audio status: {status}", flush=True)
        self.frames.append(indata.copy())
        if self.stop_event.is_set():
            raise sd.CallbackStop()

    def run(self):
        try:
            if sd is None or sf is None:
                raise RuntimeError(
                    "Install sounddevice and soundfile to enable audio recording."
                )
            # Use blocksize that matches video frame timing for better sync
            blocksize = self.samplerate // 30  # ~30fps equivalent audio blocks
            with sd.InputStream(samplerate=self.samplerate, channels=self.channels, callback=self.callback, blocksize=blocksize):
                while not self.stop_event.is_set():
                    sd.sleep(50)

            if self.frames:
                audio_data = np.concatenate(self.frames, axis=0)
            else:
                audio_data = np.empty((0, self.channels), dtype=np.float32)

            sf.write(self.file_path, audio_data, self.samplerate)
        except Exception as exc:
            self.exception = exc
            print(f"AudioRecorder error: {exc}", flush=True)

    def stop(self) -> None:
        self.stop_event.set()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='YOLO object detector')
    parser.add_argument('--model', type=str, default='yolov8n.pt', help='YOLO model path or name')
    parser.add_argument('--source', type=str, default='0', help='Image, video path, or webcam source (0 for webcam)')
    parser.add_argument('--output', type=str, default=None, help='Output image/video path for annotated results')
    parser.add_argument('--conf', type=float, default=0.25, help='Confidence threshold')
    parser.add_argument('--iou', type=float, default=0.45, help='IoU threshold')
    parser.add_argument('--imgsz', type=int, default=640, help='Image size for inference')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    detector = YOLOObjectDetector(
        model=args.model,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
    )

    if args.source == '0' or args.source.lower().startswith('http') or os.path.isfile(args.source):
        if args.source == '0':
            detector.infer_video(source='0', output_path=args.output)
        elif os.path.splitext(args.source)[1].lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}:
            annotated, detections = detector.infer_image(args.source, output_path=args.output)
            cv2.imshow('YOLO Object Detector', annotated)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        else:
            detector.infer_video(source=args.source, output_path=args.output)
    else:
        annotated, detections = detector.infer_image(args.source, output_path=args.output)
        cv2.imshow('YOLO Object Detector', annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()