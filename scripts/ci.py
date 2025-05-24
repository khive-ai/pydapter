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

    # Run only a specific component
    python scripts/ci.py --only lint
    python scripts/ci.py --only unit
    python scripts/ci.py --only integration

    # Skip tests that require external dependencies
    python scripts/ci.py --skip-external-deps

    # Run with specific Python version
    python scripts/ci.py --python-version 3.10

    # Run tests in parallel
    python scripts/ci.py --parallel 4

    # Install all dependencies before running tests
    # uv sync --extra all
    # python scripts/ci.py
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

    # Define required dependencies for each step
    REQUIRED_DEPS = {
        "lint": ["ruff"],
        "unit_tests": ["pytest", "pytest-cov"],
        "integration_tests": ["pytest", "pytest-cov"],
        "coverage": ["coverage"],
        "docs": [],  # Uses external tools (markdownlint-cli, markdown-link-check)
    }

    # Define external dependencies that might be skipped
    EXTERNAL_DEPS_FILES = [
        "test_weaviate_adapter.py",
        "test_async_weaviate_adapter.py",
        "test_neo4j_adapter.py",
        "test_async_neo4j_adapter.py",
        "test_qdrant_adapter.py",
        "test_async_qdrant_adapter.py",
        "test_mongo_adapter.py",
        "test_async_mongo_adapter.py",
        "test_integration_weaviate.py",
        "test_integration_neo4j.py",
        "test_integration_qdrant.py",
        "test_integration_mongodb.py",
        "test_integration_async_neo4j.py",
        "test_pg_vector_model_adapter.py",
    ]

    def __init__(self, args):
        self.args = args
        self.project_root = Path(__file__).parent.parent.absolute()
        self.steps: list[CIStep] = []
        self.results: list[tuple[str, StepResult]] = []
        self.missing_deps: set[str] = set()

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

    def check_dependencies(self, step_name: str) -> bool:
        """
        Check if required dependencies for a step are installed.
        Returns True if all dependencies are available or successfully installed.
        """
        if step_name not in self.REQUIRED_DEPS:
            return True

        missing_deps = []
        for dep in self.REQUIRED_DEPS[step_name]:
            exit_code, _ = self.run_command(["uv", "pip", "show", dep], check=False)
            if exit_code != 0:
                missing_deps.append(dep)

        if not missing_deps:
            return True

        # Try to install missing dependencies
        print(
            f"{Colors.WARNING}Installing missing dependencies: {', '.join(missing_deps)}{Colors.ENDC}"
        )
        for dep in missing_deps:
            exit_code, output = self.run_command(
                ["uv", "pip", "install", dep], check=False
            )
            if exit_code != 0:
                print(f"{Colors.FAIL}Failed to install {dep}: {output}{Colors.ENDC}")
                self.missing_deps.add(dep)
                return False

        return True

    def should_skip_external_deps(self) -> bool:
        """Check if external dependencies should be skipped."""
        return self.args.skip_external_deps

    def get_test_files(self) -> list[str]:
        """Get list of test files, excluding external dependency tests if needed."""
        test_dir = self.project_root / "tests"
        all_test_files = [f.name for f in test_dir.glob("test_*.py")]

        if not self.should_skip_external_deps():
            return all_test_files

        # Filter out tests that require external dependencies
        return [f for f in all_test_files if f not in self.EXTERNAL_DEPS_FILES]

    def run_linting(self) -> StepResult:
        """Run linting checks using ruff."""
        if self.args.skip_lint or (self.args.only and self.args.only != "lint"):
            return StepResult.SKIPPED

        if not self.check_dependencies("lint"):
            return StepResult.FAILURE

        step = self.add_step("lint", "Linting checks")
        step.start()

        cmd = ["uv", "run", "ruff", "check", "src", "tests"]
        exit_code, output = self.run_command(cmd)

        result = StepResult.SUCCESS if exit_code == 0 else StepResult.FAILURE
        step.complete(result, output)
        return result

    def run_formatting(self) -> StepResult:
        """Run code formatting checks."""
        if self.args.skip_lint or (self.args.only and self.args.only != "lint"):
            return StepResult.SKIPPED

        if not self.check_dependencies("lint"):
            return StepResult.FAILURE

        step = self.add_step("format", "Code formatting checks")
        step.start()

        cmd = ["uv", "run", "ruff", "format", "src", "tests"]
        exit_code, output = self.run_command(cmd)

        result = StepResult.SUCCESS if exit_code == 0 else StepResult.FAILURE
        step.complete(result, output)
        return result

    def run_unit_tests(self) -> StepResult:
        """Run unit tests."""
        if self.args.skip_unit or (self.args.only and self.args.only != "unit"):
            return StepResult.SKIPPED

        if not self.check_dependencies("unit_tests"):
            return StepResult.FAILURE

        step = self.add_step("unit_tests", "Unit tests")
        step.start()

        # Get test files, excluding external dependency tests if needed
        test_files = self.get_test_files()

        # Filter out integration tests
        test_files = [f for f in test_files if not f.startswith("test_integration_")]

        if not test_files:
            step.complete(StepResult.SKIPPED, "No test files to run")
            return StepResult.SKIPPED

        # Build the command
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

        # If skipping external deps, explicitly specify test files
        if self.should_skip_external_deps():
            cmd.extend([str(self.project_root / "tests" / f) for f in test_files])

        exit_code, output = self.run_command(cmd)

        result = StepResult.SUCCESS if exit_code == 0 else StepResult.FAILURE
        step.complete(result, output)
        return result

    def run_integration_tests(self) -> StepResult:
        """Run integration tests."""
        if self.args.skip_integration or (
            self.args.only and self.args.only != "integration"
        ):
            return StepResult.SKIPPED

        if not self.check_dependencies("integration_tests"):
            return StepResult.FAILURE

        step = self.add_step("integration_tests", "Integration tests")
        step.start()

        # Get test files, excluding external dependency tests if needed
        test_files = self.get_test_files()

        # Keep only integration tests
        test_files = [f for f in test_files if f.startswith("test_integration_")]

        if not test_files:
            step.complete(StepResult.SKIPPED, "No integration test files to run")
            return StepResult.SKIPPED

        # Build the command
        cmd = [
            "uv",
            "run",
            "pytest",
            "-xvs",
            "--cov=pydapter",
            "--cov-append",  # Append to existing coverage data instead of overwriting
            "--cov-report=term-missing",
            "-k",
            "integration",
        ]

        if self.args.parallel:
            cmd.extend(["-n", str(self.args.parallel)])

        # If skipping external deps, explicitly specify test files
        if self.should_skip_external_deps():
            cmd.extend([str(self.project_root / "tests" / f) for f in test_files])

        exit_code, output = self.run_command(cmd)

        result = StepResult.SUCCESS if exit_code == 0 else StepResult.FAILURE
        step.complete(result, output)
        return result

    def run_coverage_report(self) -> StepResult:
        """Generate coverage report."""
        if self.args.skip_coverage or (self.args.only and self.args.only != "coverage"):
            return StepResult.SKIPPED

        if not self.check_dependencies("coverage"):
            return StepResult.FAILURE

        step = self.add_step("coverage", "Coverage report")
        step.start()

        cmd = ["uv", "run", "coverage", "report", "--fail-under=45"]
        exit_code, output = self.run_command(cmd)

        result = StepResult.SUCCESS if exit_code == 0 else StepResult.FAILURE
        step.complete(result, output)
        return result

    def run_documentation_validation(self) -> StepResult:
        """Run documentation validation checks."""
        if self.args.skip_docs or (self.args.only and self.args.only != "docs"):
            return StepResult.SKIPPED

        step = self.add_step("docs_validation", "Documentation validation")
        step.start()

        # Check if documentation validation tools are available
        markdownlint_available = self.check_external_tool("markdownlint")
        link_check_available = self.check_external_tool("markdown-link-check")

        if not markdownlint_available or not link_check_available:
            missing_tools = []
            if not markdownlint_available:
                missing_tools.append("markdownlint-cli")
            if not link_check_available:
                missing_tools.append("markdown-link-check")

            error_msg = (
                f"Missing documentation validation tools: {', '.join(missing_tools)}\n"
            )
            error_msg += (
                "Install with: npm install -g markdownlint-cli markdown-link-check"
            )
            step.complete(StepResult.FAILURE, error_msg)
            return StepResult.FAILURE

        # Run markdownlint
        lint_exit_code, lint_output = self.run_command(
            ["markdownlint", "docs/**/*.md"], check=False
        )

        # Run markdown-link-check on key files
        link_check_files = [
            "docs/api/core.md",
            "docs/api/protocols.md",
            "docs/api/fields.md",
            "docs/getting_started.md",
            "docs/index.md",
        ]

        link_check_exit_code = 0
        link_check_output = ""

        for file_path in link_check_files:
            if (self.project_root / file_path).exists():
                exit_code, output = self.run_command(
                    [
                        "markdown-link-check",
                        file_path,
                        "--config",
                        ".markdownlinkcheck.json",
                    ],
                    check=False,
                )
                if exit_code != 0:
                    link_check_exit_code = exit_code
                    link_check_output += f"\n{file_path}:\n{output}"

        # Combine results
        combined_output = ""
        if lint_exit_code != 0:
            combined_output += f"Markdownlint errors:\n{lint_output}\n"
        if link_check_exit_code != 0:
            combined_output += f"Link check errors:\n{link_check_output}\n"

        overall_success = lint_exit_code == 0 and link_check_exit_code == 0
        result = StepResult.SUCCESS if overall_success else StepResult.FAILURE
        step.complete(result, combined_output)
        return result

    def check_external_tool(self, tool_name: str) -> bool:
        """Check if an external tool is available in PATH."""
        exit_code, _ = self.run_command(["which", tool_name], check=False)
        return exit_code == 0

    def run_all(self) -> bool:
        """Run all CI steps and return overall success status."""
        print(f"\n{Colors.BOLD}Running CI for pydapter{Colors.ENDC}")
        print(f"Python: {sys.version.split()[0]}")
        print(f"Working directory: {self.project_root}\n")

        # Print warning if skipping external dependencies
        if self.should_skip_external_deps():
            print(
                f"{Colors.WARNING}Skipping tests that require external dependencies{Colors.ENDC}"
            )
            print(
                f"{Colors.WARNING}To run all tests, install all dependencies with: uv sync --extra all{Colors.ENDC}\n"
            )

        # Run all steps
        lint_result = self.run_linting()
        format_result = self.run_formatting()
        unit_test_result = self.run_unit_tests()
        integration_test_result = self.run_integration_tests()
        coverage_result = self.run_coverage_report()
        docs_result = self.run_documentation_validation()

        # Collect results
        self.results = [
            ("Linting", lint_result),
            ("Formatting", format_result),
            ("Unit tests", unit_test_result),
            ("Integration tests", integration_test_result),
            ("Coverage", coverage_result),
            ("Documentation", docs_result),
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

        # Print missing dependencies if any
        if self.missing_deps:
            print(f"\n{Colors.WARNING}Missing dependencies:{Colors.ENDC}")
            for dep in self.missing_deps:
                print(f"  - {dep}")
            print(f"\nInstall with: uv pip install {' '.join(self.missing_deps)}")
            print("Or install all dependencies with: uv sync --extra all")

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
    parser.add_argument("--skip-unit", action="store_true", help="Skip unit tests")
    parser.add_argument(
        "--skip-integration", action="store_true", help="Skip integration tests"
    )
    parser.add_argument(
        "--skip-coverage", action="store_true", help="Skip coverage report"
    )
    parser.add_argument(
        "--skip-docs", action="store_true", help="Skip documentation validation"
    )
    parser.add_argument(
        "--skip-external-deps",
        action="store_true",
        help="Skip tests that require external dependencies",
    )

    # Run only specific components
    parser.add_argument(
        "--only",
        choices=["lint", "unit", "integration", "coverage", "docs"],
        help="Run only the specified component",
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
