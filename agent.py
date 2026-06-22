import json
import subprocess
import anthropic
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
MATCH_FILE = PROJECT_DIR / "match.json"
SKETCH_FILE = PROJECT_DIR / "Main1"  # update this path to your actual .ino file

def run_agent(match_data: str):
    # read the current .ino file
    try:
        with open(SKETCH_FILE, "r") as f:
            sketch = f.read()
    except FileNotFoundError:
        print(f"Error: could not find sketch at {SKETCH_FILE}")
        return

    client = anthropic.Anthropic()  # automatically uses ANTHROPIC_API_KEY env variable

    prompt = f"""
You are updating my Arduino World Cup goal tracker.

Here is the match data:

{match_data}

The JSON format is:
- "league": "World Cup"
- "team1": first team name
- "team2": second team name
- "score1": team1 final score
- "score2": team2 final score
- "goals": list of goal events
- each goal has:
  - "team": 1 if team1 scored, 2 if team2 scored
  - "minute": match minute when the goal happened

Here is the current Arduino sketch:

{sketch}

Rules:
- ONLY change C++ code that matches this format:
    float t[] = {{2.5, 7.0, 14.5}};
    int scorer[] = {{1, 2, 1}};
    int c1[] = {{255, 0, 0}};
    int c2[] = {{0, 0, 255}};
    String country1 = "Brazil";
    String country2 = "Argentina";
    int a1 = 1;   // 001.mp3
    int a2 = 2;   // 002.mp3
- Use team indexes 1 and 2 exactly as given in the JSON.
- Map goal minutes from 0-90 linearly onto Arduino playback time from 0-18 seconds.
- Formula: Arduino time = (minute / 90) * 18. Round to nearest 0.5 second.
- Goal times must be floats in the t[] array.
- scorer[] must be the same length as t[]. Each index refers to the same goal. Pull "team" from each goal in order.
- For c1 and c2, assign the most visually dominant RGB color from each country's national flag. Format: {{R, G, B}}. If unclear, use {{0, 0, 0}}.
- Update country1 and country2 strings to match team names from the JSON.
- a1 and a2 map to audio files. Assign each a unique random number between 1 and 48, no repeats. Update the // 00#.mp3 comments.
- Do not invent goals.
- Do not change unrelated code.
- Do not change variable names, only their values.
- Output ONLY the complete updated sketch, no explanation.
"""

    message = client.messages.create(
        model="claude-haiku-4-5",  # cheapest model, plenty good for this task
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    updated_sketch = message.content[0].text

    # write the updated sketch back to the file
    with open(SKETCH_FILE, "w") as f:
        f.write(updated_sketch)

    print("Sketch updated successfully!")

def git(cmd):
    subprocess.run(cmd, cwd=PROJECT_DIR, check=True)

def setup_branch():
    git(["git", "checkout", "test-branch"])
    git(["git", "pull", "origin", "test-branch"])

    result = subprocess.run(
        ["git", "branch", "--list", "api-score-update"],
        cwd=PROJECT_DIR, capture_output=True, text=True
    )

    if "api-score-update" in result.stdout:
        git(["git", "checkout", "api-score-update"])
    else:
        git(["git", "checkout", "-b", "api-score-update"])

def main():
    git(["git", "config", "user.email", "arduino-bot@noreply"])
    git(["git", "config", "user.name", "arduino-bot"])

    try:
        with open(MATCH_FILE, "r") as f:
            match = json.load(f)
    except FileNotFoundError:
        print("Error: match.json not found.")
        return
    except json.JSONDecodeError:
        print("Error: match.json is not valid JSON.")
        return

    match_data = json.dumps(match, indent=2)
    setup_branch()

    try:
        run_agent(match_data)
    except Exception as e:
        print(f"Agent failed: {e}")
        return

    git(["git", "add", "."])
    git(["git", "commit", "-m", "Update Arduino goal timings"])
    git(["git", "push", "origin", "api-score-update"])
    print("Done! Pushed to api-score-update branch.")

if __name__ == "__main__":
    main()