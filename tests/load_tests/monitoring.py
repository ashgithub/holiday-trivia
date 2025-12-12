"""
Monitoring and metrics collection for load testing

This module provides tools to monitor system performance during load tests,
collecting metrics on CPU, memory, network, and application-specific metrics.
"""

import psutil
import time
import threading
import json
import os
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict
import statistics


class SystemMonitor:
    """
    Monitors system resources during load testing
    """

    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self.is_monitoring = False
        self.metrics: List[Dict[str, Any]] = []
        self.start_time = None
        self.monitor_thread = None

    def start_monitoring(self):
        """Start collecting system metrics"""
        self.is_monitoring = True
        self.start_time = time.time()
        self.monitor_thread = threading.Thread(target=self._collect_metrics)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print("System monitoring started...")

    def stop_monitoring(self):
        """Stop collecting metrics and return results"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)

        print(f"Monitoring stopped. Collected {len(self.metrics)} data points.")
        return self._analyze_metrics()

    def _collect_metrics(self):
        """Background thread for collecting system metrics"""
        while self.is_monitoring:
            try:
                timestamp = time.time()

                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=None)

                # Memory metrics
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_used_mb = memory.used / (1024 * 1024)

                # Network metrics (system-wide)
                network = psutil.net_io_counters()
                bytes_sent = network.bytes_sent
                bytes_recv = network.bytes_recv

                # Process-specific metrics (if available)
                process_metrics = self._get_process_metrics()

                metric_data = {
                    "timestamp": timestamp,
                    "relative_time": timestamp - self.start_time,
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "memory_used_mb": memory_used_mb,
                    "network_bytes_sent": bytes_sent,
                    "network_bytes_recv": bytes_recv,
                    **process_metrics
                }

                self.metrics.append(metric_data)

            except Exception as e:
                print(f"Error collecting metrics: {e}")

            time.sleep(self.collection_interval)

    def _get_process_metrics(self) -> Dict[str, Any]:
        """Get process-specific metrics for the quiz application"""
        try:
            # Find Python processes running the quiz app
            quiz_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                        cmdline = proc.info['cmdline']
                        if cmdline and any('main.py' in arg for arg in cmdline):
                            quiz_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if quiz_processes:
                # Use the first matching process
                proc = quiz_processes[0]
                proc_cpu = proc.cpu_percent()
                proc_memory = proc.memory_info()
                proc_memory_mb = proc_memory.rss / (1024 * 1024)

                return {
                    "process_cpu_percent": proc_cpu,
                    "process_memory_mb": proc_memory_mb,
                    "process_count": len(quiz_processes)
                }

        except Exception as e:
            print(f"Error getting process metrics: {e}")

        return {
            "process_cpu_percent": None,
            "process_memory_mb": None,
            "process_count": 0
        }

    def _analyze_metrics(self) -> Dict[str, Any]:
        """Analyze collected metrics and generate summary"""
        if not self.metrics:
            return {"error": "No metrics collected"}

        # Extract metric series
        cpu_values = [m["cpu_percent"] for m in self.metrics if m["cpu_percent"] is not None]
        memory_values = [m["memory_percent"] for m in self.metrics if m["memory_percent"] is not None]
        memory_mb_values = [m["memory_used_mb"] for m in self.metrics if m["memory_used_mb"] is not None]
        network_sent = [m["network_bytes_sent"] for m in self.metrics]
        network_recv = [m["network_bytes_recv"] for m in self.metrics]

        # Process metrics
        proc_cpu_values = [m["process_cpu_percent"] for m in self.metrics if m["process_cpu_percent"] is not None]
        proc_memory_values = [m["process_memory_mb"] for m in self.metrics if m["process_memory_mb"] is not None]

        analysis = {
            "collection_duration": self.metrics[-1]["relative_time"] if self.metrics else 0,
            "data_points": len(self.metrics),
            "cpu": {
                "average": statistics.mean(cpu_values) if cpu_values else None,
                "max": max(cpu_values) if cpu_values else None,
                "min": min(cpu_values) if cpu_values else None,
                "p95": statistics.quantiles(cpu_values, n=20)[18] if len(cpu_values) >= 20 else None,
            },
            "memory": {
                "average_percent": statistics.mean(memory_values) if memory_values else None,
                "max_percent": max(memory_values) if memory_values else None,
                "average_mb": statistics.mean(memory_mb_values) if memory_mb_values else None,
                "max_mb": max(memory_mb_values) if memory_mb_values else None,
            },
                "network": {
                    "total_bytes_sent": (network_sent[-1] - network_sent[0]) if len(network_sent) >= 2 else 0,
                    "total_bytes_recv": (network_recv[-1] - network_recv[0]) if len(network_recv) >= 2 else 0,
                    "avg_bytes_sent_per_sec": ((network_sent[-1] - network_sent[0]) / len(network_sent)) if len(network_sent) >= 2 else 0,
                    "avg_bytes_recv_per_sec": ((network_recv[-1] - network_recv[0]) / len(network_recv)) if len(network_recv) >= 2 else 0,
                },
            "process": {
                "cpu_average": statistics.mean(proc_cpu_values) if proc_cpu_values else None,
                "cpu_max": max(proc_cpu_values) if proc_cpu_values else None,
                "memory_average_mb": statistics.mean(proc_memory_values) if proc_memory_values else None,
                "memory_max_mb": max(proc_memory_values) if proc_memory_values else None,
            },
            "raw_metrics": self.metrics  # Full dataset for detailed analysis
        }

        return analysis


class ApplicationMetricsCollector:
    """
    Collects application-specific metrics during testing
    """

    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_time = None

    def start_collection(self):
        """Start collecting application metrics"""
        self.start_time = time.time()
        print("Application metrics collection started...")

    def record_metric(self, metric_name: str, value: Any, timestamp: float = None):
        """Record a single metric value"""
        if timestamp is None:
            timestamp = time.time()

        relative_time = timestamp - self.start_time if self.start_time else 0

        self.metrics[metric_name].append({
            "value": value,
            "timestamp": timestamp,
            "relative_time": relative_time
        })

    def record_websocket_event(self, event_type: str, user_id: str = None, metadata: Dict[str, Any] = None):
        """Record WebSocket-related events"""
        self.record_metric(f"websocket_{event_type}", {
            "user_id": user_id or "",
            "metadata": metadata or {}
        })

    def record_quiz_event(self, event_type: str, metadata: Dict[str, Any] = None):
        """Record quiz-specific events"""
        self.record_metric(f"quiz_{event_type}", (metadata or {}))

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of collected application metrics"""
        summary = {}

        for metric_name, values in self.metrics.items():
            if not values:
                continue

            # Count events
            event_count = len(values)

            # For numeric values, calculate statistics
            numeric_values = [v["value"] for v in values if isinstance(v["value"], (int, float))]

            summary[metric_name] = {
                "count": event_count,
                "values": values
            }

            if numeric_values:
                summary[metric_name].update({
                    "average": statistics.mean(numeric_values),
                    "max": max(numeric_values),
                    "min": min(numeric_values),
                    "total": sum(numeric_values)
                })

        return summary


class LoadTestReporter:
    """
    Generates comprehensive reports from load test results
    """

    def __init__(self, system_monitor: SystemMonitor, app_metrics: ApplicationMetricsCollector):
        self.system_monitor = system_monitor
        self.app_metrics = app_metrics

    def generate_report(self, test_name: str, user_count: int) -> Dict[str, Any]:
        """Generate a comprehensive test report"""
        system_analysis = self.system_monitor._analyze_metrics()
        app_summary = self.app_metrics.get_summary()

        # Performance assessment
        performance_score = self._calculate_performance_score(system_analysis, user_count)

        report = {
            "test_info": {
                "name": test_name,
                "user_count": user_count,
                "timestamp": datetime.now().isoformat(),
                "duration": system_analysis.get("collection_duration", 0)
            },
            "system_performance": system_analysis,
            "application_metrics": app_summary,
            "performance_assessment": performance_score,
            "recommendations": self._generate_recommendations(system_analysis, performance_score, user_count)
        }

        return report

    def _calculate_performance_score(self, system_analysis: Dict, user_count: int) -> Dict[str, Any]:
        """Calculate overall performance score (0-100)"""
        score = 100  # Start with perfect score
        issues = []

        # CPU assessment
        cpu_avg = system_analysis.get("cpu", {}).get("average")
        if cpu_avg:
            if cpu_avg > 80:
                score -= 30
                issues.append(f"High CPU usage: {cpu_avg:.1f}%")
            elif cpu_avg > 60:
                score -= 15
                issues.append(f"Moderate CPU usage: {cpu_avg:.1f}%")

        # Memory assessment
        memory_avg = system_analysis.get("memory", {}).get("average_percent")
        if memory_avg:
            if memory_avg > 85:
                score -= 30
                issues.append(f"High memory usage: {memory_avg:.1f}%")
            elif memory_avg > 70:
                score -= 15
                issues.append(f"Moderate memory usage: {memory_avg:.1f}%")

        # Network assessment (rough heuristic)
        network_sent = system_analysis.get("network", {}).get("avg_bytes_sent_per_sec", 0)
        expected_min_bytes = user_count * 100  # Rough estimate: 100 bytes/sec per user
        if network_sent < expected_min_bytes:
            score -= 10
            issues.append("Low network activity - possible connection issues")

        # Process-specific checks
        proc_cpu = system_analysis.get("process", {}).get("cpu_average")
        if proc_cpu and proc_cpu > 70:
            score -= 20
            issues.append(f"High process CPU: {proc_cpu:.1f}%")

        return {
            "overall_score": max(0, score),
            "grade": self._score_to_grade(score),
            "issues": issues,
            "recommendations": self._get_score_recommendations(score)
        }

    def _score_to_grade(self, score: int) -> str:
        """Convert numeric score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _get_score_recommendations(self, score: int) -> List[str]:
        """Get recommendations based on performance score"""
        if score >= 90:
            return ["Performance excellent - ready for production with 150 users"]
        elif score >= 80:
            return ["Good performance - monitor resource usage in production"]
        elif score >= 70:
            return ["Acceptable performance - consider optimizations for peak loads"]
        elif score >= 60:
            return ["Performance concerns - optimize before production deployment"]
        else:
            return ["Critical performance issues - significant optimizations required"]

    def _generate_recommendations(self, system_analysis: Dict, performance_score: Dict, user_count: int) -> List[str]:
        """Generate specific recommendations based on test results"""
        recommendations = []

        cpu_avg = system_analysis.get("cpu", {}).get("average")
        memory_avg = system_analysis.get("memory", {}).get("average_percent")

        if cpu_avg and cpu_avg > 70:
            recommendations.append("Consider horizontal scaling or CPU optimization")
            recommendations.append("Implement connection pooling for WebSocket handling")

        if memory_avg and memory_avg > 75:
            recommendations.append("Optimize memory usage - consider in-memory caching strategies")
            recommendations.append("Monitor for memory leaks during extended quiz sessions")

        if user_count >= 100 and performance_score["overall_score"] < 80:
            recommendations.append("Test with connection limits and implement rate limiting")
            recommendations.append("Consider message batching to reduce network overhead")

        if not recommendations:
            recommendations.append("Performance looks good for target user count")

        return recommendations

    def save_report(self, report: Dict, filename: str = None):
        """Save report to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"load_test_report_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"Report saved to: {filename}")
        return filename


# Global instances for use in load tests
system_monitor = SystemMonitor()
app_metrics = ApplicationMetricsCollector()
reporter = LoadTestReporter(system_monitor, app_metrics)
