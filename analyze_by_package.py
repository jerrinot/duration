#!/usr/bin/env python3
"""
Analyze test durations grouped by Java package.
Helps identify how to split tests for parallel execution.
"""
import re
import sys
from collections import defaultdict
from typing import Dict, List, Tuple


def parse_test_durations(log_file: str) -> List[Tuple[str, float]]:
    """
    Parse test durations from a log file.

    Args:
        log_file: Path to the log file

    Returns:
        List of tuples (test_name, duration_seconds)
    """
    pattern = re.compile(r'<<<<= (.+?)\s+duration_ms=(\d+)')
    durations = []

    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                test_name = match.group(1)
                duration_ms = int(match.group(2))
                duration_sec = duration_ms / 1000.0
                durations.append((test_name, duration_sec))

    return durations


def extract_package(test_name: str) -> str:
    """
    Extract package name from full test name.

    Example: com.questdb.acl.AccessControlTest.testMethod[WITH_WAL]
             -> com.questdb.acl

    Args:
        test_name: Full test name

    Returns:
        Package name
    """
    # Remove parameter part [WITH_WAL] if present
    test_name = test_name.split('[')[0]

    # Split by dots and take all but the last two parts (ClassName.methodName)
    parts = test_name.split('.')
    if len(parts) >= 3:
        # Return all except ClassName and methodName
        return '.'.join(parts[:-2])
    else:
        return test_name


def group_by_package(durations: List[Tuple[str, float]]) -> Dict[str, dict]:
    """
    Group test durations by package.

    Args:
        durations: List of (test_name, duration_seconds)

    Returns:
        Dict mapping package -> {total_duration, test_count, tests: [(name, duration)]}
    """
    packages = defaultdict(lambda: {'total_duration': 0.0, 'test_count': 0, 'tests': []})

    for test_name, duration in durations:
        package = extract_package(test_name)
        packages[package]['total_duration'] += duration
        packages[package]['test_count'] += 1
        packages[package]['tests'].append((test_name, duration))

    return packages


def format_duration(seconds: float) -> str:
    """Format duration in a human-readable format."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.2f}s"


def analyze_by_package(log_file: str, top_n: int = 20, show_tests: bool = False):
    """
    Analyze test durations grouped by package.

    Args:
        log_file: Path to the log file
        top_n: Number of top packages to display
        show_tests: Whether to show individual tests within each package
    """
    print(f"Analyzing test durations by package from: {log_file}")
    print("=" * 80)

    durations = parse_test_durations(log_file)

    if not durations:
        print("No test durations found in the log file.")
        return

    packages = group_by_package(durations)

    # Sort packages by total duration (descending)
    sorted_packages = sorted(
        packages.items(),
        key=lambda x: x[1]['total_duration'],
        reverse=True
    )

    # Calculate overall statistics
    total_tests = len(durations)
    total_duration = sum(d[1] for d in durations)
    total_packages = len(packages)

    print(f"\nTotal packages: {total_packages}")
    print(f"Total tests: {total_tests}")
    print(f"Total duration: {format_duration(total_duration)}")
    print(f"Average tests per package: {total_tests / total_packages:.1f}")

    print(f"\n{'='*80}")
    print(f"TOP {min(top_n, total_packages)} PACKAGES BY TOTAL DURATION")
    print(f"{'='*80}")
    print(f"{'Rank':<6} {'Duration':<15} {'Tests':<8} {'Avg/Test':<12} {'%':<8} {'Package'}")
    print("-" * 80)

    for i, (package, info) in enumerate(sorted_packages[:top_n], 1):
        total_dur = info['total_duration']
        test_count = info['test_count']
        avg_duration = total_dur / test_count
        percentage = (total_dur / total_duration) * 100

        print(f"{i:<6} {format_duration(total_dur):<15} {test_count:<8} "
              f"{format_duration(avg_duration):<12} {percentage:>6.2f}%  {package}")

        if show_tests:
            # Show top 5 slowest tests in this package
            sorted_tests = sorted(info['tests'], key=lambda x: x[1], reverse=True)
            for test_name, test_dur in sorted_tests[:5]:
                # Show just the class and method name
                short_name = test_name.replace(package + '.', '')
                print(f"       ├─ {format_duration(test_dur):<12} {short_name}")
            if len(sorted_tests) > 5:
                print(f"       └─ ... and {len(sorted_tests) - 5} more tests")

    # Show cumulative percentages for parallel execution planning
    print(f"\n{'='*80}")
    print("CUMULATIVE DISTRIBUTION (for parallel execution planning)")
    print(f"{'='*80}")

    cumulative = 0.0
    thresholds = [10, 25, 50, 75, 90]
    threshold_idx = 0

    for i, (package, info) in enumerate(sorted_packages, 1):
        cumulative += info['total_duration']
        cumulative_pct = (cumulative / total_duration) * 100

        if threshold_idx < len(thresholds) and cumulative_pct >= thresholds[threshold_idx]:
            print(f"Top {i} packages account for {cumulative_pct:.1f}% of total duration "
                  f"({format_duration(cumulative)})")
            threshold_idx += 1

    # Suggest split strategies
    print(f"\n{'='*80}")
    print("PARALLEL EXECUTION SUGGESTIONS")
    print(f"{'='*80}")

    # Calculate splits for different runner counts
    for num_runners in [2, 4, 8]:
        target_duration = total_duration / num_runners
        print(f"\nFor {num_runners} parallel runners (target: {format_duration(target_duration)} each):")

        runners = [[] for _ in range(num_runners)]
        runner_durations = [0.0] * num_runners

        # Greedy bin packing: assign each package to the runner with least total time
        for package, info in sorted_packages:
            min_idx = runner_durations.index(min(runner_durations))
            runners[min_idx].append(package)
            runner_durations[min_idx] += info['total_duration']

        for i, (runner_packages, duration) in enumerate(zip(runners, runner_durations), 1):
            pct = (duration / total_duration) * 100
            print(f"  Runner {i}: {format_duration(duration):<12} ({pct:>5.1f}%) - "
                  f"{len(runner_packages)} packages")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_by_package.py <log_file> [top_n] [--show-tests]")
        print("Example: python analyze_by_package.py 176 30")
        print("         python analyze_by_package.py 176 30 --show-tests")
        sys.exit(1)

    log_file = sys.argv[1]
    top_n = 20
    show_tests = False

    for arg in sys.argv[2:]:
        if arg == '--show-tests':
            show_tests = True
        else:
            try:
                top_n = int(arg)
            except ValueError:
                print(f"Warning: Invalid argument '{arg}' ignored")

    try:
        analyze_by_package(log_file, top_n, show_tests)
    except FileNotFoundError:
        print(f"Error: File '{log_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
