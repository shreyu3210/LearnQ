import numpy as np
import tritonclient.http as httpclient

# Configuration for your local Triton server
SERVER_URL = "localhost:8000"

def check_triton_server_status():
    """
    Checks if the Triton Inference Server is live and responsive.
    """
    try:
        client = httpclient.InferenceServerClient(url=SERVER_URL)
        if client.is_server_live():
            return {"status": "Triton server is online"}
        else:
            return {"status": "Triton server is offline"}
    except Exception as e:
        return {"status": "error", "message": f"Could not connect to Triton server: {e}"}


def test_all_models():
    """
    Connects to the Triton server and tests all three deployed models
    with dummy data to ensure they are responsive.
    Returns a dictionary with the status of each model.
    """
    # ... (the rest of this function stays the same) ...
    print("[DEBUG] Starting test_all_models()")
    results = {}
    
    print("[DEBUG] Attempting to create InferenceServerClient with timeout...")
    try:
        client = httpclient.InferenceServerClient(url=SERVER_URL, connection_timeout=5.0)
        print("[DEBUG] InferenceServerClient created successfully")
    except Exception as e:
        print(f"[DEBUG] Failed to create client: {e}")
        return {"error": f"Could not connect to Triton server: {e}"}

    # # 1. Test Frame Classifier
    print("[DEBUG] Testing frame_classifier model with correct dummy data...")
    try:
        dummy_image = np.random.rand(1, 3, 224, 224).astype(np.float32)
        tensor = httpclient.InferInput("input", dummy_image.shape, "FP32")
        tensor.set_data_from_numpy(dummy_image, binary_data=True)
        client.infer(model_name="frame_classifier", inputs=[tensor])
        results["frame_classifier"] = "OK"
        print("[DEBUG] frame_classifier test passed")
    except Exception as e:
        print(f"[DEBUG] frame_classifier test failed: {e}")
        results["frame_classifier"] = f"FAILED: {e}"

    # 2. Test Whisper Encoder
    print("[DEBUG] Testing whisper_encoder model with correct dummy data...")
    encoder_output = None
    try:
        dummy_audio = np.random.rand(1, 80, 3000).astype(np.float32)
        tensor = httpclient.InferInput("input_features", dummy_audio.shape, "FP32")
        tensor.set_data_from_numpy(dummy_audio, binary_data=True)
        response = client.infer(model_name="whisper_encoder", inputs=[tensor])
        encoder_output = response.as_numpy("last_hidden_state")
        results["whisper_encoder"] = "OK"
        print("[DEBUG] whisper_encoder test passed")
    except Exception as e:
        print(f"[DEBUG] whisper_encoder test failed: {e}")
        results["whisper_encoder"] = f"FAILED: {e}"

    # 3. Test Whisper Decoder
    print("[DEBUG] Testing whisper_decoder model...")
    if encoder_output is not None:
        try:
            dummy_tokens = np.random.randint(0, 50000, size=(1, 10), dtype=np.int64)
            tokens_tensor = httpclient.InferInput("input_ids", dummy_tokens.shape, "INT64")
            tokens_tensor.set_data_from_numpy(dummy_tokens, binary_data=True)
            
            encoder_tensor = httpclient.InferInput("encoder_hidden_states", encoder_output.shape, "FP32")
            encoder_tensor.set_data_from_numpy(encoder_output, binary_data=True)
            
            client.infer(model_name="whisper_decoder", inputs=[tokens_tensor, encoder_tensor])
            results["whisper_decoder"] = "OK"
            print("[DEBUG] whisper_decoder test passed")
        except Exception as e:
            print(f"[DEBUG] whisper_decoder test failed: {e}")
            results["whisper_decoder"] = f"FAILED: {e}"
    else:
        print("[DEBUG] Skipping whisper_decoder test (no encoder output)")
            
    print(f"[DEBUG] test_all_models() completed with results: {results}")
    return results