# Test Duration Analysis Tools

A collection of Python scripts for analyzing test execution logs from CI/CD pipelines. These tools parse Azure Pipelines log files to extract test durations and provide statistical insights for optimizing test execution.

## Tools

### analyze_tests.py
Analyzes individual test durations from a single log file. Displays statistics including total/average/min/max durations, shows the longest running tests, and provides a histogram of duration distribution with threshold breakdowns.

### analyze_by_package.py
Groups tests by Java package name and calculates aggregate durations. Useful for planning parallel execution splits at the package level. Includes cumulative distribution analysis and greedy bin packing suggestions for distributing packages across multiple runners.

### analyze_by_class.py
Groups tests by Java class name (package + class) and calculates aggregate durations. Provides class-level analysis for parallel execution planning, similar to package-level analysis but with finer granularity.

### analyze_duplicates.py
Validates parallel execution splits by detecting duplicate tests across multiple log files. Identifies tests, classes, or packages that appear in multiple logs, calculates wasted time from duplicates, and evaluates load balance across runners.

### analyze_trends.py
Compares multiple log files in chronological order to track performance changes over time. Detects performance regressions and improvements, identifies new and removed tests, calculates volatility metrics for unstable tests, and provides prioritized recommendations for optimization.

## Usage

All scripts follow a similar pattern:

```bash
python3 analyze_tests.py <log_file> [options]
python3 analyze_by_package.py <log_file> [options]
python3 analyze_by_class.py <log_file> [options]
python3 analyze_duplicates.py <log_file1> <log_file2> [log_file3 ...] [options]
python3 analyze_trends.py <log_file1> <log_file2> [log_file3 ...] [options]
```

Run any script without arguments to see detailed usage information.

## Requirements

Python 3.6 or higher. No external dependencies required.

## Log Format

Log files must contain test completion markers in the format:
```
<<<<= test.package.ClassName.methodName duration_ms=1234
```

Both `<<<<= ` and `<<<< ` formats are supported.
