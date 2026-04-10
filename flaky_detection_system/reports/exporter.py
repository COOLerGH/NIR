"""
Модуль экспорта отчётов.

Генерирует отчёты в форматах JSON, HTML, Allure
на основе агрегированной статистики.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from config import REPORTS_DIR, ensure_directories
from reports.aggregator import AggregatedStats, TestStats
from detector.classifier import ClassificationResult, Classification
from quarantine.manager import QuarantineManager


@dataclass
class ExportResult:
    """Результат экспорта."""
    format: str
    file_path: Path
    success: bool
    message: str = ""


class ReportExporter:
    """Экспортёр отчётов."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or REPORTS_DIR
        ensure_directories()

    def export_all(
        self,
        stats: AggregatedStats,
        classification: Optional[ClassificationResult] = None,
        quarantine: Optional[QuarantineManager] = None
    ) -> List[ExportResult]:
        """
        Экспортировать отчёты во всех форматах.

        Args:
            stats: агрегированная статистика
            classification: результат классификации
            quarantine: менеджер карантина

        Returns:
            список ExportResult
        """
        results = []

        results.append(self.export_json(stats, classification, quarantine))
        results.append(self.export_html(stats, classification, quarantine))
        results.append(self.export_summary(stats))

        return results

    def export_json(
        self,
        stats: AggregatedStats,
        classification: Optional[ClassificationResult] = None,
        quarantine: Optional[QuarantineManager] = None
    ) -> ExportResult:
        """
        Экспортировать в JSON.

        Args:
            stats: агрегированная статистика
            classification: результат классификации
            quarantine: менеджер карантина

        Returns:
            ExportResult
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.output_dir / f"report_{timestamp}.json"

        data = self._build_json_data(stats, classification, quarantine)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return ExportResult(
                format="json",
                file_path=file_path,
                success=True,
                message=f"Exported JSON report to {file_path}",
            )
        except IOError as e:
            return ExportResult(
                format="json",
                file_path=file_path,
                success=False,
                message=f"Failed to export JSON: {e}",
            )

    def export_html(
        self,
        stats: AggregatedStats,
        classification: Optional[ClassificationResult] = None,
        quarantine: Optional[QuarantineManager] = None
    ) -> ExportResult:
        """
        Экспортировать в HTML.

        Args:
            stats: агрегированная статистика
            classification: результат классификации
            quarantine: менеджер карантина

        Returns:
            ExportResult
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.output_dir / f"report_{timestamp}.html"

        html_content = self._build_html_content(stats, classification, quarantine)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            return ExportResult(
                format="html",
                file_path=file_path,
                success=True,
                message=f"Exported HTML report to {file_path}",
            )
        except IOError as e:
            return ExportResult(
                format="html",
                file_path=file_path,
                success=False,
                message=f"Failed to export HTML: {e}",
            )

    def export_summary(self, stats: AggregatedStats) -> ExportResult:
        """
        Экспортировать краткую сводку.

        Args:
            stats: агрегированная статистика

        Returns:
            ExportResult
        """
        file_path = self.output_dir / "summary.json"

        summary = {
            "timestamp": stats.timestamp,
            "total_tests": stats.total_tests,
            "flaky_count": stats.flaky_count,
            "stable_count": stats.stable_count,
            "quarantined_count": stats.quarantined_count,
            "flaky_rate_percent": round(stats.flaky_rate * 100, 2),
            "pass_rate_percent": round(stats.pass_rate * 100, 2),
            "by_type": stats.by_type,
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)

            return ExportResult(
                format="summary",
                file_path=file_path,
                success=True,
                message=f"Exported summary to {file_path}",
            )
        except IOError as e:
            return ExportResult(
                format="summary",
                file_path=file_path,
                success=False,
                message=f"Failed to export summary: {e}",
            )

    def export_allure_results(
        self,
        stats: AggregatedStats,
        classification: Optional[ClassificationResult] = None
    ) -> ExportResult:
        """
        Экспортировать результаты в формате Allure.

        Args:
            stats: агрегированная статистика
            classification: результат классификации

        Returns:
            ExportResult
        """
        allure_dir = self.output_dir / "allure-results"
        allure_dir.mkdir(parents=True, exist_ok=True)

        try:
            for test_stat in stats.tests:
                if not test_stat.is_flaky:
                    continue

                result_file = allure_dir / f"{self._sanitize_name(test_stat.node_id)}-result.json"

                allure_result = self._build_allure_result(test_stat, classification)

                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump(allure_result, f, ensure_ascii=False, indent=2)

            return ExportResult(
                format="allure",
                file_path=allure_dir,
                success=True,
                message=f"Exported Allure results to {allure_dir}",
            )
        except IOError as e:
            return ExportResult(
                format="allure",
                file_path=allure_dir,
                success=False,
                message=f"Failed to export Allure results: {e}",
            )

    def _build_json_data(
        self,
        stats: AggregatedStats,
        classification: Optional[ClassificationResult],
        quarantine: Optional[QuarantineManager]
    ) -> Dict[str, Any]:
        """Построить данные для JSON-отчёта."""
        data = {
            "meta": {
                "timestamp": stats.timestamp,
                "generator": "flaky_detection_system",
                "version": "1.0.0",
            },
            "summary": {
                "total_tests": stats.total_tests,
                "total_runs": stats.total_runs,
                "total_duration_seconds": round(stats.total_duration, 2),
                "flaky_count": stats.flaky_count,
                "stable_count": stats.stable_count,
                "quarantined_count": stats.quarantined_count,
                "flaky_rate_percent": round(stats.flaky_rate * 100, 2),
                "pass_rate_percent": round(stats.pass_rate * 100, 2),
            },
            "by_type": stats.by_type,
            "trends": stats.trends,
            "tests": [],
        }

        for test_stat in stats.tests:
            test_data = {
                "node_id": test_stat.node_id,
                "name": test_stat.name,
                "total_runs": test_stat.total_runs,
                "passed": test_stat.passed,
                "failed": test_stat.failed,
                "pass_rate_percent": round(test_stat.pass_rate * 100, 2),
                "avg_duration_seconds": round(test_stat.avg_duration, 4),
                "is_flaky": test_stat.is_flaky,
                "flaky_type": test_stat.flaky_type,
                "is_quarantined": test_stat.is_quarantined,
            }

            if classification and test_stat.is_flaky:
                cls = classification.get_by_node_id(test_stat.node_id)
                if cls:
                    test_data["classification"] = {
                        "type": cls.flaky_type.value,
                        "confidence": cls.confidence,
                        "reasons": cls.reasons,
                        "recommendations": cls.recommendations,
                        "related_tests": cls.related_tests,
                    }

            data["tests"].append(test_data)

        if quarantine:
            data["quarantine"] = {
                "stats": quarantine.get_stats(),
                "tests": [
                    {
                        "node_id": t.node_id,
                        "reason": t.reason,
                        "added_date": t.added_date,
                        "expire_date": t.expire_date,
                        "days_remaining": t.days_remaining(),
                    }
                    for t in quarantine.get_active()
                ],
            }

        return data

    def _build_html_content(
        self,
        stats: AggregatedStats,
        classification: Optional[ClassificationResult],
        quarantine: Optional[QuarantineManager]
    ) -> str:
        """Построить HTML-отчёт."""
        flaky_tests_html = self._build_flaky_tests_table(stats, classification)
        quarantine_html = self._build_quarantine_section(quarantine)
        type_distribution_html = self._build_type_distribution(stats)

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flaky Tests Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1, h2, h3 {{
            color: #333;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card-title {{
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }}
        .card-value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .card-value.danger {{
            color: #dc3545;
        }}
        .card-value.success {{
            color: #28a745;
        }}
        .card-value.warning {{
            color: #ffc107;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background-color: #333;
            color: white;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-flaky {{
            background-color: #fff3cd;
            color: #856404;
        }}
        .badge-quarantined {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .badge-stable {{
            background-color: #d4edda;
            color: #155724;
        }}
        .badge-od {{
            background-color: #cce5ff;
            color: #004085;
        }}
        .progress-bar {{
            width: 100%;
            height: 20px;
            background-color: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background-color: #28a745;
        }}
        .section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .timestamp {{
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <h1>Flaky Tests Detection Report</h1>
    <p class="timestamp">Generated: {stats.timestamp}</p>

    <div class="summary-cards">
        <div class="card">
            <div class="card-title">Total Tests</div>
            <div class="card-value">{stats.total_tests}</div>
        </div>
        <div class="card">
            <div class="card-title">Flaky Tests</div>
            <div class="card-value danger">{stats.flaky_count}</div>
        </div>
        <div class="card">
            <div class="card-title">Stable Tests</div>
            <div class="card-value success">{stats.stable_count}</div>
        </div>
        <div class="card">
            <div class="card-title">Quarantined</div>
            <div class="card-value warning">{stats.quarantined_count}</div>
        </div>
        <div class="card">
            <div class="card-title">Flaky Rate</div>
            <div class="card-value danger">{round(stats.flaky_rate * 100, 1)}%</div>
        </div>
        <div class="card">
            <div class="card-title">Pass Rate</div>
            <div class="card-value success">{round(stats.pass_rate * 100, 1)}%</div>
        </div>
    </div>

    {type_distribution_html}

    <div class="section">
        <h2>Flaky Tests Details</h2>
        {flaky_tests_html}
    </div>

    {quarantine_html}
</body>
</html>
"""
        return html

    def _build_flaky_tests_table(
        self,
        stats: AggregatedStats,
        classification: Optional[ClassificationResult]
    ) -> str:
        """Построить таблицу flaky-тестов."""
        flaky_tests = [t for t in stats.tests if t.is_flaky]

        if not flaky_tests:
            return "<p>No flaky tests detected.</p>"

        rows = []
        for test in flaky_tests:
            badges = []
            if test.is_flaky:
                badges.append('<span class="badge badge-flaky">FLAKY</span>')
            if test.is_quarantined:
                badges.append('<span class="badge badge-quarantined">QUARANTINED</span>')
            if test.flaky_type == "order_dependent":
                badges.append('<span class="badge badge-od">ORDER-DEPENDENT</span>')

            recommendations = ""
            if classification:
                cls = classification.get_by_node_id(test.node_id)
                if cls and cls.recommendations:
                    recommendations = "<br>".join(f"- {r}" for r in cls.recommendations[:3])

            rows.append(f"""
                <tr>
                    <td>{test.name}</td>
                    <td>{' '.join(badges)}</td>
                    <td>{test.passed}/{test.total_runs}</td>
                    <td>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {test.pass_rate * 100}%"></div>
                        </div>
                        {round(test.pass_rate * 100, 1)}%
                    </td>
                    <td>{round(test.avg_duration * 1000, 1)} ms</td>
                    <td>{recommendations}</td>
                </tr>
            """)

        return f"""
        <table>
            <thead>
                <tr>
                    <th>Test Name</th>
                    <th>Status</th>
                    <th>Passed/Total</th>
                    <th>Pass Rate</th>
                    <th>Avg Duration</th>
                    <th>Recommendations</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """

    def _build_quarantine_section(
        self,
        quarantine: Optional[QuarantineManager]
    ) -> str:
        """Построить секцию карантина."""
        if not quarantine:
            return ""

        active = quarantine.get_active()
        if not active:
            return """
            <div class="section">
                <h2>Quarantine</h2>
                <p>No tests currently in quarantine.</p>
            </div>
            """

        rows = []
        for test in active:
            rows.append(f"""
                <tr>
                    <td>{test.name}</td>
                    <td>{test.reason}</td>
                    <td>{test.flaky_type}</td>
                    <td>{test.added_date[:10]}</td>
                    <td>{test.days_remaining()} days</td>
                </tr>
            """)

        return f"""
        <div class="section">
            <h2>Quarantine ({len(active)} tests)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Reason</th>
                        <th>Type</th>
                        <th>Added</th>
                        <th>Expires In</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """

    def _build_type_distribution(self, stats: AggregatedStats) -> str:
        """Построить секцию распределения по типам."""
        if not stats.by_type:
            return ""

        items = []
        for type_name, count in stats.by_type.items():
            items.append(f"<li><strong>{type_name}</strong>: {count}</li>")

        return f"""
        <div class="section">
            <h2>Distribution by Type</h2>
            <ul>
                {''.join(items)}
            </ul>
        </div>
        """

    def _build_allure_result(
        self,
        test_stat: TestStats,
        classification: Optional[ClassificationResult]
    ) -> Dict[str, Any]:
        """Построить результат в формате Allure."""
        labels = [
            {"name": "suite", "value": "Flaky Tests"},
            {"name": "severity", "value": "normal"},
        ]

        if test_stat.flaky_type:
            labels.append({"name": "tag", "value": test_stat.flaky_type})

        if test_stat.is_quarantined:
            labels.append({"name": "tag", "value": "quarantined"})

        description = f"Pass rate: {round(test_stat.pass_rate * 100, 1)}%"
        if classification:
            cls = classification.get_by_node_id(test_stat.node_id)
            if cls:
                description += f"\n\nType: {cls.flaky_type.value}"
                description += f"\nConfidence: {cls.confidence}"
                if cls.reasons:
                    description += "\n\nReasons:\n" + "\n".join(f"- {r}" for r in cls.reasons)

        return {
            "uuid": self._sanitize_name(test_stat.node_id),
            "name": test_stat.name,
            "status": "broken" if test_stat.is_flaky else "passed",
            "stage": "finished",
            "description": description,
            "labels": labels,
            "parameters": [
                {"name": "total_runs", "value": str(test_stat.total_runs)},
                {"name": "passed", "value": str(test_stat.passed)},
                {"name": "failed", "value": str(test_stat.failed)},
            ],
        }

    def _sanitize_name(self, name: str) -> str:
        """Очистить имя для использования в имени файла."""
        return name.replace("::", "_").replace("/", "_").replace("\\", "_")
