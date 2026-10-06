import streamlit as st
import requests
import matplotlib.pyplot as plt
import base64
import numpy as np
import cv2

# D:/Program_file/Anaconda/Scripts/activate
# conda activate MyEnv
# D:/Program_file/Anaconda/envs/MyEnv/python.exe -m streamlit run d:/Deep_Project/Marine_ISR/stram_dash.py   
# "wide" layout uses full browser width.
st.set_page_config(layout="wide")

st.title("🛰 Marine AI Guard")
st.subheader("On-Orbit Marine Activity Detector")

st.markdown("---")

uploaded_file = st.file_uploader(
    "Upload SAR Image",
    type=["jpg", "png", "jpeg"]
)

# Main Logic Executes Only If File Is Uploaded
if uploaded_file is not None:

    # seperating Screen into 2 parts by column.
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Raw Image") # reading input image
        st.image(uploaded_file, use_column_width=True)

    # Send Image to Backend (FastAPI)
    try:
        files = {"file":(uploaded_file.name,
        uploaded_file.getvalue(),
        uploaded_file.type)}

        response = requests.post("http://127.0.0.1:8000/detect/", files=files)

        if response.status_code == 200:
            result = response.json()

            # Decode annotated image
            img_data = base64.b64decode(result["annotated_image"])
            np_arr = np.frombuffer(img_data, np.uint8)
            annotated_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            with col2:
                st.subheader("Detected Ships (Annotated)")
                st.image(annotated_img, use_column_width=True)

            st.markdown("---")
            st.subheader("Edge Inference Metrics")

            # Display Performance Metrics
            m1, m2, m3 = st.columns(3)


            # Metrics visualize
            m1.metric("Inference Time (ms)", result["inference_time_ms"])
            m2.metric("Raw Image Size (MB)", result["raw_image_MB"])
            m3.metric("Bandwidth Saved (%)", result["bandwidth_saved_percent"])

            st.markdown("---")
            st.subheader("Bandwidth Comparison")

            raw_size = result["raw_image_MB"]
            metadata_size = result["metadata_KB"] / 1024

            # Create Bar Chart
            fig = plt.figure()
            plt.bar(
                ["Raw Image (MB)", "Metadata (MB)"],
                [raw_size, metadata_size]
            )
            plt.ylabel("Size (MB)")
            plt.title("Satellite-to-Ground Bandwidth Reduction")
            st.pyplot(fig)

            st.markdown("---")
            st.subheader("Actionable Metadata Transmitted")
            st.json(result["detections"])

        else:
            # Backend responded but returned error
            st.error(f"Backend Error {response.status_code}")
            st.write(response.text)
            
    # Backend unreachable or network issue
    except Exception:
        st.error("Cannot connect to backend.")
        st.write("Ensure Server is running at http://127.0.0.1:8000")