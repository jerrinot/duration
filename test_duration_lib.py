#!/usr/bin/env python3
"""
Unit tests for duration_lib module.
Tests are written first following TDD principles.
"""
import unittest
import tempfile
import os
from typing import List, Tuple


class TestParsing(unittest.TestCase):
    """Tests for parse_test_durations function."""

    def test_parse_single_test(self):
        """Test parsing a single test duration."""
        from duration_lib import parse_test_durations

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write('<<<<= com.questdb.acl.Test.testMethod duration_ms=1000\n')
            f.flush()

            durations = parse_test_durations(f.name)
            self.assertEqual(len(durations), 1)
            self.assertEqual(durations[0][0], 'com.questdb.acl.Test.testMethod')
            self.assertEqual(durations[0][1], 1.0)  # 1000ms = 1.0s

            os.unlink(f.name)

    def test_parse_multiple_tests(self):
        """Test parsing multiple test durations."""
        from duration_lib import parse_test_durations

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write('Some log line\n')
            f.write('<<<<= com.questdb.Test1.test1 duration_ms=1500\n')
            f.write('Another log line\n')
            f.write('<<<<= com.questdb.Test2.test2 duration_ms=2500\n')
            f.flush()

            durations = parse_test_durations(f.name)
            self.assertEqual(len(durations), 2)
            self.assertEqual(durations[0], ('com.questdb.Test1.test1', 1.5))
            self.assertEqual(durations[1], ('com.questdb.Test2.test2', 2.5))

            os.unlink(f.name)

    def test_parse_with_parameters(self):
        """Test parsing tests with parameters like [WITH_WAL]."""
        from duration_lib import parse_test_durations

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write('<<<<= com.questdb.Test.method[WITH_WAL] duration_ms=3000\n')
            f.flush()

            durations = parse_test_durations(f.name)
            self.assertEqual(len(durations), 1)
            self.assertEqual(durations[0][0], 'com.questdb.Test.method[WITH_WAL]')
            self.assertEqual(durations[0][1], 3.0)

            os.unlink(f.name)

    def test_parse_empty_file(self):
        """Test parsing an empty file."""
        from duration_lib import parse_test_durations

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.flush()

            durations = parse_test_durations(f.name)
            self.assertEqual(len(durations), 0)

            os.unlink(f.name)

    def test_parse_no_test_lines(self):
        """Test parsing a file with no test duration markers."""
        from duration_lib import parse_test_durations

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write('This is a log line\n')
            f.write('Another line without test markers\n')
            f.flush()

            durations = parse_test_durations(f.name)
            self.assertEqual(len(durations), 0)

            os.unlink(f.name)


class TestFormatDuration(unittest.TestCase):
    """Tests for format_duration function."""

    def test_format_seconds(self):
        """Test formatting durations less than 60 seconds."""
        from duration_lib import format_duration

        self.assertEqual(format_duration(0.5), "0.50s")
        self.assertEqual(format_duration(1.0), "1.00s")
        self.assertEqual(format_duration(30.25), "30.25s")
        self.assertEqual(format_duration(59.99), "59.99s")

    def test_format_minutes(self):
        """Test formatting durations in minutes."""
        from duration_lib import format_duration

        self.assertEqual(format_duration(60.0), "1m 0.00s")
        self.assertEqual(format_duration(90.5), "1m 30.50s")
        self.assertEqual(format_duration(125.75), "2m 5.75s")
        self.assertEqual(format_duration(3599.0), "59m 59.00s")

    def test_format_hours(self):
        """Test formatting durations in hours."""
        from duration_lib import format_duration

        self.assertEqual(format_duration(3600.0), "1h 0m 0.00s")
        self.assertEqual(format_duration(3661.5), "1h 1m 1.50s")
        self.assertEqual(format_duration(7384.25), "2h 3m 4.25s")

    def test_format_zero(self):
        """Test formatting zero duration."""
        from duration_lib import format_duration

        self.assertEqual(format_duration(0.0), "0.00s")


class TestExtraction(unittest.TestCase):
    """Tests for name extraction functions."""

    def test_extract_package(self):
        """Test extracting package name from full test name."""
        from duration_lib import extract_package

        # Standard test name
        self.assertEqual(
            extract_package('com.questdb.acl.Test.method'),
            'com.questdb.acl'
        )

        # With parameters
        self.assertEqual(
            extract_package('com.questdb.acl.Test.method[WITH_WAL]'),
            'com.questdb.acl'
        )

        # Deep package
        self.assertEqual(
            extract_package('com.company.project.module.Test.method'),
            'com.company.project.module'
        )

    def test_extract_package_edge_cases(self):
        """Test edge cases for package extraction."""
        from duration_lib import extract_package

        # Only 2 parts (no package)
        self.assertEqual(extract_package('Test.method'), 'Test.method')

        # Only 1 part
        self.assertEqual(extract_package('Test'), 'Test')

    def test_extract_class(self):
        """Test extracting class name from full test name."""
        from duration_lib import extract_class

        # Standard test name
        self.assertEqual(
            extract_class('com.questdb.acl.Test.method'),
            'com.questdb.acl.Test'
        )

        # With parameters
        self.assertEqual(
            extract_class('com.questdb.acl.Test.method[WITH_WAL]'),
            'com.questdb.acl.Test'
        )

        # Deep package
        self.assertEqual(
            extract_class('com.company.project.module.TestClass.testMethod'),
            'com.company.project.module.TestClass'
        )

    def test_extract_class_edge_cases(self):
        """Test edge cases for class extraction."""
        from duration_lib import extract_class

        # Only 1 part (no method)
        self.assertEqual(extract_class('Test'), 'Test')


class TestGrouping(unittest.TestCase):
    """Tests for grouping functions."""

    def test_group_by_function(self):
        """Test generic grouping with custom extraction function."""
        from duration_lib import group_by

        durations = [
            ('com.questdb.acl.Test1.method1', 1.0),
            ('com.questdb.acl.Test1.method2', 2.0),
            ('com.questdb.acl.Test2.method1', 3.0),
        ]

        # Group by class (extract all but last part)
        extractor = lambda name: '.'.join(name.split('.')[:-1])
        groups = group_by(durations, extractor)

        self.assertEqual(len(groups), 2)
        self.assertIn('com.questdb.acl.Test1', groups)
        self.assertIn('com.questdb.acl.Test2', groups)

        # Check Test1 group
        self.assertEqual(groups['com.questdb.acl.Test1']['total_duration'], 3.0)
        self.assertEqual(groups['com.questdb.acl.Test1']['test_count'], 2)
        self.assertEqual(len(groups['com.questdb.acl.Test1']['tests']), 2)

        # Check Test2 group
        self.assertEqual(groups['com.questdb.acl.Test2']['total_duration'], 3.0)
        self.assertEqual(groups['com.questdb.acl.Test2']['test_count'], 1)

    def test_group_by_empty(self):
        """Test grouping with empty list."""
        from duration_lib import group_by

        groups = group_by([], lambda x: x)
        self.assertEqual(len(groups), 0)


class TestCumulativeDistribution(unittest.TestCase):
    """Tests for cumulative distribution calculation."""

    def test_calculate_cumulative_distribution(self):
        """Test cumulative distribution calculation."""
        from duration_lib import calculate_cumulative_distribution

        items = [
            ('item1', {'total_duration': 50.0}),
            ('item2', {'total_duration': 30.0}),
            ('item3', {'total_duration': 20.0}),
        ]

        thresholds = [25, 50, 75]
        total_duration = 100.0

        result = calculate_cumulative_distribution(items, thresholds, total_duration)

        # Result should be list of (count, percentage, cumulative_duration)
        # item1 (50%) crosses both 25% and 50% thresholds
        # item1+item2 (80%) crosses 75% threshold
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], (1, 50.0, 50.0))  # item1 hits 25% threshold
        self.assertEqual(result[1], (1, 50.0, 50.0))  # item1 hits 50% threshold
        self.assertEqual(result[2], (2, 80.0, 80.0))  # item1+item2 hits 75% threshold

    def test_cumulative_distribution_empty(self):
        """Test cumulative distribution with empty items."""
        from duration_lib import calculate_cumulative_distribution

        result = calculate_cumulative_distribution([], [25, 50, 75], 100.0)
        self.assertEqual(len(result), 0)


class TestParallelExecution(unittest.TestCase):
    """Tests for parallel execution bin packing algorithm."""

    def test_suggest_parallel_splits_simple(self):
        """Test parallel split suggestions with simple case."""
        from duration_lib import suggest_parallel_splits

        items = [
            ('item1', {'total_duration': 10.0}),
            ('item2', {'total_duration': 10.0}),
        ]

        splits = suggest_parallel_splits(items, 2, 20.0)

        # Should return 2 runners
        self.assertEqual(len(splits), 2)

        # Each runner should have 1 item
        self.assertEqual(len(splits[0]['items']), 1)
        self.assertEqual(len(splits[1]['items']), 1)

        # Each should have 10.0 duration
        self.assertEqual(splits[0]['duration'], 10.0)
        self.assertEqual(splits[1]['duration'], 10.0)

        # Percentages should be 50% each
        self.assertEqual(splits[0]['percentage'], 50.0)
        self.assertEqual(splits[1]['percentage'], 50.0)

    def test_suggest_parallel_splits_greedy(self):
        """Test that bin packing uses greedy algorithm correctly."""
        from duration_lib import suggest_parallel_splits

        items = [
            ('item1', {'total_duration': 5.0}),
            ('item2', {'total_duration': 3.0}),
            ('item3', {'total_duration': 2.0}),
        ]

        splits = suggest_parallel_splits(items, 2, 10.0)

        # Greedy should assign: item1->runner1, item2->runner2, item3->runner2
        # Runner 1: 5.0, Runner 2: 5.0
        self.assertEqual(splits[0]['duration'], 5.0)
        self.assertEqual(splits[1]['duration'], 5.0)

    def test_suggest_parallel_splits_more_runners_than_items(self):
        """Test with more runners than items."""
        from duration_lib import suggest_parallel_splits

        items = [
            ('item1', {'total_duration': 10.0}),
        ]

        splits = suggest_parallel_splits(items, 4, 10.0)

        # Should have 4 runners, but only first has items
        self.assertEqual(len(splits), 4)
        self.assertEqual(len(splits[0]['items']), 1)
        self.assertEqual(len(splits[1]['items']), 0)
        self.assertEqual(len(splits[2]['items']), 0)
        self.assertEqual(len(splits[3]['items']), 0)


if __name__ == '__main__':
    unittest.main()
