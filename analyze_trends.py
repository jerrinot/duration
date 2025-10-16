#!/usr/bin/env python3
"""
Analyze test duration trends across multiple log files.
Track performance changes, detect regressions, and identify improvement patterns.
"""
import sys
import statistics
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from duration_lib import parse_test_durations, format_duration


def calculate_test_trends(test_history: Dict[str, List[Tuple[int, float]]],
                          log_files: List[str]) -> Dict[str, dict]:
    """
    Calculate trend metrics for each test across all runs.

    Args:
        test_history: Dict mapping test_name -> [(log_index, duration), ...]
        log_files: List of log file paths

    Returns:
        Dict mapping test_name -> {
            'baseline_duration': float,
            'current_duration': float,
            'absolute_change': float,
            'relative_change': float,
            'variance': Optional[float],
            'stdev': Optional[float],
            'mean': Optional[float],
            'cv': Optional[float],  # coefficient of variation
            'trend': str,  # 'improving', 'degrading', 'stable', 'volatile'
            'history': List[float],  # all durations in order
            'occurrences': int
        }
    """
    trends = {}

    for test_name, history in test_history.items():
        # Sort by log index to get chronological order
        history_sorted = sorted(history, key=lambda x: x[0])
        durations = [duration for _, duration in history_sorted]

        baseline_duration = durations[0]
        current_duration = durations[-1]
        absolute_change = current_duration - baseline_duration
        relative_change = ((current_duration - baseline_duration) / baseline_duration * 100) if baseline_duration > 0 else 0.0

        # Calculate variance metrics for 3+ occurrences
        variance = None
        stdev = None
        mean = None
        cv = None

        if len(durations) >= 3:
            variance = statistics.variance(durations)
            stdev = statistics.stdev(durations)
            mean = statistics.mean(durations)
            cv = (stdev / mean * 100) if mean > 0 else 0.0

        # Determine trend
        if len(durations) >= 3 and cv and cv > 30:
            trend = 'volatile'
        elif abs(relative_change) < 10 and abs(absolute_change) < 2:
            trend = 'stable'
        elif relative_change < 0:
            trend = 'improving'
        else:
            trend = 'degrading'

        trends[test_name] = {
            'baseline_duration': baseline_duration,
            'current_duration': current_duration,
            'absolute_change': absolute_change,
            'relative_change': relative_change,
            'variance': variance,
            'stdev': stdev,
            'mean': mean,
            'cv': cv,
            'trend': trend,
            'history': durations,
            'occurrences': len(durations)
        }

    return trends


def detect_regressions(test_trends: Dict[str, dict],
                       threshold_pct: float,
                       threshold_abs: float) -> List[Tuple[str, dict]]:
    """
    Detect performance regressions.

    Args:
        test_trends: Dict of test trends from calculate_test_trends()
        threshold_pct: Percentage threshold for regression (e.g., 20.0 for 20%)
        threshold_abs: Absolute threshold in seconds (e.g., 5.0 for 5s)

    Returns:
        Sorted list of (test_name, trend_metrics) for regressed tests
    """
    regressions = []

    for test_name, metrics in test_trends.items():
        if (metrics['relative_change'] > threshold_pct or
            metrics['absolute_change'] > threshold_abs):
            regressions.append((test_name, metrics))

    # Sort by impact (combination of absolute and relative change)
    regressions.sort(key=lambda x: x[1]['absolute_change'], reverse=True)

    return regressions


def detect_improvements(test_trends: Dict[str, dict],
                        threshold_pct: float,
                        threshold_abs: float) -> List[Tuple[str, dict]]:
    """
    Detect performance improvements.

    Args:
        test_trends: Dict of test trends from calculate_test_trends()
        threshold_pct: Percentage threshold for improvement (e.g., 20.0 for 20%)
        threshold_abs: Absolute threshold in seconds (e.g., 5.0 for 5s)

    Returns:
        Sorted list of (test_name, trend_metrics) for improved tests
    """
    improvements = []

    for test_name, metrics in test_trends.items():
        if (metrics['relative_change'] < -threshold_pct or
            metrics['absolute_change'] < -threshold_abs):
            improvements.append((test_name, metrics))

    # Sort by impact (combination of absolute and relative change)
    improvements.sort(key=lambda x: x[1]['absolute_change'])

    return improvements


def format_change(change_seconds: float, change_pct: float) -> str:
    """
    Format a duration change with appropriate indicator.

    Args:
        change_seconds: Change in seconds
        change_pct: Change in percentage

    Returns:
        Formatted string like "+2m 30.50s (+45.2%) ⬆" or "-15.30s (-12.5%) ⬇"
    """
    sign = "+" if change_seconds >= 0 else ""
    indicator = "⬆" if change_seconds > 0 else "⬇" if change_seconds < 0 else "➡"

    return f"{sign}{format_duration(abs(change_seconds))} ({sign}{change_pct:.1f}%) {indicator}"


def print_trend_visualization(log_metadata: List[dict]):
    """
    Print a simple visualization of total duration trend.

    Args:
        log_metadata: List of dicts with 'log_file', 'total_duration', 'test_count'
    """
    if len(log_metadata) < 2:
        return

    print("\nTotal Duration Trend:")

    max_duration = max(meta['total_duration'] for meta in log_metadata)
    bar_width = 50

    for i, meta in enumerate(log_metadata, 1):
        duration = meta['total_duration']
        bar_length = int((duration / max_duration) * bar_width) if max_duration > 0 else 0
        bar = "█" * bar_length

        short_name = meta['log_file'][-30:] if len(meta['log_file']) > 30 else meta['log_file']
        print(f"  Run {i} ({short_name:>30}): {bar:<{bar_width}} {format_duration(duration)}")


def analyze_trends(log_files: List[str],
                   show_details: bool = False,
                   regression_threshold_pct: float = 20.0,
                   regression_threshold_abs: float = 5.0):
    """
    Analyze test duration trends across multiple log files.

    Args:
        log_files: List of log file paths in chronological order
        show_details: Whether to show detailed information
        regression_threshold_pct: Percentage threshold for regression detection
        regression_threshold_abs: Absolute threshold in seconds for regression detection
    """
    print("=" * 80)
    print(f"PERFORMANCE TREND ANALYSIS ACROSS {len(log_files)} LOG FILES")
    print("=" * 80)

    # Parse all log files
    log_metadata = []
    test_history = defaultdict(list)  # test_name -> [(log_index, duration), ...]
    all_tests_baseline = set()
    all_tests_current = set()

    for i, log_file in enumerate(log_files):
        print(f"\n[{i+1}/{len(log_files)}] Parsing: {log_file}")
        try:
            durations = parse_test_durations(log_file)

            test_names = set(test_name for test_name, _ in durations)
            total_duration = sum(d for _, d in durations)

            log_metadata.append({
                'log_file': log_file,
                'total_duration': total_duration,
                'test_count': len(durations),
                'test_names': test_names
            })

            # Track first and last run for new/removed test detection
            if i == 0:
                all_tests_baseline = test_names
            if i == len(log_files) - 1:
                all_tests_current = test_names

            # Build test history
            for test_name, duration in durations:
                test_history[test_name].append((i, duration))

            print(f"  Tests: {len(durations)}, Total duration: {format_duration(total_duration)}")

        except FileNotFoundError:
            print(f"  ERROR: File not found!")
            sys.exit(1)
        except Exception as e:
            print(f"  ERROR: {e}")
            sys.exit(1)

    # Overall statistics
    print("\n" + "=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)

    for i, meta in enumerate(log_metadata, 1):
        short_name = meta['log_file'][-40:] if len(meta['log_file']) > 40 else meta['log_file']
        label = "(baseline)" if i == 1 else "(current)" if i == len(log_metadata) else ""
        print(f"Run {i} {label:12}: {meta['test_count']:4} tests, {format_duration(meta['total_duration'])}")

    # Calculate overall changes
    baseline_duration = log_metadata[0]['total_duration']
    current_duration = log_metadata[-1]['total_duration']
    duration_change = current_duration - baseline_duration
    duration_change_pct = (duration_change / baseline_duration * 100) if baseline_duration > 0 else 0.0

    baseline_count = log_metadata[0]['test_count']
    current_count = log_metadata[-1]['test_count']
    count_change = current_count - baseline_count

    print(f"\nTotal duration change: {format_change(duration_change, duration_change_pct)}")
    print(f"Total test count change: {count_change:+d} tests")

    # Print trend visualization
    if len(log_files) >= 2:
        print_trend_visualization(log_metadata)

    # Calculate test-level trends (only for tests appearing in both baseline and current)
    tests_in_both = all_tests_baseline & all_tests_current
    test_trends = calculate_test_trends(
        {k: v for k, v in test_history.items() if k in tests_in_both},
        log_files
    )

    # Performance regressions
    print("\n" + "=" * 80)
    print(f"PERFORMANCE REGRESSIONS (>{regression_threshold_pct:.0f}% or >{format_duration(regression_threshold_abs)} slower)")
    print("=" * 80)

    regressions = detect_regressions(test_trends, regression_threshold_pct, regression_threshold_abs)

    print(f"\nFound {len(regressions)} test regressions")

    if regressions:
        display_count = min(20, len(regressions)) if not show_details else len(regressions)
        print(f"\nTop {display_count} slowest regressions (by absolute impact):")

        for i, (test_name, metrics) in enumerate(regressions[:display_count], 1):
            print(f"\n  {i}. {test_name}")
            print(f"     Baseline: {format_duration(metrics['baseline_duration'])} → "
                  f"Current: {format_duration(metrics['current_duration'])}")
            print(f"     Change: {format_change(metrics['absolute_change'], metrics['relative_change'])}")

        # Calculate total impact
        total_regression_time = sum(m['absolute_change'] for _, m in regressions)
        print(f"\n  Total time added by regressions: {format_duration(total_regression_time)}")
    else:
        print("  ✓ No significant regressions detected!")

    # Performance improvements
    print("\n" + "=" * 80)
    print(f"PERFORMANCE IMPROVEMENTS (>{regression_threshold_pct:.0f}% or >{format_duration(regression_threshold_abs)} faster)")
    print("=" * 80)

    improvements = detect_improvements(test_trends, regression_threshold_pct, regression_threshold_abs)

    print(f"\nFound {len(improvements)} test improvements")

    if improvements:
        display_count = min(10, len(improvements)) if not show_details else len(improvements)
        print(f"\nTop {display_count} best improvements:")

        for i, (test_name, metrics) in enumerate(improvements[:display_count], 1):
            print(f"\n  {i}. {test_name}")
            print(f"     Baseline: {format_duration(metrics['baseline_duration'])} → "
                  f"Current: {format_duration(metrics['current_duration'])}")
            print(f"     Change: {format_change(metrics['absolute_change'], metrics['relative_change'])}")

        # Calculate total improvement
        total_improvement_time = sum(-m['absolute_change'] for _, m in improvements)
        print(f"\n  Total time saved by improvements: {format_duration(total_improvement_time)}")

    # New tests
    new_tests = all_tests_current - all_tests_baseline

    if new_tests:
        print("\n" + "=" * 80)
        print("NEW TESTS (added since baseline)")
        print("=" * 80)

        print(f"\n{len(new_tests)} new tests added")

        # Get durations for new tests from current run
        new_test_durations = [(name, test_history[name][-1][1]) for name in new_tests]
        new_test_durations.sort(key=lambda x: x[1], reverse=True)

        total_new_time = sum(d for _, d in new_test_durations)
        print(f"Total time for new tests: {format_duration(total_new_time)}")

        display_count = min(10, len(new_test_durations)) if not show_details else len(new_test_durations)
        if display_count > 0:
            print(f"\nTop {display_count} slowest new tests:")
            for i, (test_name, duration) in enumerate(new_test_durations[:display_count], 1):
                print(f"  {i}. {test_name} - {format_duration(duration)}")

    # Removed tests
    removed_tests = all_tests_baseline - all_tests_current

    if removed_tests:
        print("\n" + "=" * 80)
        print("REMOVED TESTS (present in baseline, missing from current)")
        print("=" * 80)

        print(f"\n{len(removed_tests)} tests removed")

        # Get durations for removed tests from baseline run
        removed_test_durations = [(name, test_history[name][0][1]) for name in removed_tests]
        removed_test_durations.sort(key=lambda x: x[1], reverse=True)

        total_removed_time = sum(d for _, d in removed_test_durations)
        print(f"Total time freed by removed tests: {format_duration(total_removed_time)}")

        display_count = min(10, len(removed_test_durations)) if not show_details else len(removed_test_durations)
        if display_count > 0 and (show_details or len(removed_tests) <= 20):
            print(f"\nRemoved tests:")
            for test_name, duration in removed_test_durations[:display_count]:
                print(f"  - {test_name} (was {format_duration(duration)})")

    # Most volatile tests (only for 3+ logs)
    if len(log_files) >= 3:
        print("\n" + "=" * 80)
        print("MOST VOLATILE TESTS (high duration variance)")
        print("=" * 80)

        # Filter tests with significant volatility
        volatile_tests = [(name, metrics) for name, metrics in test_trends.items()
                         if metrics['cv'] is not None and metrics['cv'] > 30]
        volatile_tests.sort(key=lambda x: x[1]['cv'], reverse=True)

        print(f"\n{len(volatile_tests)} tests with significant variance (CV > 30%)")

        if volatile_tests:
            display_count = min(10, len(volatile_tests)) if not show_details else len(volatile_tests)
            print(f"\nTop {display_count} most volatile tests:")

            for i, (test_name, metrics) in enumerate(volatile_tests[:display_count], 1):
                min_dur = min(metrics['history'])
                max_dur = max(metrics['history'])
                variation_ratio = max_dur / min_dur if min_dur > 0 else 0

                print(f"\n  {i}. {test_name}")
                print(f"     Range: {format_duration(min_dur)} - {format_duration(max_dur)} "
                      f"({variation_ratio:.1f}x variation)")
                print(f"     Mean: {format_duration(metrics['mean'])}, "
                      f"StdDev: {format_duration(metrics['stdev'])}, CV: {metrics['cv']:.1f}%")

                if show_details:
                    history_str = " → ".join(format_duration(d) for d in metrics['history'])
                    print(f"     History: {history_str}")

    # Summary and recommendations
    print("\n" + "=" * 80)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 80)

    # Determine overall trend
    if abs(duration_change_pct) < 5:
        trend_label = "➡ STABLE"
    elif duration_change_pct > 0:
        trend_label = f"⬆ DEGRADATION ({duration_change_pct:+.1f}% slower)"
    else:
        trend_label = f"⬇ IMPROVEMENT ({duration_change_pct:+.1f}% faster)"

    print(f"\nOverall Trend: {trend_label}")

    # Issues and recommendations
    issues = []

    if len(regressions) > 0:
        issues.append(f"⚠ {len(regressions)} test regressions detected (threshold: >{regression_threshold_pct:.0f}% or >{format_duration(regression_threshold_abs)})")

    if len(log_files) >= 3:
        high_volatility = sum(1 for _, m in test_trends.items() if m['cv'] and m['cv'] > 50)
        if high_volatility > 0:
            issues.append(f"⚠ {high_volatility} tests are highly volatile (CV > 50%)")

    if len(improvements) > 0:
        issues.append(f"✓ {len(improvements)} tests improved significantly")

    if len(new_tests) > 0:
        issues.append(f"ℹ {len(new_tests)} new tests added")

    if len(removed_tests) > 0:
        issues.append(f"ℹ {len(removed_tests)} tests removed")

    if issues:
        print("\nFindings:")
        for issue in issues:
            print(f"  {issue}")

    # Recommendations
    recommendations = []

    if len(regressions) > 0:
        top_regressions = regressions[:5]
        total_top_impact = sum(m['absolute_change'] for _, m in top_regressions)
        recommendations.append(f"Investigate top {len(top_regressions)} regressions - they account for {format_duration(total_top_impact)} of added time")

    if len(new_tests) > 10:
        recommendations.append(f"Review new tests - {len(new_tests)} tests added contribute {format_duration(total_new_time)}")

    if len(log_files) >= 3:
        high_volatility_tests = [(name, m) for name, m in test_trends.items() if m['cv'] and m['cv'] > 50]
        if high_volatility_tests:
            recommendations.append("Consider stabilizing tests with high variance for more predictable CI times")

    if duration_change_pct > 10:
        recommendations.append(f"Overall test suite is {duration_change_pct:.1f}% slower - consider optimization effort")

    if recommendations:
        print("\nRecommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

    if not issues and not recommendations:
        print("\n✓ Test suite performance is stable - no significant issues detected!")

    # Critical regressions to investigate (if any major ones)
    critical_regressions = [(name, m) for name, m in regressions
                           if m['relative_change'] > 50 or m['absolute_change'] > 30]

    if critical_regressions:
        print("\nCritical regressions to investigate immediately:")
        for i, (test_name, metrics) in enumerate(critical_regressions[:5], 1):
            print(f"  {i}. {test_name} "
                  f"({format_change(metrics['absolute_change'], metrics['relative_change'])})")


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python analyze_trends.py <log_file1> <log_file2> [log_file3 ...] [OPTIONS]")
        print("\nAnalyzes test duration trends across multiple log files.")
        print("Log files should be provided in chronological order (oldest to newest).")
        print("\nExamples:")
        print("  python analyze_trends.py logs/baseline.log logs/current.log")
        print("  python analyze_trends.py logs/run1.log logs/run2.log logs/run3.log logs/run4.log")
        print("  python analyze_trends.py logs/150 logs/176 --threshold-pct 15 --threshold-abs 3")
        print("\nOptions:")
        print("  --show-details       Show detailed information for all items")
        print("  --threshold-pct N    Set percentage threshold for regression detection (default: 20)")
        print("  --threshold-abs N    Set absolute threshold in seconds for regression (default: 5)")
        sys.exit(1)

    log_files = []
    show_details = False
    regression_threshold_pct = 20.0
    regression_threshold_abs = 5.0

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg == '--show-details':
            show_details = True
        elif arg == '--threshold-pct':
            if i + 1 < len(sys.argv):
                try:
                    regression_threshold_pct = float(sys.argv[i + 1])
                    i += 1
                except ValueError:
                    print(f"Error: Invalid value for --threshold-pct: {sys.argv[i + 1]}")
                    sys.exit(1)
            else:
                print("Error: --threshold-pct requires a value")
                sys.exit(1)
        elif arg == '--threshold-abs':
            if i + 1 < len(sys.argv):
                try:
                    regression_threshold_abs = float(sys.argv[i + 1])
                    i += 1
                except ValueError:
                    print(f"Error: Invalid value for --threshold-abs: {sys.argv[i + 1]}")
                    sys.exit(1)
            else:
                print("Error: --threshold-abs requires a value")
                sys.exit(1)
        else:
            log_files.append(arg)

        i += 1

    if len(log_files) < 2:
        print("Error: At least 2 log files are required for trend analysis.")
        sys.exit(1)

    try:
        analyze_trends(log_files, show_details, regression_threshold_pct, regression_threshold_abs)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
