#!/usr/bin/env python3
"""
Analyze test durations grouped by Java package.
Helps identify how to split tests for parallel execution.
"""
import sys
from duration_lib import (
    parse_test_durations,
    format_duration,
    extract_package,
    group_by,
    calculate_cumulative_distribution,
    suggest_parallel_splits,
    print_histogram
)


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

    packages = group_by(durations, extract_package)

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

    # Print histogram of package total durations
    package_durations = [info['total_duration'] for _, info in sorted_packages]
    print_histogram(package_durations, "PACKAGE DURATION DISTRIBUTION")

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

    thresholds = [10, 25, 50, 75, 90]
    cumulative_results = calculate_cumulative_distribution(
        sorted_packages, thresholds, total_duration
    )

    for count, pct, cumulative in cumulative_results:
        print(f"Top {count} packages account for {pct:.1f}% of total duration "
              f"({format_duration(cumulative)})")

    # Suggest split strategies
    print(f"\n{'='*80}")
    print("PARALLEL EXECUTION SUGGESTIONS")
    print(f"{'='*80}")

    # Calculate splits for different runner counts
    for num_runners in [2, 4, 8]:
        target_duration = total_duration / num_runners
        print(f"\nFor {num_runners} parallel runners (target: {format_duration(target_duration)} each):")

        splits = suggest_parallel_splits(sorted_packages, num_runners, total_duration)

        for i, split in enumerate(splits, 1):
            print(f"  Runner {i}: {format_duration(split['duration']):<12} "
                  f"({split['percentage']:>5.1f}%) - {len(split['items'])} packages")


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
