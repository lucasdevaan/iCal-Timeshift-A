import requests
from icalendar import Calendar, Event
from datetime import datetime, timedelta, timezone
import pytz
import os

# The URL of the iCal file to fetch.
# NOTE: The token in this URL is hardcoded. If it's a sensitive token,
# consider using GitHub Secrets to store it securely.
URL = os.environ.get("ICAL_URL")

# --- Main Logic ---
def main():
    try:
        # Fetch the iCal file from the URL with a 15-second timeout
        print(f"Fetching iCal from {URL}...")
        resp = requests.get(URL, timeout=15)
        resp.raise_for_status()  # This will raise an HTTPError for bad responses (4xx or 5xx)

        # A more robust method to clean the text content.
        # It handles hidden characters and line-ending issues by rebuilding
        # the text content from clean, stripped lines.
        lines = resp.text.splitlines()
        clean_lines = [line.strip().replace('\xa0', '') for line in lines]
        clean_text = '\n'.join(clean_lines)

        # Parse the original calendar from the cleaned text
        cal = Calendar.from_ical(clean_text)
        new_cal = Calendar()

        # Copy calendar metadata (like timezone info, etc.)
        for k, v in cal.items():
            new_cal.add(k, v)

        print("Processing events and adjusting times...")
        events = list(cal.walk("VEVENT"))
        print(f"Found {len(events)} events to process.")

        # Set the local timezone for calculations
        tz = pytz.timezone("Europe/Amsterdam")

        for component in events:
            # Check if DTSTART and DTEND exist before trying to access them
            if 'DTSTART' not in component or 'DTEND' not in component:
                uid = component.get("UID", "N/A")
                print(f"Skipping event with UID '{uid}' because it's missing DTSTART or DTEND.")
                continue

            start_utc = component.decoded("DTSTART")
            end_utc = component.decoded("DTEND")

            # Convert to Amsterdam time for correct shift adjustment logic
            start_local = start_utc.astimezone(tz)
            end_local = end_utc.astimezone(tz)

            # Check if it's a morning or afternoon shift based on the original local time
            # and adjust to the desired times (e.g., 9:00-13:00)
            if start_local.hour == 8 and start_local.minute == 45:  # Morning shift
                start_local = start_local.replace(hour=9, minute=0)
                end_local = end_local.replace(hour=13, minute=0)
            elif start_local.hour == 13 and start_local.minute == 45:  # Afternoon shift
                start_local = start_local.replace(hour=13, minute=0)
                end_local = end_local.replace(hour=17, minute=0)

            # Convert the new, adjusted local times back to UTC
            new_start_utc = start_local.astimezone(timezone.utc)
            new_end_utc = end_local.astimezone(timezone.utc)

            # Rebuild the same event, only changing times
            new_event = Event()
            for k, v in component.items():
                if k not in ("DTSTART", "DTEND"):
                    new_event.add(k, v)
            new_event.add("DTSTART", new_start_utc)
            new_event.add("DTEND", new_end_utc)

            new_cal.add_component(new_event)
            print(f"Shift {component.get('UID')} adjusted to: {start_local.strftime('%H:%M')} - {end_local.strftime('%H:%M')} (Local Time)")

        # Ensure the 'docs' directory exists
        os.makedirs("docs", exist_ok=True)
        
        # Save the new iCal file
        output_file_path = "docs/fixed_shifts.ics"
        with open(output_file_path, "wb") as f:
            f.write(new_cal.to_ical())
        print(f"New iCal file saved to {output_file_path}")

        # Create a .nojekyll file to ensure GitHub Pages serves the file as-is
        # without trying to process it with Jekyll.
        nojekyll_path = "docs/.nojekyll"
        with open(nojekyll_path, "w") as f:
            f.write("")
        print(f"Created {nojekyll_path} for GitHub Pages.")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the iCal file: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise

if __name__ == "__main__":
    main()
