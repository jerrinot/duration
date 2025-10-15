#!/usr/bin/env python3
"""
Analyze test durations from log files and find the longest running tests.
"""
import sys
from duration_lib import parse_test_durations, format_duration


def analyze_tests(log_file: str, top_n: int = 20):
    """
    Analyze test durations and display statistics.

    Args:
        log_file: Path to the log file
        top_n: Number of longest running tests to display
    """
    print(f"Analyzing test durations from: {log_file}")
    print("=" * 80)

    durations = parse_test_durations(log_file)

    if not durations:
        print("No test durations found in the log file.")
        return

    # Sort by duration (descending)
    durations.sort(key=lambda x: x[1], reverse=True)

    # Calculate statistics
    total_tests = len(durations)
    total_duration = sum(d[1] for d in durations)
    avg_duration = total_duration / total_tests
    max_duration = durations[0][1]
    min_duration = durations[-1][1]

    print(f"\nTotal tests found: {total_tests}")
    print(f"Total duration: {format_duration(total_duration)}")
    print(f"Average duration: {format_duration(avg_duration)}")
    print(f"Max duration: {format_duration(max_duration)}")
    print(f"Min duration: {format_duration(min_duration)}")

    print(f"\n{'='*80}")
    print(f"TOP {min(top_n, total_tests)} LONGEST RUNNING TESTS")
    print(f"{'='*80}")
    print(f"{'Rank':<6} {'Duration':<15} {'Test Name'}")
    print("-" * 80)

    for i, (test_name, duration) in enumerate(durations[:top_n], 1):
        print(f"{i:<6} {format_duration(duration):<15} {test_name}")

    # Show tests over certain thresholds
    print(f"\n{'='*80}")
    print("DURATION BREAKDOWN")
    print(f"{'='*80}")

    thresholds = [
        (60, "Tests over 1 minute"),
        (120, "Tests over 2 minutes"),
        (300, "Tests over 5 minutes"),
        (600, "Tests over 10 minutes"),
    ]

    for threshold, label in thresholds:
        count = sum(1 for _, d in durations if d > threshold)
        if count > 0:
            percentage = (count / total_tests) * 100
            print(f"{label}: {count} ({percentage:.1f}%)")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_tests.py <log_file> [top_n]")
        print("Example: python analyze_tests.py 176 50")
        sys.exit(1)

    log_file = sys.argv[1]
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    try:
        analyze_tests(log_file, top_n)
    except FileNotFoundError:
        print(f"Error: File '{log_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
