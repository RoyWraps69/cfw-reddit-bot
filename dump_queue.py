#!/usr/bin/env python3
"""Dump the content queue to stdout for inspection."""
import json, os

QUEUE_FILE = os.path.join(os.path.dirname(__file__), "data", "content_queue", "queue.json")

if not os.path.exists(QUEUE_FILE):
    print("Queue file not found!")
else:
    queue = json.load(open(QUEUE_FILE))
    print(f"\n{'='*70}")
    print(f"  CONTENT QUEUE: {len(queue)} posts ready")
    print(f"{'='*70}\n")
    for i, post in enumerate(queue, 1):
        decision = post.get("decision", {})
        captions = post.get("captions", post.get("platforms", {}))
        fb_cap = ""
        ig_cap = ""
        # Try different caption structures
        if isinstance(captions, dict):
            fb_data = captions.get("facebook", {})
            ig_data = captions.get("instagram", {})
            if isinstance(fb_data, dict):
                fb_cap = fb_data.get("caption", "")
            elif isinstance(fb_data, str):
                fb_cap = fb_data
            if isinstance(ig_data, dict):
                ig_cap = ig_data.get("caption", "")
            elif isinstance(ig_data, str):
                ig_cap = ig_data
        
        print(f"--- POST {i} ---")
        print(f"Topic: {decision.get('topic', 'N/A')}")
        print(f"Audience: {decision.get('audience', 'N/A')}")
        print(f"Image: {'YES' if post.get('image_path') else 'NO'}")
        print(f"Video: {'YES' if post.get('video_path') else 'NO'}")
        print(f"Queued: {post.get('queued_at', 'N/A')}")
        print(f"\nFACEBOOK CAPTION:")
        print(fb_cap[:500] if fb_cap else "(empty)")
        print(f"\nINSTAGRAM CAPTION:")
        print(ig_cap[:500] if ig_cap else "(empty)")
        print(f"\n{'='*70}\n")
