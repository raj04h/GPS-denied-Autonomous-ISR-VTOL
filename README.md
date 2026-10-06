# Maritime Surveillance Platform: AI-Enabled ISR System

## Working Demo Video
[![Watch the video](https://img.youtube.com/vi/XuEhmXikd80/0.jpg)](https://youtu.be/XuEhmXikd80)





Summery

Marine Intelligence Guard is an end-to-end, downstream intelligence system designed to solve the "Satellite-to-Ground Bottleneck."

By simulating onboard edge intelligence, this system processes high-volume Synthetic Aperture Radar (SAR) imagery to detect maritime vessels in real-time, transmitting only actionable metadata to ground stations.

Key Engineering Impact:

* 99% Data Reduction: Successfully reduced downlink payload by transmitting JSON metadata instead of raw, high-resolution imagery.
* Production-Ready API: Developed a modular FastAPI inference engine for seamless integration into satellite ground-segment workflows.
* Real-Time Latency Mitigation: Addresses the critical 100+ GB/day bandwidth constraint inherent in modern SAR constellations.

# Software Architecture & Systems Design

Technical StackBackend: 
* FastAPI (Inference Engine) for high-performance, asynchronous processing.
* Frontend: Streamlit-based Ground Control Dashboard for real-time visualization.
* Image Processing: OpenCV for pre-processing and Base64-encoded visualization layers.
* Deployment: Designed for ONNX format compatibility to ensure high-speed execution on Edge devices.

# Computer Vision Pipeline
Detection Workflow
* Ingestion: Satellite SAR image capture (simulated 10–50 MB per image). 
* Inference: YOLOv8 detects ships even in high-noise environments. 
* Extraction: The system extracts bounding box coordinates and confidence scores.
* Transmission: Only a lightweight JSON payload is downlinked to the ground station.

# Space-Tech Applications
* National Security: Unauthorized entry detection and coastal monitoring.
* Environmental Monitoring: Surface mining expansion and flood impact assessment.
* Logistics: Port congestion monitoring and risk estimation for shipping corridors.

# Limitations & Future Roadmap
* Geospatial Precision: Currently focuses on bounding box detection; future iterations will integrate rasterio for precise orbit-based pixel-to-Lat/Long mapping.
* Temporal Analytics: Plans to implement multi-temporal change detection for vessel trajectory estimation and behavioral anomaly modeling.
* Environmental Robustness: Further training is required for extremely high sea clutter and heavy storm conditions.

Result Graph

<img width="1035" height="518" alt="image" src="https://github.com/user-attachments/assets/33f512b7-cfe4-4ca4-8102-c832612f0ae9" />


Model Testing

<img width="729" height="344" alt="image" src="https://github.com/user-attachments/assets/460cd547-d83c-477c-a96d-4706b732079c" />


FastAPI Backend

<img width="591" height="375" alt="image" src="https://github.com/user-attachments/assets/82c8b4e4-dc65-455a-9b3b-f2e99e4ea8bf" />


Predicted Result

<img width="414" height="375" alt="image" src="https://github.com/user-attachments/assets/2022ea66-f2e5-4977-abac-45c1d532484a" />


# Author: Himanshu Raj
© 2026, All rights reserved.
