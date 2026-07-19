"""
Complete test showing the full flow with varied hooks and product features.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generators.llm_generator import LLMGenerator
from utils.logging import create_session

def test_complete_flow():
    """Test complete flow: varied hooks + product features."""
    
    print("=" * 70)
    print("COMPLETE FLOW TEST: Varied Hooks + Product Features")
    print("=" * 70)
    
    session_id = "test_complete"
    create_session(session_id)
    llm = LLMGenerator(session_id)
    
    test_cases = [
        {
            "product": "Face Wash",
            "features": "vitamin C, natural herbs",
            "description": "Influencer holding face wash bottle"
        },
        {
            "product": "Wireless Earbuds",
            "features": "active noise cancellation, 8-hour battery",
            "description": "Influencer wearing earbuds"
        },
        {
            "product": "Protein Shake",
            "features": "25g protein, zero sugar, chocolate flavor",
            "description": "Influencer holding protein shake"
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}: {test['product']}")
        print(f"Features: {test['features']}")
        print("="*70)
        
        # Test with LLM (will fallback if API fails)
        result = llm.generate(
            user_description=test['description'],
            user_script=None,
            shot_type_pref="half_body",
            product_name=test['product'],
            product_features=test['features'],
            product_placement="in_hand",
            gender="female",
            body_type="normal",
            influencer_name="Aira"
        )
        
        script = result['video_script']
        words = len(script.split())
        
        # Extract hook (first sentence)
        hook = script.split('!')[0] + '!' if '!' in script else script.split('.')[0] + '.'
        
        print(f"\n📢 HOOK:")
        print(f"   {hook}")
        
        print(f"\n📝 FULL SCRIPT ({words} words):")
        print(f"   {script}")
        
        # Check if features are mentioned
        script_lower = script.lower()
        features_list = [f.strip().lower() for f in test['features'].split(',')]
        found_features = [f for f in features_list if f in script_lower]
        
        print(f"\n✅ FEATURES CHECK:")
        print(f"   Expected: {test['features']}")
        print(f"   Found: {', '.join(found_features) if found_features else 'None'}")
        
        if len(found_features) >= len(features_list) * 0.5:  # At least 50% of features
            print(f"   Status: ✅ PASS")
        else:
            print(f"   Status: ⚠️  Some features missing")
        
        print(f"\n🎬 MOTION PROMPT:")
        print(f"   {result['motion_prompt'][:80]}...")
        
        print(f"\n⏱️  DURATION: {result['duration']}s")
        print(f"💰 SHOT TYPE: {result['shot_type']}")
    
    print("\n" + "="*70)
    print("✅ COMPLETE FLOW TEST FINISHED")
    print("="*70)
    print("\nKEY OBSERVATIONS:")
    print("1. Each hook should be DIFFERENT (not all 'You guys, I finally found it!')")
    print("2. Product features should appear in the Demo section")
    print("3. Scripts should be 28-36 words (target 32)")
    print("4. Structure: Hook (8w) → Demo (16w) → Close (8w)")
    print("="*70)
    
    llm.cleanup()

if __name__ == "__main__":
    test_complete_flow()
