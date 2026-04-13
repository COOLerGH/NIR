# NIR: Automated Detection and Quarantine of Order-Dependent Flaky Tests in a CI/CD Pipeline

## Authors and contributors
Main contributor: Mikhail A. Goriunov, Bachelor student (3rd year), Peter the Great St. Petersburg Polytechnic University, Institute of Computer Science and Cybersecurity (SPbPU ICSC / ИКНК).

Advisor and contributor: Vladimir A. Parkhomenko, Senior Lecturer, Peter the Great St. Petersburg Polytechnic University, Institute of Computer Science and Cybersecurity (SPbPU ICSC / ИКНК).

## Introduction
This repository contains the results of a research work (НИР) performed within the course “Software Testing Methods” at SPbPU ICSC.

The work focuses on flaky tests, specifically **order-dependent flaky tests** (tests whose outcome depends on the execution order). The repository provides:
- `file_explorer_search/`: a target Python project (File Explorer API / search system) with a pytest test suite, including dedicated victim–polluter order-dependent tests for demonstration.
- `flaky_detection_system/`: a CI/CD-oriented system that performs repeated test executions, parses JSON reports, detects flaky behavior, classifies flaky tests, and automatically quarantines unstable tests.

## Instruction

### Requirements
- Python 3.13.2
- `pip`

### Installation
From the repository root:
```bash
pip install -r file_explorer_search/requirements.txt
pip install -r flaky_detection_system/requirements.txt
```

### Run the flaky detection system (full cycle)
```bash
cd flaky_detection_system
python main.py run-all --runs 10
```

### Useful commands
```bash
# Run only repeated executions
python main.py detect --runs 10

# Analyze existing results
python main.py analyze --last 10

# Generate reports (JSON/HTML)
python main.py report --format all --last 10

# Quarantine management
python main.py quarantine --list
```

### Outputs
Test run results: flaky_detection_system/results/*.json
Reports: flaky_detection_system/reports/
Quarantine state: flaky_detection_system/quarantine/quarantine.json and deselect.txt

## Licence
MIT License for the original source code in this repository.

Third-party dependencies (pytest and plugins, etc.) remain under their respective licenses.

## Warranty
The developed software is research/prototype software. The authors provide it “as is” without any warranty.

## References
Luo Q., Hariri F., Eloussi L., Marinov D. An Empirical Analysis of Flaky Tests // Proceedings of the 22nd ACM SIGSOFT International Symposium on Foundations of Software Engineering (FSE). 2014. P. 643–653.
Lam W., Oei R., Shi A., Marinov D., Xie T. iDFlakies: A Framework for Detecting and Partially Classifying Flaky Tests // Proceedings of the 12th IEEE International Conference on Software Testing, Verification and Validation (ICST). 2019. P. 312–322.
Shi A., Gyori A., Leesatapornwongsa T., Marinov D. Detecting Assumptions on Deterministic Implementations of Non-Deterministic Specifications // Proceedings of the 2016 IEEE International Conference on Software Testing, Verification and Validation (ICST). 2016. P. 80–90.
