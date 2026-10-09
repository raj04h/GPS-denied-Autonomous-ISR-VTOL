# Dependencies

import csv
import os
import time
import statistics

import psutil

# Configuration

RESULT_DIRECTORY = "benchmark/results"


# Core Logic
class Benchmark:

    def __init__(self):

        self.latencies = []

        self.processed_frames = 0

        self.success_frames = 0

        self.lost_frames = 0

        self.start_time = None

        self.end_time = None

        self.process = psutil.Process(os.getpid())

        self.cpu_start = 0.0

        self.cpu_end = 0.0

    def start(self):

        self.latencies = []

        self.processed_frames = 0

        self.success_frames = 0

        self.lost_frames = 0

        self.cpu_start = self.process.cpu_percent(interval=None)

        self.start_time = time.perf_counter()

    def record_frame(self, latency_ms, success):

        self.latencies.append(latency_ms)

        self.processed_frames += 1

        if success:

            self.success_frames += 1

        else:

            self.lost_frames += 1

    def stop(self):

        self.end_time = time.perf_counter()

        self.cpu_end = self.process.cpu_percent(interval=None)

    def calculate_results(self):

        if self.processed_frames == 0:

            raise RuntimeError("No frames were recorded.")

        duration = self.end_time - self.start_time

        average_fps = self.processed_frames / duration

        average_latency = statistics.mean(self.latencies)

        minimum_latency = min(self.latencies)

        maximum_latency = max(self.latencies)

        success_rate = (self.success_frames / self.processed_frames) * 100.0

        cpu_usage = (self.cpu_start + self.cpu_end) / 2.0

        memory_usage = self.process.memory_info().rss / (1024 * 1024)

        return {
            "frames_processed": self.processed_frames,
            "duration_sec": duration,
            "average_fps": average_fps,
            "average_latency_ms": average_latency,
            "min_latency_ms": minimum_latency,
            "max_latency_ms": maximum_latency,
            "tracking_success_frames": self.success_frames,
            "tracking_lost_frames": self.lost_frames,
            "tracking_success_rate": success_rate,
            "cpu_usage_percent": cpu_usage,
            "memory_usage_mb": memory_usage,
        }

    def save_results(self, results, filename):

        os.makedirs(RESULT_DIRECTORY, exist_ok=True)

        filepath = os.path.join(RESULT_DIRECTORY, filename)

        file_exists = os.path.exists(filepath)

        with open(filepath, "a", newline="") as file:

            writer = csv.DictWriter(file, fieldnames=results.keys())

            if not file_exists:

                writer.writeheader()

            writer.writerow(results)

        return filepath

    def print_results(self, results):

        print()
        print("           BENCHMARK RESULTS")

        print(f"Frames processed : " f"{results['frames_processed']}")

        print(f"Duration         : " f"{results['duration_sec']:.3f} sec")

        print(f"Average FPS      : " f"{results['average_fps']:.2f}")

        print(f"Average latency  : " f"{results['average_latency_ms']:.3f} ms")

        print(f"Minimum latency  : " f"{results['min_latency_ms']:.3f} ms")

        print(f"Maximum latency  : " f"{results['max_latency_ms']:.3f} ms")

        print(f"Success frames   : " f"{results['tracking_success_frames']}")

        print(f"Lost frames      : " f"{results['tracking_lost_frames']}")

        print(f"Success rate     : " f"{results['tracking_success_rate']:.2f}%")

        print(f"CPU usage        : " f"{results['cpu_usage_percent']:.2f}%")

        print(f"Memory usage     : " f"{results['memory_usage_mb']:.2f} MB")

