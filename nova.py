from controller import handle_command, get_logger, execute_confirmed_action, cancel_confirmed_action, execute_confirmed_step
import json
import subprocess


def speak(text):
    try:
        subprocess.run(["say", text])
    except Exception as e:
        print(f"[Voice Error]: {e}")


def show_logs():
    """Display the last 5 execution records."""
    logger = get_logger()
    logs = logger.get_recent_logs(5)

    if not logs:
        print("No execution logs found.")
        return

    print("\n" + "=" * 50)
    print("  RECENT EXECUTION LOGS")
    print("=" * 50)

    for log in logs:
        log_id, timestamp, command, intent, domain, action, risk, status, summary = log
        print(f"\n  [{log_id}] {timestamp}")
        print(f"  Command : {command}")
        print(f"  Intent  : {intent}  |  Domain: {domain}")
        print(f"  Action  : {action}")
        print(f"  Risk    : {risk}  |  Status: {status}")
        print(f"  Response: {summary[:100]}{'...' if len(summary) > 100 else ''}")
        print("-" * 50)


def handle_confirmation(command, result):
    """Handle yes/no confirmation for high-risk actions."""
    # Print action description without the "Confirm?" suffix
    msg = result['response'].replace("Confirm? (yes/no)", "").strip()
    print(f"\n⚠  {msg}")

    # Show completed steps if this is a multi-step pause
    prior = result.get("step_results", [])
    if prior:
        print(f"\n  Completed {len(prior)} step(s) before this:")
        for j, r in enumerate(prior):
            print(f"    Step {j + 1}: [{r['status']}] {r['response'][:80]}")

    # Flush any stray input left in terminal buffer
    import sys
    import termios
    termios.tcflush(sys.stdin, termios.TCIFLUSH)

    while True:
        confirm = input("Confirm? (yes/no) > ").strip().lower()

        if confirm == "yes":
            print("[NOVA] Executing confirmed action...")
            if result.get("confirm_type") == "multi_step":
                response = execute_confirmed_step(command, result)
            else:
                response = execute_confirmed_action(command, result)
            print(response)
            speak(response)
            return
        elif confirm == "no":
            print("[NOVA] Action cancelled.")
            cancel_confirmed_action(command, result)
            speak("Action cancelled.")
            return
        elif confirm == "":
            continue  # Ignore empty input
        else:
            print("[NOVA] Please type 'yes' or 'no'.")


def main():
    print("=" * 50)
    print("  NOVA online.")
    print("=" * 50)

    try:
        while True:
            print("\n" + "-" * 50)
            command = input("NOVA > ")

            # Handle special CLI commands
            if command.strip().lower() == "show logs":
                show_logs()
                continue

            result = handle_command(command)

            print("\n--- STRUCTURED PLAN ---")
            print(json.dumps(result, indent=2))
            print("--- END PLAN ---\n")

            # Check if confirmation is required
            if result.get("requires_confirmation"):
                handle_confirmation(command, result)
                continue

            # Display per-step results for multi-step commands
            step_results = result.get("step_results")
            if step_results:
                print(f"\n  [{len(step_results)} step(s) executed]")
                for j, r in enumerate(step_results):
                    status_icon = "✓" if r["status"] == "success" else "✗"
                    print(f"    {status_icon} Step {j + 1} [{r['domain']}/{r['action']}]: {r['response'][:100]}")

            final_response = result["response"]
            print(final_response)
            speak(final_response)
    except KeyboardInterrupt:
        print("\n\nNOVA offline.")


if __name__ == "__main__":
    main()
