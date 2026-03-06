import ollama
import cv2
import base64
import os

class VisionService:
    def __init__(self, model="qwen3-vl:2b"):
        self.model = model

    def analyze(self, frame):
        if frame is None:
            return None

        # Convert the frame to base64 for Ollama
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')

        # Precise prompt to get structured-like output from a small VLM
        prompt = (
            "Describe the scene for a child's educational companion. "
            "Identify: 1. Is a child present? 2. What objects is the child holding or looking at? "
            "3. What is the overall mood or activity? "
            "Keep the description concise and factual."
        )

        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                images=[frame_base64],
                stream=False
            )
            return response['response']
        except Exception as e:
            print(f"Vision analysis error: {e}")
            return None

if __name__ == "__main__":
    # Test with the saved frame from camera_service test
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_image_path = os.path.join(project_root, "data/test_capture.jpg")
    
    if os.path.exists(test_image_path):
        print(f"Testing vision with {test_image_path}...")
        frame = cv2.imread(test_image_path)
        vision = VisionService()
        result = vision.analyze(frame)
        print("--- Vision Result ---")
        print(result)
    else:
        print("No test_capture.jpg found. Run camera_service.py first.")
