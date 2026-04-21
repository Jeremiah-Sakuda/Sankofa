#!/usr/bin/env python3
"""
Capture a narrative session to use as the sample.

Usage:
    python scripts/capture_sample.py --api-url https://YOUR_BACKEND_URL

Or to use an existing session:
    python scripts/capture_sample.py --api-url https://YOUR_BACKEND_URL --session-id abc-123

The script will save the result to backend/app/data/sample_narrative.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

# Default sample input - customize as needed
DEFAULT_INPUT = {
    "family_name": "Asante",
    "region_of_origin": "Ghana, West Africa",
    "time_period": "1920s",
    "known_fragments": "Gold Coast traders, Ashanti kingdom",
    "language_or_ethnicity": "Akan",
    "specific_interests": "Traditional crafts and trade routes",
}


def create_session(api_url: str, user_input: dict) -> str:
    """Create a new session via the intake endpoint."""
    print(f"Creating session with input: {user_input['family_name']} from {user_input['region_of_origin']}")

    resp = requests.post(
        f"{api_url}/api/intake",
        json=user_input,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    session_id = data["session_id"]
    print(f"Session created: {session_id}")
    return session_id


def stream_narrative(api_url: str, session_id: str, audio: bool = True) -> None:
    """Stream the narrative generation (blocking until complete)."""
    print(f"Starting narrative generation (audio={audio})...")
    print("This may take 1-3 minutes...")

    url = f"{api_url}/api/narrative/{session_id}/stream?audio={str(audio).lower()}"

    with requests.get(url, stream=True, timeout=600) as resp:
        resp.raise_for_status()

        for line in resp.iter_lines():
            if not line:
                continue

            line_str = line.decode("utf-8")

            if line_str.startswith("event:"):
                event_type = line_str[6:].strip()
                if event_type == "status":
                    continue
                print(f"  Received: {event_type}")

            elif line_str.startswith("data:"):
                try:
                    data = json.loads(line_str[5:])
                    if isinstance(data, dict):
                        if data.get("status") == "complete":
                            print("Generation complete!")
                            return
                        elif data.get("status"):
                            print(f"  Status: {data['status']}")
                        elif data.get("error"):
                            print(f"  ERROR: {data['error']}")
                            sys.exit(1)
                except json.JSONDecodeError:
                    pass


def fetch_session(api_url: str, session_id: str) -> dict:
    """Fetch the full session data including segments."""
    print(f"Fetching session data...")

    resp = requests.get(
        f"{api_url}/api/session/{session_id}?include_segments=true",
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def save_sample(data: dict, output_path: Path, strip_audio: bool = False) -> None:
    """Save the session data as the sample narrative."""

    if strip_audio:
        print("Stripping audio segments to reduce file size...")
        original_count = len(data.get("segments", []))
        data["segments"] = [
            seg for seg in data.get("segments", [])
            if seg.get("type") != "audio"
        ]
        removed = original_count - len(data["segments"])
        print(f"  Removed {removed} audio segments")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Saved to {output_path} ({size_mb:.2f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Capture a narrative session for the sample")
    parser.add_argument("--api-url", required=True, help="Backend API URL (e.g., https://sankofa-xxx.run.app)")
    parser.add_argument("--session-id", help="Use existing session ID instead of creating new")
    parser.add_argument("--no-audio", action="store_true", help="Skip audio generation")
    parser.add_argument("--strip-audio", action="store_true", help="Remove audio from saved file")
    parser.add_argument("--output", default="backend/app/data/sample_narrative.json", help="Output path")
    parser.add_argument("--input-json", help="Path to JSON file with custom user input")

    args = parser.parse_args()

    # Determine user input
    if args.input_json:
        with open(args.input_json) as f:
            user_input = json.load(f)
    else:
        user_input = DEFAULT_INPUT

    api_url = args.api_url.rstrip("/")

    # Create or use existing session
    if args.session_id:
        session_id = args.session_id
        print(f"Using existing session: {session_id}")
    else:
        session_id = create_session(api_url, user_input)
        stream_narrative(api_url, session_id, audio=not args.no_audio)

    # Fetch and save
    session_data = fetch_session(api_url, session_id)

    # Add session_id to the data (it's not included in the response)
    session_data["session_id"] = session_id

    output_path = Path(args.output)
    save_sample(session_data, output_path, strip_audio=args.strip_audio)

    print("\nDone! To use this sample:")
    print(f"  1. Review the file at {output_path}")
    print("  2. Commit and push to deploy")


if __name__ == "__main__":
    main()
