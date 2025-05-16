#!/usr/bin/env python3
"""
CI script for pydapter project.

This script orchestrates all testing and quality checks for the pydapter project.
It can be run locally or in CI environments like GitHub Actions.

Usage:
    python scripts/ci.py [options]

Examples:
    # Run all checks
    python scripts/ci.py

    # Run only unit tests
    python scripts/ci.py --skip-lint --skip-type-check --skip-integration

    # Run with specific Python version
    python scripts/ci.py --python-version 3.10
"""

import argparse
import os
import subprocess
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Optional


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class StepResult(Enum):
    """Result of a CI step."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


class CIStep:
    """Represents a step in the CI process."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.result: Optional[StepResult] = None
        self.output: str = ""

    def start(self):
        """Mark the step as started."""
        self.start_time = time.time()
        print(f"{Colors.HEADER}{Colors.BOLD}Running: {self.description}{Colors.ENDC}")

    def complete(self, result: StepResult, output: str = ""):
        """Mark the step as completed with a result."""
        self.end_time = time.time()
        self.result = result
        self.output = output

        duration = round(self.end_time - (self.start_time or 0), 2)

        if result == StepResult.SUCCESS:
            status = f"{Colors.GREEN}✓ PASSED{Colors.ENDC}"
        elif result == StepResult.FAILURE:
            status = f"{Colors.FAIL}✗ FAILED{Colors.ENDC}"
        else:  # SKIPPED
            status = f"{Colors.WARNING}⚠ SKIPPED{Colors.ENDC}"

        print(f"{status} {self.description} in {duration}s")

        if output and result == StepResult.FAILURE:
            print(f"\n{Colors.FAIL}Output:{Colors.ENDC}")
            print(output)
            print()


class CIRunner:
    """Main CI runner that orchestrates all steps."""

    def __init__(self, args):
        self.args = args
        self.project_root = Path(__file__).parent.parent.absolute()
        self.steps: list[CIStep] = []
        self.results: list[tuple[str, StepResult]] = []

        # Environment setup
        self.env = os.environ.copy()
        if args.python_path:
            self.env["PATH"] = f"{args.python_path}:{self.env.get('PATH', '')}"

    def run_command(
        self, cmd: list[str], check: bool = True, cwd: Optional[Path] = None
    ) -> tuple[int, str]:
        """Run a shell command and return exit code and output."""
        if self.args.dry_run:
            print(f"Would run: {' '.join(cmd)}")
            return 0, "Dry run - no output"

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                check=False,
                capture_output=True,
                text=True,
                env=self.env,
            )
            if check and result.returncode != 0:
                return (
                    result.returncode,
                    f"Command failed with code {result.returncode}\n{result.stdout}\n{result.stderr}",
                )
            return result.returncode, f"{result.stdout}\n{result.stderr}"
        except Exception as e:
            return 1, f"Error executing command: {e}"

    def add_step(self, name: str, description: str) -> CIStep:
        """Add a step to the CI process."""
        step = CIStep(name, description)
        self.steps.append(step)
        return step

    def run_linting(self) -> StepResult:
        """Run linting checks using ruff."""
        if self.args.skip_lint:
            return StepResult.SKIPPED

        step = self.add_step("lint", "Linting checks")
        step.start()

        cmd = ["uv", "run", "ruff", "check", "src", "tests"]
        exit_code, output = self.run_command(cmd)

        result = StepResult.SUCCESS if exit_code == 0 else StepResult.FAILURE
        step.complete(result, output)
        return result

    def run_formatting(self) -> StepResult:
        """Run code formatting checks."""
        if self.args.skip_lint:
            return StepResult.SKIPPED

        step = self.add_step("format", "Code formatting checks")
        step.start()

        cmd = ["uv", "run", "ruff", "format", "--check", "src", "tests"]
        exit_code, output = self.run_command(cmd)

        result = StepResult.SUCCESS if exit_code == 0 else StepResult.FAILURE
        step.complete(result, output)
        return result

    def run_type_checking(self) -> StepResult:
        """Run type checking with mypy."""
        if self.args.skip_type_check:
            return StepResult.SKIPPED

        step = self.add_step("type_check", "Type checking")
        step.start()

        # Check if mypy is installed
        exit_code, _ = self.run_command(["uv", "pip", "show", "mypy"], check=False)
        if exit_code != 0:
            # Install mypy if not available
            _, output = self.run_command(["uv", "pip", "install", "mypy"], check=False)
            if "Successfully installed mypy" not in output:
                step.complete(StepResult.FAILURE, "Failed to install mypy")
                return StepResult.FAILURE

        cmd = ["uv", "run", "mypy", "src"]
        exit_code, output = self.run_command(cmd)

        result = StepResult.SUCCESS if exit_code == 0 else StepResult.FAILURE
        step.complete(result, output)
        return result

    def run_unit_tests(self) -> StepResult:
        """Run unit tests."""
        if self.args.skip_unit:
            return StepResult.SKIPPED

        step = self.add_step("unit_tests", "Unit tests")
        step.start()

        # Exclude integration tests
        cmd = [
            "uv",
            "run",
            "pytest",
            "-xvs",
            "--cov=pydapter",
            "--cov-report=term-missing",
            "-k",
            "not integration",
        ]

        if self.args.parallel:
            cmd.extend(["-n", str(self.args.parallel)])

        exit_code, output = self.run_command(cmd)

        result = StepResult.SUCCESS if exit_code == 0 else StepResult.FAILURE
        step.complete(result, output)
        return result

    def run_integration_tests(self) -> StepResult:
        """Run integration tests."""
        if self.args.skip_integration:
            return StepResult.SKIPPED

        step = self.add_step("integration_tests", "Integration tests")
        step.start()

        # Only run integration tests
        cmd = [
            "uv",
            "run",
            "pytest",
            "-xvs",
            "--cov=pydapter",
            "--cov-report=term-missing",
            "-k",
            "integration",
        ]

        if self.args.parallel:
            cmd.extend(["-n", str(self.args.parallel)])

        exit_code, output = self.run_command(cmd)

        result = StepResult.SUCCESS if exit_code == 0 else StepResult.FAILURE
        step.complete(result, output)
        return result

    def run_coverage_report(self) -> StepResult:
        """Generate coverage report."""
        if self.args.skip_coverage:
            return StepResult.SKIPPED

        step = self.add_step("coverage", "Coverage report")
        step.start()

        cmd = ["uv", "run", "coverage", "report", "--fail-under=80"]
        exit_code, output = self.run_command(cmd)

        result = StepResult.SUCCESS if exit_code == 0 else StepResult.FAILURE
        step.complete(result, output)
        return result

    def run_all(self) -> bool:
        """Run all CI steps and return overall success status."""
        print(f"\n{Colors.BOLD}Running CI for pydapter{Colors.ENDC}")
        print(f"Python: {sys.version.split()[0]}")
        print(f"Working directory: {self.project_root}\n")

        # Run all steps
        lint_result = self.run_linting()
        format_result = self.run_formatting()
        type_check_result = self.run_type_checking()
        unit_test_result = self.run_unit_tests()
        integration_test_result = self.run_integration_tests()
        coverage_result = self.run_coverage_report()

        # Collect results
        self.results = [
            ("Linting", lint_result),
            ("Formatting", format_result),
            ("Type checking", type_check_result),
            ("Unit tests", unit_test_result),
            ("Integration tests", integration_test_result),
            ("Coverage", coverage_result),
        ]

        # Print summary
        print(f"\n{Colors.BOLD}CI Summary:{Colors.ENDC}")
        for name, result in self.results:
            if result == StepResult.SUCCESS:
                status = f"{Colors.GREEN}PASS{Colors.ENDC}"
            elif result == StepResult.FAILURE:
                status = f"{Colors.FAIL}FAIL{Colors.ENDC}"
            else:  # SKIPPED
                status = f"{Colors.WARNING}SKIP{Colors.ENDC}"
            print(f"  {name}: {status}")

        # Determine overall success
        failures = [r for _, r in self.results if r == StepResult.FAILURE]
        success = len(failures) == 0

        if success:
            print(f"\n{Colors.GREEN}{Colors.BOLD}CI PASSED{Colors.ENDC}")
        else:
            print(f"\n{Colors.FAIL}{Colors.BOLD}CI FAILED{Colors.ENDC}")

        return success


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run CI checks for pydapter")

    # Skip options
    parser.add_argument("--skip-lint", action="store_true", help="Skip linting checks")
    parser.add_argument(
        "--skip-type-check", action="store_true", help="Skip type checking"
    )
    parser.add_argument("--skip-unit", action="store_true", help="Skip unit tests")
    parser.add_argument(
        "--skip-integration", action="store_true", help="Skip integration tests"
    )
    parser.add_argument(
        "--skip-coverage", action="store_true", help="Skip coverage report"
    )

    # Configuration options
    parser.add_argument("--python-version", help="Python version to use (e.g., 3.10)")
    parser.add_argument("--python-path", help="Path to Python executable")
    parser.add_argument(
        "--parallel",
        type=int,
        help="Run tests in parallel with specified number of processes",
    )

    # Other options
    parser.add_argument(
        "--dry-run", action="store_true", help="Show commands without executing them"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    runner = CIRunner(args)
    success = runner.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
