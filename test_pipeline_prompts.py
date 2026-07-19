import os
import sys
import json
from unittest.mock import patch

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generators.llm_generator import LLMGenerator
from clients.flux_client import FluxKontextClient
from clients.kling_client import KlingClient
from utils import create_session

def run_test():
    session_id = "test_pipeline_prompts_001"
    create_session(session_id)
    
    print("=" * 80)
    print("🚀 PIPELINE PROMPT TEST (15s Kling O3 Pro + Flux Max)")
    print("=" * 80)
    
    print("\n[PHASE 0: LLM GENERATOR]")
    llm = LLMGenerator(session_id)
    result = llm.generate(
        user_description="A fitness influencer showing off a new protein powder bottle.",
        product_name="PowerWhey",
        product_features="30g protein, zero sugar, chocolate flavor",
        product_placement="in_hand",
        gender="female",
        body_type="athletic",
        influencer_name="Aira"
    )
    
    print(f"✓ Target Video Duration : 15s")
    print(f"✓ Shot Type             : {result.get('shot_type')}")
    print(f"✓ Voice Tone            : {result.get('voice_tone')}")
    print(f"✓ Script Length         : {len(result.get('video_script', '').split())} words")
    
    print("\n[PHASE 1: FLUX KONTEXT MAX (Image Gen) Inputs]")
    print("Intercepting API call via mock...")
    
    flux_client = FluxKontextClient(session_id)
    from config.settings import SHOT_TYPE_CONFIGS
    shot_config = SHOT_TYPE_CONFIGS.get(result.get("shot_type", "half_body"))
    
    # We want to test a 16:9 landscape aspect ratio to verify dimensions work
    test_aspect_ratio = "16:9"
    print(f"Testing with UI Aspect Ratio: {test_aspect_ratio}")
    
    with patch('fal_client.submit') as mock_submit:
        # Mock the handler.get() response
        mock_handler = mock_submit.return_value
        mock_handler.get.return_value = {"images": [{"url": "mock_flux_url.jpg", "width": 1344, "height": 768}]}
        
        # We catch exceptions about file downloads since this is a mock
        try:
            flux_client.generate(
                flux_prompt=result.get("flux_prompt"),
                shot_config=shot_config,
                product_image_path=None,
                product_placement=result.get("product_placement"),
                reference_image_path="dummy.jpg",  # won't be read because image_to_data_uri will fail gracefully or we mock it
                gender=result.get("gender"),
                body_type=result.get("body_type"),
                aspect_ratio=test_aspect_ratio
            )
        except Exception:
            pass # ignore download errors, we just want to see the submit call
            
        if mock_submit.called:
            print("The following kwargs were actually sent to fal_client.submit for FLUX:")
            print(json.dumps(mock_submit.call_args.kwargs.get("arguments", {}), indent=2))
        else:
            print("Error: fal_client.submit was not called for Flux.")


    print("\n[PHASE 2: KLING O3 PRO (Video Gen) Inputs]")
    print("Intercepting API call via mock...")
    
    kling_client = KlingClient(session_id)
    
    with patch('fal_client.submit') as mock_submit:
        mock_handler = mock_submit.return_value
        mock_handler.get.return_value = {"video": {"url": "mock_kling_url.mp4"}}
        
        try:
            kling_client.generate(
                image_url="mock_flux_url.jpg",
                motion_prompt=result.get("motion_prompt"),
                video_script=result.get("video_script"),
                duration=15,
                voice_tone=result.get("voice_tone"),
                aspect_ratio=test_aspect_ratio,
                voice_language="en"
            )
        except Exception:
            pass # ignore download errors
            
        if mock_submit.called:
            print("The following kwargs were actually sent to fal_client.submit for KLING:")
            kling_args = mock_submit.call_args.kwargs.get("arguments", {})
            print(json.dumps(kling_args, indent=2))
            
            # Highlight the Kling bracket syntax
            print("\n👀 Notice the 'prompt' field above uses the [Subject, tone]: syntax!")
        else:
            print("Error: fal_client.submit was not called for Kling.")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    run_test()
