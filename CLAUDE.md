# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based test duration analysis tool designed to parse and analyze QuestDB test execution logs. It extracts test durations from CI/CD pipeline logs (Azure Pipelines format) and provides statistical insights about test performance.

## Architecture

**Core Scripts**: Both are standalone Python 3 scripts with no external dependencies

1. **`analyze_tests.py`** - Individual test duration analysis
   - Log Parsing: Extracts test completion markers from CI logs using regex
   - Data Processing: Sorts and aggregates individual test durations
   - Statistical Analysis: Computes total/avg/max/min durations and threshold breakdowns
   - Reporting: Shows longest running individual tests

2. **`analyze_by_package.py`** - Package-level duration analysis for parallel execution planning
   - Log Parsing: Reuses same parsing logic as `analyze_tests.py`
   - Package Extraction: Extracts Java package names from fully qualified test names
   - Aggregation: Groups and sums test durations by package
   - Distribution Analysis: Shows cumulative distribution to identify heavy packages
   - Parallel Planning: Uses greedy bin packing algorithm to suggest optimal package distribution across runners

**Log Format**: The parser expects lines in the format:
```
<<<<= [test_name] duration_ms=[milliseconds]
```
Example: `<<<<= com.questdb.acl.AccessControlConcurrentTest.testRevokeAllConcurrentTableLevel[WITH_WAL] duration_ms=4001`

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

The package analysis script outputs:
- Total duration per package with test counts
- Cumulative distribution showing which packages account for most test time
- Parallel execution suggestions for 2, 4, and 8 runners using greedy bin packing

## Code Structure

**`analyze_tests.py` functions:**
- `parse_test_durations()`: Parses log file and extracts test names with durations
- `format_duration()`: Converts seconds to human-readable format (e.g., "2m 30.45s")
- `analyze_tests()`: Main analysis function that displays statistics and breakdowns
- `main()`: Entry point handling CLI arguments and error handling

**`analyze_by_package.py` functions:**
- `parse_test_durations()`: Parses log file (same logic as `analyze_tests.py`)
- `extract_package()`: Extracts Java package name from full test name (e.g., `com.questdb.acl` from `com.questdb.acl.TestClass.testMethod[params]`)
- `group_by_package()`: Aggregates test durations by package, returns dict with total_duration, test_count, and test list
- `format_duration()`: Shared duration formatting utility
- `analyze_by_package()`: Main analysis showing package statistics, cumulative distribution, and parallel execution suggestions
- `main()`: Entry point with support for `--show-tests` flag

## Key Implementation Details

**Regex Pattern**: `r'<<<<= (.+?)\s+duration_ms=(\d+)'` captures test names and millisecond durations

**Package Extraction Logic** (`analyze_by_package.py`):
- Strips parameter notation (e.g., `[WITH_WAL]`)
- Splits by dots and removes last two parts (ClassName and methodName)
- Example: `com.questdb.acl.AccessControlTest.testMethod[WITH_WAL]` → `com.questdb.acl`

**Parallel Execution Algorithm** (`analyze_by_package.py`):
- Uses greedy bin packing to distribute packages across runners
- Assigns each package to the runner with the current lowest total duration
- Aims to balance total duration across all runners

**Duration Thresholds** (`analyze_tests.py`): Tests are categorized by duration:
- Over 1 minute (60s)
- Over 2 minutes (120s)
- Over 5 minutes (300s)
- Over 10 minutes (600s)

**Error Handling**: Both scripts use `errors='ignore'` when reading log files to handle encoding issues in large CI logs
