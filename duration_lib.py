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
