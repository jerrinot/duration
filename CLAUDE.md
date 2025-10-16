# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based test duration analysis tool designed to parse and analyze QuestDB test execution logs. It extracts test durations from CI/CD pipeline logs (Azure Pipelines format) and provides statistical insights about test performance.

## Architecture

**Core Library**:
- **`duration_lib.py`** - Shared library module with no external dependencies containing all common functionality:
  - Parsing: `parse_test_durations()` - extracts test durations from log files
  - Formatting: `format_duration()` - converts seconds to human-readable format
  - Extraction: `extract_package()`, `extract_class()` - extracts grouping keys from test names
  - Grouping: `group_by()` - generic grouping function using custom extractors
  - Analysis: `calculate_cumulative_distribution()`, `suggest_parallel_splits()` - statistical analysis functions
  - Visualization: `print_histogram()` - ASCII histogram generation with smart bucketing

**Analysis Scripts**: All are standalone Python 3 scripts that import from `duration_lib.py`

1. **`analyze_tests.py`** - Individual test duration analysis
   - Displays statistics: total/avg/max/min durations
   - Shows longest running individual tests
   - Provides duration threshold breakdowns (1min, 2min, 5min, 10min)
   - Includes histogram visualization of test duration distribution

2. **`analyze_by_package.py`** - Package-level duration analysis for parallel execution planning
   - Groups tests by Java package name
   - Shows cumulative distribution to identify heavy packages
   - Uses greedy bin packing algorithm to suggest optimal package distribution across runners
   - Includes histogram visualization of package duration distribution

3. **`analyze_by_class.py`** - Class-level duration analysis for parallel execution planning
   - Groups tests by Java test class (package + class name)
   - Shows cumulative distribution to identify heavy test classes
   - Uses greedy bin packing algorithm to suggest optimal class distribution across runners
   - Includes histogram visualization of class duration distribution

4. **`analyze_duplicates.py`** - Multi-log duplicate detection for validating parallel splits
   - Detects overlapping tests across multiple log files (same test running in multiple places)
   - Analyzes duplicates at test, class, and package levels
   - Calculates wasted time from duplicate test executions
   - Evaluates load balance across runners
   - Provides recommendations for clean test distribution

**Testing**:
- **`test_duration_lib.py`** - Comprehensive unit tests for `duration_lib.py` using Python's unittest framework

**Log Format**: The parser expects lines in one of these formats:
```
<<<<= [test_name] duration_ms=[milliseconds]
<<<< [test_name] duration_ms=[milliseconds]
```
Example: `<<<<= com.questdb.acl.AccessControlConcurrentTest.testRevokeAllConcurrentTableLevel[WITH_WAL] duration_ms=4001`

The parser automatically detects and handles both formats, and includes duplicate detection to only keep the first occurrence of each test.

**Input Files**: Log files (like `176` and `404`) are Azure Pipelines CI logs containing test execution output with duration markers. These logs use CRLF line terminators and can contain very long lines (2000+ characters).

## Usage

**Individual test analysis:**
```bash
python3 analyze_tests.py <log_file> [top_n]
```

- `log_file`: Path to the CI log file to analyze
- `top_n`: Optional number of longest tests to display (default: 20)

Example:
```bash
python3 analyze_tests.py 176 50
```

**Package-level analysis (for parallel execution planning):**
```bash
python3 analyze_by_package.py <log_file> [top_n] [--show-tests]
```

- `log_file`: Path to the CI log file to analyze
- `top_n`: Optional number of top packages to display (default: 20)
- `--show-tests`: Show the top 5 slowest tests within each package

Examples:
```bash
python3 analyze_by_package.py 176 30
python3 analyze_by_package.py 176 15 --show-tests
```

**Class-level analysis (for parallel execution planning):**
```bash
python3 analyze_by_class.py <log_file> [top_n] [--show-tests]
```

- `log_file`: Path to the CI log file to analyze
- `top_n`: Optional number of top classes to display (default: 20)
- `--show-tests`: Show the top 5 slowest tests within each class

Examples:
```bash
python3 analyze_by_class.py 150 30
python3 analyze_by_class.py 150 15 --show-tests
```

**Duplicate detection (validate parallel splits):**
```bash
python3 analyze_duplicates.py <log_file1> <log_file2> [log_file3 ...] [--show-details]
```

- `log_file1`, `log_file2`, etc.: Paths to log files from different runners/splits
- `--show-details`: Show detailed lists of duplicate items

Examples:
```bash
python3 analyze_duplicates.py runner1.log runner2.log runner3.log
python3 analyze_duplicates.py logs/shard*.log --show-details
```

**Running tests:**
```bash
python3 test_duration_lib.py
python3 test_duration_lib.py -v  # verbose output
```

The package and class analysis scripts output:
- Histogram showing duration distribution across packages/classes
- Total duration per package/class with test counts and average duration per test
- Cumulative distribution showing which packages/classes account for most test time
- Parallel execution suggestions for 2, 4, and 8 runners using greedy bin packing

The duplicate detection script outputs:
- Overall statistics (unique tests/classes/packages, total duration)
- Test-level analysis showing duplicate tests and wasted time
- Class-level analysis showing classes split across logs
- Package-level analysis showing packages split across logs
- Distribution analysis comparing test counts and durations across logs
- Balance metrics (balance ratio, max/min/avg durations)
- Summary with actionable recommendations for improving test distribution

## Code Structure

**`duration_lib.py` functions (shared library):**
- `parse_test_durations(log_file)`: Parses log file and extracts test names with durations; handles both `<<<<= ` and `<<<< ` formats; includes duplicate detection
- `format_duration(seconds)`: Converts seconds to human-readable format (e.g., "2m 30.45s", "1h 15m 30.00s")
- `extract_package(test_name)`: Extracts Java package name (e.g., `com.questdb.acl` from `com.questdb.acl.TestClass.testMethod[params]`)
- `extract_class(test_name)`: Extracts Java class name (e.g., `com.questdb.acl.TestClass` from `com.questdb.acl.TestClass.testMethod[params]`)
- `group_by(durations, extractor)`: Generic grouping function using a custom extraction function; returns dict with total_duration, test_count, and test list
- `calculate_cumulative_distribution(sorted_items, thresholds, total_duration)`: Calculates cumulative distribution for specified percentage thresholds
- `suggest_parallel_splits(sorted_items, num_runners, total_duration)`: Uses greedy bin packing to suggest how to split items across parallel runners
- `print_histogram(durations, title, bar_width, num_buckets)`: Prints ASCII histogram with smart bucket sizing
- `_create_smart_buckets(min_val, max_val, target_buckets)`: Helper to create histogram buckets with nice round numbers
- `_nice_number(value)`: Helper to round values to nice numbers for histogram labels

**`analyze_tests.py` functions:**
- `analyze_tests(log_file, top_n)`: Main analysis function displaying individual test statistics, histogram, and duration breakdowns
- `main()`: Entry point handling CLI arguments and error handling

**`analyze_by_package.py` functions:**
- `analyze_by_package(log_file, top_n, show_tests)`: Main analysis showing package statistics, histogram, cumulative distribution, and parallel execution suggestions
- `main()`: Entry point with support for `--show-tests` flag

**`analyze_by_class.py` functions:**
- `analyze_by_class(log_file, top_n, show_tests)`: Main analysis showing class-level statistics, histogram, cumulative distribution, and parallel execution suggestions
- `main()`: Entry point with support for `--show-tests` flag

**`analyze_duplicates.py` functions:**
- `analyze_duplicates(log_files, show_details)`: Main analysis detecting duplicate tests across multiple log files; reports at test, class, and package levels; calculates balance metrics and wasted time
- `main()`: Entry point handling multiple log file arguments and `--show-details` flag

**`test_duration_lib.py` test classes:**
- `TestParsing`: Tests for `parse_test_durations()` including edge cases and multiple log formats
- `TestFormatDuration`: Tests for duration formatting in seconds, minutes, and hours
- `TestExtraction`: Tests for `extract_package()` and `extract_class()` functions
- `TestGrouping`: Tests for the generic `group_by()` function
- `TestCumulativeDistribution`: Tests for cumulative distribution calculations
- `TestParallelExecution`: Tests for greedy bin packing algorithm

## Key Implementation Details

**Regex Pattern**: `r'<<<<[=]?\s+(.+?)\s+duration_ms=(\d+)'` - captures test names and millisecond durations from both `<<<<= ` and `<<<< ` log formats

**Duplicate Detection** (`duration_lib.parse_test_durations`):
- Tracks seen test names to avoid duplicates
- Only keeps the first occurrence of each test
- Uses a dictionary to efficiently detect duplicates during parsing

**Package Extraction Logic** (`duration_lib.extract_package`):
- Strips parameter notation (e.g., `[WITH_WAL]`)
- Splits by dots and removes last two parts (ClassName and methodName)
- Example: `com.questdb.acl.AccessControlTest.testMethod[WITH_WAL]` → `com.questdb.acl`
- Handles edge cases where test names have fewer than 3 parts

**Class Extraction Logic** (`duration_lib.extract_class`):
- Strips parameter notation (e.g., `[WITH_WAL]`)
- Splits by dots and removes last part (methodName)
- Example: `com.questdb.acl.AccessControlTest.testMethod[WITH_WAL]` → `com.questdb.acl.AccessControlTest`

**Generic Grouping** (`duration_lib.group_by`):
- Accepts a custom extraction function for flexible grouping
- Used by both package and class analysis scripts
- Returns dict with total_duration, test_count, and test list for each group

**Parallel Execution Algorithm** (`duration_lib.suggest_parallel_splits`):
- Uses greedy bin packing to distribute items across runners
- Assigns each item to the runner with the current lowest total duration
- Aims to balance total duration across all runners
- Works for both package-level and class-level splits

**Histogram Visualization** (`duration_lib.print_histogram`):
- Automatically determines smart bucket ranges based on data distribution
- Uses "nice" round numbers for bucket boundaries (1, 2, 5, 10, 15, 30, 60, etc.)
- Adapts units based on data range (seconds, minutes, or hours)
- Coalesces consecutive empty buckets to save space
- Scales bar width based on maximum count

**Duration Thresholds** (`analyze_tests.py`): Tests are categorized by duration:
- Over 1 minute (60s)
- Over 2 minutes (120s)
- Over 5 minutes (300s)
- Over 10 minutes (600s)

**Duplicate Detection Algorithm** (`analyze_duplicates.py`):
- Parses multiple log files and tracks test occurrences across all files
- Uses dictionaries to map test names/classes/packages to the log files they appear in
- Identifies items appearing in 2+ logs (duplicates) at test, class, and package granularity
- Calculates wasted time by multiplying test duration by (occurrences - 1)
- Computes balance ratio as min_duration/max_duration (1.0 = perfect balance)
- Provides actionable recommendations based on findings

**Error Handling**: All scripts use `errors='ignore'` when reading log files to handle encoding issues in large CI logs
