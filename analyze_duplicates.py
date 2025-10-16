#!/usr/bin/env python3
"""
Analyze multiple log files to detect duplicate tests across runners.
Useful for validating parallel execution splits to ensure no overlaps or gaps.
"""
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple
from duration_lib import (
    parse_test_durations,
    format_duration,
    extract_package,
    extract_class
)


def analyze_duplicates(log_files: List[str], show_details: bool = False):
    """
    Analyze multiple log files to detect duplicate and missing tests.

    Args:
        log_files: List of log file paths to analyze
        show_details: Whether to show detailed lists of duplicates
    """
    print("=" * 80)
    print(f"DUPLICATE TEST ANALYSIS ACROSS {len(log_files)} LOG FILES")
    print("=" * 80)

    # Parse all log files
    log_data = {}
    all_tests = set()
    all_classes = set()
    all_packages = set()

    for i, log_file in enumerate(log_files, 1):
        print(f"\n[{i}/{len(log_files)}] Parsing: {log_file}")
        try:
            durations = parse_test_durations(log_file)

            tests = set(test_name for test_name, _ in durations)
            classes = set(extract_class(test_name) for test_name in tests)
            packages = set(extract_package(test_name) for test_name in tests)

            total_duration = sum(d for _, d in durations)

            log_data[log_file] = {
                'durations': durations,
                'tests': tests,
                'classes': classes,
                'packages': packages,
                'total_duration': total_duration
            }

            all_tests.update(tests)
            all_classes.update(classes)
            all_packages.update(packages)

            print(f"  Tests: {len(tests)}, Classes: {len(classes)}, "
                  f"Packages: {len(packages)}, Duration: {format_duration(total_duration)}")

        except FileNotFoundError:
            print(f"  ERROR: File not found!")
            sys.exit(1)
        except Exception as e:
            print(f"  ERROR: {e}")
            sys.exit(1)

    # Analyze at different levels
    print("\n" + "=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)

    total_duration_all = sum(data['total_duration'] for data in log_data.values())
    print(f"Total unique tests: {len(all_tests)}")
    print(f"Total unique classes: {len(all_classes)}")
    print(f"Total unique packages: {len(all_packages)}")
    print(f"Total duration across all logs: {format_duration(total_duration_all)}")

    # Detect duplicates at test level
    print("\n" + "=" * 80)
    print("TEST-LEVEL ANALYSIS")
    print("=" * 80)

    test_occurrences = defaultdict(list)
    for log_file, data in log_data.items():
        for test_name in data['tests']:
            test_occurrences[test_name].append(log_file)

    duplicate_tests = {test: files for test, files in test_occurrences.items()
                       if len(files) > 1}
    missing_tests = {test: files for test, files in test_occurrences.items()
                     if len(files) == 0}  # Should never happen, but for completeness

    print(f"\nDuplicate tests (appearing in multiple logs): {len(duplicate_tests)}")
    if duplicate_tests:
        print(f"  WARNING: {len(duplicate_tests)} tests appear in multiple log files!")

        # Calculate wasted time from duplicates
        wasted_time = 0
        for test, files in duplicate_tests.items():
            # Find the duration for this test
            for log_file in files:
                for test_name, duration in log_data[log_file]['durations']:
                    if test_name == test:
                        wasted_time += duration * (len(files) - 1)
                        break
                break

        print(f"  Wasted time from duplicates: {format_duration(wasted_time)}")
        print(f"  Average duplications per test: {sum(len(f) for f in duplicate_tests.values()) / len(duplicate_tests):.1f}")

        if show_details:
            print("\n  Top 20 most duplicated tests:")
            sorted_dupes = sorted(duplicate_tests.items(),
                                 key=lambda x: len(x[1]), reverse=True)
            for test, files in sorted_dupes[:20]:
                print(f"    {test}")
                print(f"      Appears in {len(files)} logs: {', '.join(f'log{log_files.index(f)+1}' for f in files)}")
    else:
        print("  ✓ No duplicate tests found - excellent!")

    # Detect duplicates at class level
    print("\n" + "=" * 80)
    print("CLASS-LEVEL ANALYSIS")
    print("=" * 80)

    class_occurrences = defaultdict(list)
    for log_file, data in log_data.items():
        for class_name in data['classes']:
            class_occurrences[class_name].append(log_file)

    duplicate_classes = {cls: files for cls, files in class_occurrences.items()
                        if len(files) > 1}

    print(f"\nClasses appearing in multiple logs: {len(duplicate_classes)}")
    if duplicate_classes:
        print(f"  WARNING: {len(duplicate_classes)} classes appear in multiple log files!")
        print(f"  This may indicate split boundaries should be at class level")

        if show_details:
            print("\n  Top 20 most duplicated classes:")
            sorted_dupes = sorted(duplicate_classes.items(),
                                 key=lambda x: len(x[1]), reverse=True)
            for class_name, files in sorted_dupes[:20]:
                print(f"    {class_name}")
                print(f"      Appears in {len(files)} logs: {', '.join(f'log{log_files.index(f)+1}' for f in files)}")
    else:
        print("  ✓ No classes span multiple logs")

    # Detect duplicates at package level
    print("\n" + "=" * 80)
    print("PACKAGE-LEVEL ANALYSIS")
    print("=" * 80)

    package_occurrences = defaultdict(list)
    for log_file, data in log_data.items():
        for package_name in data['packages']:
            package_occurrences[package_name].append(log_file)

    duplicate_packages = {pkg: files for pkg, files in package_occurrences.items()
                         if len(files) > 1}

    print(f"\nPackages appearing in multiple logs: {len(duplicate_packages)}")
    if duplicate_packages:
        print(f"  WARNING: {len(duplicate_packages)} packages appear in multiple log files!")
        print(f"  This may indicate split boundaries should be at package level")

        if show_details:
            print("\n  All duplicated packages:")
            sorted_dupes = sorted(duplicate_packages.items(),
                                 key=lambda x: len(x[1]), reverse=True)
            for package_name, files in sorted_dupes:
                print(f"    {package_name}")
                print(f"      Appears in {len(files)} logs: {', '.join(f'log{log_files.index(f)+1}' for f in files)}")
    else:
        print("  ✓ No packages span multiple logs")

    # Distribution analysis
    print("\n" + "=" * 80)
    print("DISTRIBUTION ANALYSIS")
    print("=" * 80)

    print(f"\n{'Log File':<40} {'Tests':<10} {'Duration':<15} {'%':<8}")
    print("-" * 80)

    for log_file, data in log_data.items():
        short_name = log_file[-37:] if len(log_file) > 37 else log_file
        test_count = len(data['tests'])
        duration = data['total_duration']
        percentage = (duration / total_duration_all * 100) if total_duration_all > 0 else 0
        print(f"{short_name:<40} {test_count:<10} {format_duration(duration):<15} {percentage:>6.2f}%")

    # Balance analysis
    if total_duration_all > 0:
        durations = [data['total_duration'] for data in log_data.values()]
        max_duration = max(durations)
        min_duration = min(durations)
        avg_duration = total_duration_all / len(log_files)

        balance_ratio = min_duration / max_duration if max_duration > 0 else 0

        print(f"\nBalance metrics:")
        print(f"  Max duration: {format_duration(max_duration)}")
        print(f"  Min duration: {format_duration(min_duration)}")
        print(f"  Avg duration: {format_duration(avg_duration)}")
        print(f"  Balance ratio: {balance_ratio:.2f} (1.0 = perfect balance)")

        if balance_ratio < 0.8:
            print(f"  ⚠ Poor balance - consider redistributing tests")
        elif balance_ratio < 0.9:
            print(f"  ⚠ Moderate balance - some improvement possible")
        else:
            print(f"  ✓ Good balance")

    # Summary and recommendations
    print("\n" + "=" * 80)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 80)

    issues = []

    if duplicate_tests:
        issues.append(f"❌ {len(duplicate_tests)} duplicate tests found")
    else:
        print("✓ No duplicate tests - clean separation")

    if duplicate_classes and not duplicate_tests:
        issues.append(f"⚠ {len(duplicate_classes)} classes split across logs (tests from same class in different logs)")

    if duplicate_packages and not duplicate_classes:
        issues.append(f"⚠ {len(duplicate_packages)} packages split across logs (classes from same package in different logs)")

    if balance_ratio < 0.8:
        issues.append(f"⚠ Poor load balance (ratio: {balance_ratio:.2f})")

    if issues:
        print("\nIssues found:")
        for issue in issues:
            print(f"  {issue}")

        print("\nRecommendations:")
        if duplicate_tests:
            print("  1. Remove duplicate tests - same test should not run in multiple logs")
            print("  2. This wastes CI time and may mask intermittent failures")
        if duplicate_classes and not duplicate_tests:
            print("  3. Consider keeping test classes together for better isolation")
        if duplicate_packages and not duplicate_classes:
            print("  4. Consider using package-level splits for cleaner boundaries")
        if balance_ratio < 0.8:
            print("  5. Redistribute tests for better load balancing")
    else:
        print("\n✓ All checks passed - excellent test distribution!")


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python analyze_duplicates.py <log_file1> <log_file2> [log_file3 ...] [--show-details]")
        print("\nAnalyzes multiple log files to detect duplicate tests across runners.")
        print("\nExamples:")
        print("  python analyze_duplicates.py runner1.log runner2.log runner3.log")
        print("  python analyze_duplicates.py logs/*.log --show-details")
        print("\nFlags:")
        print("  --show-details  Show detailed lists of duplicate items")
        sys.exit(1)

    log_files = []
    show_details = False

    for arg in sys.argv[1:]:
        if arg == '--show-details':
            show_details = True
        else:
            log_files.append(arg)

    if len(log_files) < 2:
        print("Error: At least 2 log files are required for duplicate detection.")
        sys.exit(1)

    try:
        analyze_duplicates(log_files, show_details)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
