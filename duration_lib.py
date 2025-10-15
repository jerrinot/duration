#!/usr/bin/env python3
"""
Shared library for test duration analysis tools.
Contains common functions used by analyze_tests.py, analyze_by_package.py, and analyze_by_class.py
"""
import re
from collections import defaultdict
from typing import List, Tuple, Dict, Callable


def parse_test_durations(log_file: str) -> List[Tuple[str, float]]:
    """
    Parse test durations from a log file.

    Args:
        log_file: Path to the log file

    Returns:
        List of tuples (test_name, duration_seconds)
    """
    # Support both log formats: "<<<<= " (old) and "<<<< " (new)
    pattern = re.compile(r'<<<<[=]?\s+(.+?)\s+duration_ms=(\d+)')
    durations = []
    seen = {}  # Track test names to avoid duplicates

    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                test_name = match.group(1)
                duration_ms = int(match.group(2))
                duration_sec = duration_ms / 1000.0

                # Only keep the first occurrence of each test
                if test_name not in seen:
                    seen[test_name] = duration_sec
                    durations.append((test_name, duration_sec))

    return durations


def format_duration(seconds: float) -> str:
    """
    Format duration in a human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "1m 30.50s", "2h 15m 30.00s")
    """
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


def extract_package(test_name: str) -> str:
    """
    Extract package name from full test name.

    Example: com.questdb.acl.AccessControlTest.testMethod[WITH_WAL]
             -> com.questdb.acl

    Args:
        test_name: Full test name

    Returns:
        Package name (all parts except ClassName and methodName)
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


def extract_class(test_name: str) -> str:
    """
    Extract class name from full test name.

    Example: com.questdb.acl.AccessControlTest.testMethod[WITH_WAL]
             -> com.questdb.acl.AccessControlTest

    Args:
        test_name: Full test name

    Returns:
        Class name (package + class, excluding methodName)
    """
    # Remove parameter part [WITH_WAL] if present
    test_name = test_name.split('[')[0]

    # Split by dots and take all but the last part (methodName)
    parts = test_name.split('.')
    if len(parts) >= 2:
        # Return all except methodName
        return '.'.join(parts[:-1])
    else:
        return test_name


def group_by(
    durations: List[Tuple[str, float]],
    extractor: Callable[[str], str]
) -> Dict[str, dict]:
    """
    Group test durations using a custom extraction function.

    Args:
        durations: List of (test_name, duration_seconds) tuples
        extractor: Function that extracts the grouping key from a test name

    Returns:
        Dict mapping group_key -> {
            'total_duration': float,
            'test_count': int,
            'tests': [(name, duration), ...]
        }
    """
    groups = defaultdict(lambda: {'total_duration': 0.0, 'test_count': 0, 'tests': []})

    for test_name, duration in durations:
        group_key = extractor(test_name)
        groups[group_key]['total_duration'] += duration
        groups[group_key]['test_count'] += 1
        groups[group_key]['tests'].append((test_name, duration))

    return dict(groups)


def calculate_cumulative_distribution(
    sorted_items: List[Tuple[str, dict]],
    thresholds: List[float],
    total_duration: float
) -> List[Tuple[int, float, float]]:
    """
    Calculate cumulative distribution thresholds.

    Args:
        sorted_items: List of (name, info_dict) sorted by duration descending
        thresholds: List of percentage thresholds (e.g., [10, 25, 50, 75, 90])
        total_duration: Total duration across all items

    Returns:
        List of (item_count, cumulative_percentage, cumulative_duration) tuples
        for each threshold that is reached
    """
    results = []
    cumulative = 0.0
    threshold_idx = 0

    for i, (name, info) in enumerate(sorted_items, 1):
        cumulative += info['total_duration']
        cumulative_pct = (cumulative / total_duration) * 100 if total_duration > 0 else 0

        while threshold_idx < len(thresholds) and cumulative_pct >= thresholds[threshold_idx]:
            results.append((i, cumulative_pct, cumulative))
            threshold_idx += 1

    return results


def suggest_parallel_splits(
    sorted_items: List[Tuple[str, dict]],
    num_runners: int,
    total_duration: float
) -> List[dict]:
    """
    Suggest how to split items across parallel runners using greedy bin packing.

    Args:
        sorted_items: List of (name, info_dict) sorted by duration descending
        num_runners: Number of parallel runners
        total_duration: Total duration across all items

    Returns:
        List of dicts, one per runner:
        {
            'items': [item_names],
            'duration': total_duration,
            'percentage': percentage of total
        }
    """
    runners = [[] for _ in range(num_runners)]
    runner_durations = [0.0] * num_runners

    # Greedy bin packing: assign each item to the runner with least total time
    for item_name, info in sorted_items:
        min_idx = runner_durations.index(min(runner_durations))
        runners[min_idx].append(item_name)
        runner_durations[min_idx] += info['total_duration']

    # Build result
    result = []
    for items, duration in zip(runners, runner_durations):
        percentage = (duration / total_duration * 100) if total_duration > 0 else 0.0
        result.append({
            'items': items,
            'duration': duration,
            'percentage': percentage
        })

    return result


def print_histogram(durations: List[float], title: str = "DURATION HISTOGRAM", bar_width: int = 40, num_buckets: int = 10):
    """
    Print an ASCII histogram showing the distribution of durations.
    Automatically determines bucket ranges based on data distribution.

    Args:
        durations: List of duration values in seconds
        title: Title for the histogram section
        bar_width: Maximum width of histogram bars in characters
        num_buckets: Target number of buckets (will be adjusted based on data)
    """
    if not durations:
        return

    min_duration = min(durations)
    max_duration = max(durations)

    # If all durations are the same, show a single bucket
    if min_duration == max_duration:
        print(f"\n{'='*80}")
        print(title)
        print(f"{'='*80}")
        label = format_duration(min_duration)
        bar = "█" * bar_width
        print(f"[{label:<12}] {bar:<{bar_width}} {len(durations):>5} (100.0%)")
        return

    # Create smart buckets based on data range
    buckets = _create_smart_buckets(min_duration, max_duration, num_buckets)

    # Count items in each bucket
    bucket_counts = [0] * len(buckets)
    for duration in durations:
        for i, (min_val, max_val, _) in enumerate(buckets):
            if min_val <= duration < max_val:
                bucket_counts[i] += 1
                break
        else:
            # Handle edge case: duration == max_duration
            if duration == max_duration:
                bucket_counts[-1] += 1

    # Find max count for scaling
    max_count = max(bucket_counts) if bucket_counts else 1
    total_items = len(durations)

    # Print histogram
    print(f"\n{'='*80}")
    print(title)
    print(f"{'='*80}")

    # Print buckets, coalescing consecutive empty ones
    i = 0
    while i < len(buckets):
        label = buckets[i][2]
        count = bucket_counts[i]

        if count == 0:
            # Count consecutive empty buckets
            empty_start = i
            while i < len(bucket_counts) and bucket_counts[i] == 0:
                i += 1

            # Show "..." for any empty range (single or multiple)
            print(f"{'...':<14} {'':40} {'':>5}")
        else:
            # Non-empty bucket
            # Calculate bar length
            bar_length = int((count / max_count) * bar_width)
            bar = "█" * bar_length

            # Calculate percentage
            percentage = (count / total_items) * 100

            # Print the histogram line
            print(f"[{label:<12}] {bar:<{bar_width}} {count:>5} ({percentage:>5.1f}%)")
            i += 1


def _create_smart_buckets(min_val: float, max_val: float, target_buckets: int) -> List[Tuple[float, float, str]]:
    """
    Create smart bucket ranges based on the data distribution.
    Uses nice round numbers for bucket boundaries.

    Args:
        min_val: Minimum duration value
        max_val: Maximum duration value
        target_buckets: Target number of buckets

    Returns:
        List of (min_val, max_val, label) tuples
    """
    # Calculate range and determine appropriate step size
    data_range = max_val - min_val
    raw_step = data_range / target_buckets

    # Round step to a "nice" number for better readability
    step = _nice_number(raw_step)

    # Create buckets starting from a nice round number at or before min_val
    start = (min_val // step) * step
    buckets = []

    current = start
    # Ensure we cover the full range - continue until we pass max_val
    while current <= max_val:
        next_val = current + step

        # Format label - use consistent unit for the entire range
        if max_val < 60:
            # Everything in seconds
            if step < 1:
                label = f"{current:.1f}-{next_val:.1f}s"
            else:
                label = f"{current:.0f}-{next_val:.0f}s"
        elif max_val < 3600:
            # Everything in minutes
            curr_m = current / 60
            next_m = next_val / 60
            if step < 60:
                label = f"{curr_m:.1f}-{next_m:.1f}m"
            else:
                label = f"{curr_m:.0f}-{next_m:.0f}m"
        else:
            # Everything in hours
            curr_h = current / 3600
            next_h = next_val / 3600
            if step < 3600:
                label = f"{curr_h:.1f}-{next_h:.1f}h"
            else:
                label = f"{curr_h:.0f}-{next_h:.0f}h"

        buckets.append((current, next_val, label))
        current = next_val

        # Safety limit
        if len(buckets) > 20:
            break

    return buckets


def _nice_number(value: float) -> float:
    """
    Round a number to a "nice" value for histogram buckets.
    Uses common nice numbers: 1, 2, 5 (and their powers of 10).

    Args:
        value: The raw value to round

    Returns:
        A "nice" rounded value
    """
    if value <= 0:
        return 1.0

    # Special handling for time-based nice numbers
    time_steps = [0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 20, 30, 60, 120, 180, 300, 600, 900, 1800, 3600]

    # Find the closest time step that's >= value
    for step in time_steps:
        if step >= value:
            return step

    # For very large values, use powers of 10
    exponent = 10 ** int(max(0, round(value / 10)))
    normalized = value / exponent

    # Round to nearest nice fraction
    if normalized <= 1:
        nice = 1
    elif normalized <= 2:
        nice = 2
    elif normalized <= 5:
        nice = 5
    else:
        nice = 10

    return nice * exponent
