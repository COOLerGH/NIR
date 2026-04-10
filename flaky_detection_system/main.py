"""
Точка входа системы детектирования flaky-тестов.

Использование:
    python main.py detect [--runs N] [--workers N]
    python main.py analyze [--input FILE]
    python main.py quarantine [--add NODE_ID] [--remove NODE_ID] [--list]
    python main.py report [--format FORMAT]
    python main.py run-all
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from config import (
    ensure_directories,
    load_thresholds,
    RESULTS_DIR,
    TESTS_DIR,
    DEFAULT_RUNS,
    DEFAULT_WORKERS,
)
from detector import TestRunner, ResultsParser, FlakyAnalyzer, FlakyClassifier
from detector.runner import RunConfig
from quarantine import QuarantineManager, TestMarker, ConfigUpdater
from reports import StatsAggregator, ReportExporter


def cmd_detect(args) -> int:
    """Запустить детектирование flaky-тестов."""
    print(f"Starting flaky test detection...")
    print(f"  Runs: {args.runs}")
    print(f"  Workers: {args.workers}")
    print(f"  Test path: {args.path or TESTS_DIR}")

    config = RunConfig(
        runs=args.runs,
        workers=args.workers,
        randomize_order=True,
    )
    runner = TestRunner(config)

    try:
        if args.multi_order:
            print(f"\nRunning tests in {args.runs} different orders...")
            results = runner.run_multiple_orders(args.path, num_orders=args.runs)
            print(f"Completed {len(results)} runs")
            
            for i, result in enumerate(results):
                status = "OK" if result.success else "FAILED"
                print(f"  Run {i + 1}: {status} ({result.duration:.2f}s)")
        else:
            print("\nRunning tests with flakefinder...")
            result = runner.run(args.path)
            
            if result.success:
                print(f"Tests completed successfully in {result.duration:.2f}s")
            else:
                print(f"Tests completed with failures in {result.duration:.2f}s")
            
            print(f"Results saved to: {result.output_file}")

    except Exception as e:
        print(f"Error during detection: {e}")
        return 1

    return 0


def cmd_analyze(args) -> int:
    """Анализировать результаты прогонов."""
    print("Analyzing test results...")

    if args.input:
        result_files = [Path(args.input)]
    else:
        result_files = list(RESULTS_DIR.glob("*.json"))
        result_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        result_files = result_files[:args.last]

    if not result_files:
        print("No result files found")
        return 1

    print(f"Analyzing {len(result_files)} result file(s)...")

    parser = ResultsParser()
    reports = parser.parse_multiple(result_files)

    if not reports:
        print("Failed to parse result files")
        return 1

    test_histories = parser.get_test_histories()
    print(f"Found {len(test_histories)} unique tests")

    analyzer = FlakyAnalyzer()
    analysis = analyzer.analyze_from_results(test_histories)

    print(f"\nAnalysis Results:")
    print(f"  Flaky tests: {len(analysis.flaky_tests)}")
    print(f"  Order-dependent: {len(analysis.order_dependent_tests)}")
    print(f"  Polluters: {len(analysis.polluters)}")
    print(f"  Victims: {len(analysis.victims)}")

    if analysis.flaky_tests:
        classifier = FlakyClassifier()
        classification = classifier.classify(test_histories, analysis)

        print(f"\nClassification by type:")
        for flaky_type, count in classification.summary.items():
            if count > 0:
                print(f"  {flaky_type.value}: {count}")

        print(f"\nFlaky tests details:")
        for cls in classification.classifications:
            print(f"  - {cls.name}")
            print(f"    Type: {cls.flaky_type.value}")
            print(f"    Confidence: {cls.confidence:.2f}")
            if cls.reasons:
                print(f"    Reasons: {', '.join(cls.reasons[:2])}")

    return 0


def cmd_quarantine(args) -> int:
    """Управление карантином тестов."""
    manager = QuarantineManager()

    if args.list:
        active = manager.get_active()
        if not active:
            print("No tests in quarantine")
            return 0

        print(f"Quarantined tests ({len(active)}):")
        for test in active:
            print(f"  - {test.name}")
            print(f"    Node ID: {test.node_id}")
            print(f"    Reason: {test.reason}")
            print(f"    Type: {test.flaky_type}")
            print(f"    Days remaining: {test.days_remaining()}")
        return 0

    if args.add:
        test = manager.add(
            node_id=args.add,
            name=args.add.split("::")[-1],
            reason=args.reason or "Manually added",
            flaky_type=args.type or "unknown",
        )
        print(f"Added to quarantine: {test.name}")
        print(f"  Expires: {test.expire_date[:10]}")
        return 0

    if args.remove:
        if manager.remove(args.remove):
            print(f"Removed from quarantine: {args.remove}")
        else:
            print(f"Test not found in quarantine: {args.remove}")
            return 1
        return 0

    if args.cleanup:
        expired = manager.cleanup_expired()
        if expired:
            print(f"Cleaned up {len(expired)} expired tests:")
            for node_id in expired:
                print(f"  - {node_id}")
        else:
            print("No expired tests to clean up")
        return 0

    if args.apply:
        active = manager.get_active()
        if not active:
            print("No tests to apply quarantine to")
            return 0

        node_ids = [t.node_id for t in active]

        marker = TestMarker()
        results = marker.mark_tests(node_ids, marker="flaky", reruns=3)

        success = sum(1 for r in results if r.success)
        print(f"Applied quarantine markers: {success}/{len(results)}")

        updater = ConfigUpdater()
        result = updater.update_pytest_ini(node_ids)
        print(f"Updated pytest.ini: {result.action}")

        return 0

    if args.generate_config:
        active = manager.get_active()
        node_ids = [t.node_id for t in active]

        updater = ConfigUpdater()

        result = updater.generate_workflow(node_ids)
        print(f"Generated workflow: {result.file_path}")

        result = updater.generate_deselect_file(node_ids)
        print(f"Generated deselect file: {result.file_path}")

        return 0

    print("No action specified. Use --list, --add, --remove, --cleanup, --apply, or --generate-config")
    return 1


def cmd_report(args) -> int:
    """Сгенерировать отчёты."""
    print("Generating reports...")

    result_files = list(RESULTS_DIR.glob("*.json"))
    result_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    result_files = result_files[:args.last]

    if not result_files:
        print("No result files found")
        return 1

    parser = ResultsParser()
    reports = parser.parse_multiple(result_files)
    test_histories = parser.get_test_histories()

    analyzer = FlakyAnalyzer()
    analysis = analyzer.analyze_from_results(test_histories)

    classifier = FlakyClassifier()
    classification = classifier.classify(test_histories, analysis)

    quarantine = QuarantineManager()

    aggregator = StatsAggregator()
    stats = aggregator.aggregate(
        test_histories=test_histories,
        reports=reports,
        analysis=analysis,
        classification=classification,
        quarantine=quarantine,
    )

    exporter = ReportExporter()

    if args.format == "all":
        results = exporter.export_all(stats, classification, quarantine)
        for result in results:
            status = "OK" if result.success else "FAILED"
            print(f"  {result.format}: {status} -> {result.file_path}")
    elif args.format == "json":
        result = exporter.export_json(stats, classification, quarantine)
        print(f"Exported: {result.file_path}")
    elif args.format == "html":
        result = exporter.export_html(stats, classification, quarantine)
        print(f"Exported: {result.file_path}")
    elif args.format == "allure":
        result = exporter.export_allure_results(stats, classification)
        print(f"Exported: {result.file_path}")
    else:
        result = exporter.export_summary(stats)
        print(f"Exported: {result.file_path}")

    print(f"\nSummary:")
    print(f"  Total tests: {stats.total_tests}")
    print(f"  Flaky tests: {stats.flaky_count}")
    print(f"  Flaky rate: {stats.flaky_rate * 100:.1f}%")
    print(f"  Pass rate: {stats.pass_rate * 100:.1f}%")

    return 0


def cmd_run_all(args) -> int:
    """Запустить полный цикл: детектирование, анализ, карантин, отчёт."""
    print("=" * 60)
    print("FLAKY TEST DETECTION - FULL CYCLE")
    print("=" * 60)

    ensure_directories()

    print("\n[1/4] Detection")
    print("-" * 40)

    config = RunConfig(
        runs=args.runs,
        workers=args.workers,
        randomize_order=True,
    )
    runner = TestRunner(config)

    results = runner.run_multiple_orders(num_orders=args.runs)

    # # DEBUG
    # print(f"DEBUG: results count = {len(results)}")
    # for i, r in enumerate(results):
    #     print(f"  Run {i}: success={r.success}, output={r.output_file}, exists={r.output_file.exists()}")
    #     if r.stderr:
    #         print(f"    STDERR: {r.stderr[:200]}")

    
    # Проверяем успешность по наличию output_file
    successful_runs = sum(1 for r in results if r.output_file.exists())
    print(f"Completed {successful_runs}/{len(results)} runs")

    print("\n[2/4] Analysis")
    print("-" * 40)

    result_files = runner.get_last_results(count=args.runs)

    if not result_files:
        print("No result files found")
        return 1

    parser = ResultsParser()
    reports = parser.parse_multiple(result_files)
    test_histories = parser.get_test_histories()

    flaky_tests = parser.get_flaky_tests()
    print(f"Found {len(flaky_tests)} flaky tests out of {len(test_histories)}")

    analyzer = FlakyAnalyzer()
    analysis = analyzer.analyze_from_results(test_histories)

    classifier = FlakyClassifier()
    classification = classifier.classify(test_histories, analysis)

    print("\n[3/4] Quarantine")
    print("-" * 40)

    quarantine = QuarantineManager()
    thresholds = load_thresholds()
    auto_quarantine = thresholds.get("quarantine", {}).get("auto_quarantine", True)

    if auto_quarantine and flaky_tests:
        for history in flaky_tests:
            if quarantine.is_quarantined(history.node_id):
                continue

            cls = classification.get_by_node_id(history.node_id)
            flaky_type = cls.flaky_type.value if cls else "unknown"
            confidence = cls.confidence if cls else 0.0

            quarantine.add(
                node_id=history.node_id,
                name=history.name,
                reason="Automatically detected as flaky",
                flaky_type=flaky_type,
                confidence=confidence,
                pass_rate=history.pass_rate,
                total_runs=history.total_runs,
            )
            print(f"  Quarantined: {history.name}")

        updater = ConfigUpdater()
        node_ids = quarantine.get_node_ids()
        updater.generate_deselect_file(node_ids)
        print(f"Updated deselect file with {len(node_ids)} tests")
    else:
        print("Auto-quarantine disabled or no flaky tests found")

    print("\n[4/4] Report Generation")
    print("-" * 40)

    aggregator = StatsAggregator()
    stats = aggregator.aggregate(
        test_histories=test_histories,
        reports=reports,
        analysis=analysis,
        classification=classification,
        quarantine=quarantine,
    )

    exporter = ReportExporter()
    export_results = exporter.export_all(stats, classification, quarantine)

    for result in export_results:
        if result.success:
            print(f"  {result.format}: {result.file_path}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total tests:      {stats.total_tests}")
    print(f"  Flaky tests:      {stats.flaky_count}")
    print(f"  Quarantined:      {stats.quarantined_count}")
    print(f"  Flaky rate:       {stats.flaky_rate * 100:.1f}%")
    print(f"  Pass rate:        {stats.pass_rate * 100:.1f}%")
    print("=" * 60)

    return 0


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Flaky Test Detection System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    detect_parser = subparsers.add_parser("detect", help="Run flaky test detection")
    detect_parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="Number of test runs")
    detect_parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Number of parallel workers")
    detect_parser.add_argument("--path", type=str, help="Path to tests")
    detect_parser.add_argument("--multi-order", action="store_true", help="Run tests in multiple orders")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze test results")
    analyze_parser.add_argument("--input", type=str, help="Input result file")
    analyze_parser.add_argument("--last", type=int, default=10, help="Analyze last N result files")

    quarantine_parser = subparsers.add_parser("quarantine", help="Manage test quarantine")
    quarantine_parser.add_argument("--list", action="store_true", help="List quarantined tests")
    quarantine_parser.add_argument("--add", type=str, help="Add test to quarantine")
    quarantine_parser.add_argument("--remove", type=str, help="Remove test from quarantine")
    quarantine_parser.add_argument("--reason", type=str, help="Reason for quarantine")
    quarantine_parser.add_argument("--type", type=str, help="Flaky type")
    quarantine_parser.add_argument("--cleanup", action="store_true", help="Clean up expired tests")
    quarantine_parser.add_argument("--apply", action="store_true", help="Apply quarantine to test files")
    quarantine_parser.add_argument("--generate-config", action="store_true", help="Generate CI config files")

    report_parser = subparsers.add_parser("report", help="Generate reports")
    report_parser.add_argument("--format", choices=["json", "html", "allure", "summary", "all"], default="all", help="Report format")
    report_parser.add_argument("--last", type=int, default=10, help="Use last N result files")

    run_all_parser = subparsers.add_parser("run-all", help="Run full detection cycle")
    run_all_parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="Number of test runs")
    run_all_parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Number of parallel workers")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    ensure_directories()

    commands = {
        "detect": cmd_detect,
        "analyze": cmd_analyze,
        "quarantine": cmd_quarantine,
        "report": cmd_report,
        "run-all": cmd_run_all,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
