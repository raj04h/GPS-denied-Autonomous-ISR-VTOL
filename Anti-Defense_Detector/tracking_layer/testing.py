import cv2
 
# Open the video file
cap = cv2.VideoCapture("asset/drone_testing.mp4"
)
 
# Check if the video was opened successfully
if not cap.isOpened():
    print("Error: Could not open video file.")
else:
    print("Video file opened successfully!")
 
# Read the first frame to confirm reading
ret, frame = cap.read()
 
if ret:
 
    # Display the frame using imshow
    cv2.imshow("First Frame", frame)
    cv2.waitKey(0)  # Wait for a key press to close the window
    cv2.destroyAllWindows()  # Close the window
else:
    print("Error: Could not read the frame.")
 
# Release the video capture object
cap.release()