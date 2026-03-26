import subprocess
import random
import sys

CHANNELS = [
    "https://youtube.com/@natebjones",
    "https://youtube.com/@mreflow",
    "https://youtube.com/@aiexplained-official",
    "https://youtube.com/@MatthewBerman",
    "https://youtube.com/@Fireship",
    "https://youtube.com/@DavidShapiroAutomator",
    "https://youtube.com/@WesRoth",
    "https://youtube.com/@AIAdvantage"
]

def main():
    email = "luv2worship@gmail.com"
    max_vids = "3"
    
    # Randomly pick 2 channels to check
    selected = random.sample(CHANNELS, 2)
    print(f"Selected channels for today: {selected}")
    
    for ch in selected:
        print(f"Running digest for {ch}...")
        cmd = [
            "python3", 
            "/home/ec2-user/.openclaw/workspace/features/youtube-agent-setup/scripts/channel_daily_digest.py",
            "--channel", ch,
            "--email-to", email,
            "--max-videos", max_vids
        ]
        result = subprocess.run(cmd, text=True, capture_output=True)
        print(result.stdout)
        if result.returncode != 0:
            print(f"Error: {result.stderr}", file=sys.stderr)

if __name__ == "__main__":
    main()
