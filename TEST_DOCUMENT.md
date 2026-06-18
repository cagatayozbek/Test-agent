# Enhancing ReAct-based Agents with Program Analysis for Software Testing

**Software Test Documentation**
Version 1.0
03.06.2026

Prepared by: Furkan Çağatay Özbek - Şerafettin Tayyip Özdemir
Advisor: Ömer Özgür TANRIÖVER
Institution: Ankara University Department of Computer Engineering

---

## Document History

### Revision History

| Revision # | Revision Date | Description of Change | Author |
|---|---|---|---|
| 1.0 | 03.06.2026 | Initial Software Test Documentation, derived from SDD v2.0. Defines the test plan, test design, test cases, procedures, traceability, and reporting templates for the implemented system (Deep Agents orchestration, SafeEditor reasoning gates, multi-provider LLM abstraction, BugTest evaluation surface). Test cases are grounded in the realised automated test suite (`tests/`, 9 suites, 67 cases). | Furkan Çağatay Özbek, Şerafettin Tayyip Özdemir |

---

## Table of Contents

1. Introduction
   - 1.1 Purpose
   - 1.2 Scope
   - 1.3 References
   - 1.4 Definitions, Acronyms, and Abbreviations
   - 1.5 Document Overview
2. Test Plan
   - 2.1 Test Objectives
   - 2.2 Test Items
   - 2.3 Features to be Tested
   - 2.4 Features Not to be Tested
   - 2.5 Test Approach and Levels
   - 2.6 Item Pass/Fail Criteria
   - 2.7 Test Environment
   - 2.8 Test Deliverables
   - 2.9 Responsibilities and Schedule
   - 2.10 Testing Risks and Contingencies
3. Test Design Specification
   - 3.1 Unit-Level Design
   - 3.2 Integration-Level Design
   - 3.3 System-Level Design
4. Test Case Specifications
   - 4.1 SafeEditor and ReasoningEnvelope
   - 4.2 Agent ReAct Loop
   - 4.3 Provider Capabilities and Routing
   - 4.4 Reliability and Rate-Limit Detection
   - 4.5 Data Models and Compatibility
   - 4.6 Prompt Rendering and Fairness
   - 4.7 Integration
   - 4.8 System and Bug-Revealing Verification
   - 4.9 Results Tagging Utility
5. Test Procedure Specification
6. Requirements Traceability Matrix
7. Test Reporting
   - 7.1 Test Log
   - 7.2 Test Summary Report
   - 7.3 Defect Reporting
8. Supporting Information
   - 8.1 Glossary
   - 8.2 Appendices

---

## 1. Introduction

### 1.1 Purpose

The purpose of this Software Test Documentation (STD) is to define the testing
strategy, test design, and concrete test cases used to verify the system titled
*"Enhancing ReAct-based Agents with Program Analysis for Software Testing"*.

This document operationalises the Verification Strategy outlined in Section 7.2
of the Software Design Document (SDD) v2.0. Where the SDD states *how*
verification is to be conducted at a high level, this STD specifies the concrete
test items, test cases, pass/fail criteria, execution procedures, and reporting
templates. It is the primary reference for the verification phase and the basis
on which conformance to the requirements is demonstrated.

This document does not report measured experimental results (model rankings,
Bug-Revealing Test Rate comparisons, statistical analysis). Those belong to the
project's separate Experiment Report. This STD defines the tests; the Experiment
Report records the empirical findings of running the system.

### 1.2 Scope

The system under test is a research-oriented prototype that produces
bug-revealing pytest test cases for Python code under test using a Large Language
Model (LLM) driven, ReAct-based agent enhanced with static program analysis,
subagent delegation, and a guarded safe-edit mechanism.

This STD covers three levels of testing for the implemented system:

- **Unit testing** of the individual design components (SafeEditor, Agent,
  capabilities/provider routing, data models, prompt rendering, rate-limit
  detection, results tagging).
- **Integration testing** of the orchestrator, subagents, and prompt/capability
  stack working together across all configured providers.
- **System testing** of the end-to-end agent against the locally curated BugTest
  evaluation surface, validated by the deterministic bug-revealing predicate.

Out of scope for this STD (consistent with SDD v2.0 §1.2):

- Performance benchmarking and comparative model evaluation (Experiment Report).
- The planned SWE-Atlas containerised evaluation surface (SDD §2.3, future work).
- Verification of third-party dependencies (pytest, the Deep Agents SDK, provider
  SDKs); these are assumed correct and are exercised only indirectly.

### 1.3 References

1. Software Requirements Specification (SRS) v1.0, 23.11.2025. Internal project
   document.
2. Software Design Document (SDD) v2.0, 03.05.2026. Internal project document.
3. IEEE Std 829-2008. *IEEE Standard for Software and System Test
   Documentation.*
4. IEEE Std 830-1998. *IEEE Recommended Practice for Software Requirements
   Specifications.*
5. pytest documentation. https://docs.pytest.org/
6. Project source repository, `tests/` directory (realised automated test
   suite).

### 1.4 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|---|---|
| STD | Software Test Documentation (this document) |
| SUT | System Under Test |
| TC | Test Case |
| Bug-Revealing Test | A test that **passes** on the fixed (correct) code and **fails** on the buggy code, thereby exposing the defect |
| BRTR | Bug-Revealing Test Rate — proportion of runs yielding a bug-revealing test (reported in the Experiment Report) |
| ReasoningEnvelope | The (hypothesis, why_this_action, expected_outcome) triplet required on every state-changing tool call |
| Fixture | A pytest construct providing a controlled, repeatable test pre-condition (e.g. a temporary workspace) |
| Stub LLM | A scripted fake LLM client returning a deterministic tool-call sequence, used to test the agent loop without a live provider |
| Oracle | The deterministic decision procedure that classifies a test outcome as pass or fail |

(See also SDD §8.1 for the full domain glossary: Agent, AST, BugTest, Critic,
ProjectSnapshot, SafeEditor, TestRunner, Workspace.)

### 1.5 Document Overview

Section 2 presents the Test Plan (objectives, items, approach, criteria,
environment, schedule, risks). Section 3 gives the Test Design Specification per
level. Section 4 specifies the concrete test cases grouped by component. Section
5 specifies the execution procedure. Section 6 is the Requirements Traceability
Matrix. Section 7 defines the reporting templates (test log, summary report,
defect report). Section 8 contains supporting information.

---

## 2. Test Plan

### 2.1 Test Objectives

The testing effort verifies that the implemented system satisfies the functional
requirements (FR-01 … FR-09) and non-functional requirements (NFR-01 … NFR-07)
defined in SDD v2.0 §7.1. Specifically, testing must demonstrate that:

1. The safety contract holds: generated code cannot escape the workspace and
   cannot regress previously passing tests, except where a failure is the
   intended bug-revealing signal.
2. The reasoning-gate contract holds: no state-changing tool call proceeds
   without a complete ReasoningEnvelope.
3. The ReAct loop terminates correctly under every terminal condition
   (completed, error, timeout, max_steps) and accounts for steps, tokens, and
   anti-loop guardrails.
4. The provider abstraction routes the same agent loop to every configured
   provider without changes at the call site.
5. The end-to-end agent produces bug-revealing tests on the BugTest surface,
   judged by the deterministic oracle.

### 2.2 Test Items

The following implemented components are the items under test. Each is mapped to
its SDD design component and to the automated test suite that exercises it.

| Item | SDD Component | Source | Test Suite |
|---|---|---|---|
| Safe edit / reasoning gate | SafeEditor (`editor.py`) | `bugtest/deep/` | `tests/test_safe_edit_file.py` |
| ReAct loop | Agent (`core/agent.py`) | `bugtest/deep/agent.py` | `tests/test_agent_loop.py` |
| Provider capabilities/routing | LLMClient (`core/llm.py`) | `bugtest/deep/capabilities.py` | `tests/test_capabilities.py` |
| Rate-limit / reliability | LLMClient retry path | `bugtest/deep/` | `tests/test_claude_limit_detection.py` |
| Data models | Data Design (§5) | `bugtest/models.py` | `tests/test_models_compat.py` |
| Prompt rendering / fairness | System prompts (`prompts.py`) | `bugtest/deep/prompts.py` | `tests/test_prompt_render.py` |
| Orchestration integration | DeepTestOrchestrator | `bugtest/deep/orchestrator.py` | `tests/test_v2_integration.py` |
| Bug-revealing verification | TestRunner + oracle | `bugtest/validator.py` | `tests/test_benchmark.py` |
| Results tagging utility | Evaluation tooling | `scripts/` | `tests/test_tag_v1_results.py` |

### 2.3 Features to be Tested

- Workspace confinement, no-op rejection, regression check, bug-revealing
  exception, and cache invalidation in the safe-edit path.
- ReasoningEnvelope completeness enforcement and the `reasoning_filled` signal.
- Append vs. replace edit modes and their conflict diagnostics.
- ReAct loop termination, step/timeout accounting, parallel-tool-call handling,
  stop-on-bug short-circuit, and consecutive-failure instrumentation.
- Provider capability resolution and prefix-based routing for every configured
  model.
- Robust detection of provider rate-limit / quota signals versus false positives
  embedded in generated test code.
- Backward- and forward-compatible (de)serialisation of the run-record data
  models.
- Deterministic, fairness-preserving prompt rendering and versioning.
- Orchestrator construction and tool-surface selection across all models.
- The end-to-end bug-revealing predicate on a representative BugTest task.
- Idempotent, side-effect-free results tagging.

### 2.4 Features Not to be Tested

- The reasoning quality of any specific LLM provider (non-deterministic;
  measured statistically in the Experiment Report, not asserted here).
- Network transport, TLS, and provider-side availability.
- The internal correctness of pytest, coverage.py, the Deep Agents SDK, and the
  provider SDKs.
- The planned SWE-Atlas sandbox surface (future work, SDD §2.3).

### 2.5 Test Approach and Levels

Testing follows the three-level strategy of SDD §7.2.

**Unit Verification.** Each component is exercised in isolation against
controlled fixtures (temporary workspaces, synthetic baseline/modified test
results, mock provider back-ends). LLM non-determinism is removed by substituting
a **Stub LLM** that returns a scripted tool-call sequence.

**Integration Verification.** The orchestrator, prompt stack, capability layer,
and subagents are exercised together. Provider routing is asserted with a mock
back-end so the integration is deterministic.

**System Verification.** The full agent runs end-to-end against BugTest tasks.
The verdict is computed by the deterministic oracle, never by LLM judgment.

**The bug-revealing oracle.** A run is a bug-revealing success if and only if:

```
baseline.passed  AND  (NOT final.passed)  AND  (final.num_failed > baseline.num_failed)
```

i.e. the generated test passes on the correct code and fails on the buggy code.
This predicate is the single source of truth for system-level pass/fail.

### 2.6 Item Pass/Fail Criteria

- **Unit / Integration:** A suite passes when every automated test case in it
  returns the asserted result (pytest exit code 0). A single failing assertion
  fails the case and is logged as a defect.
- **System:** A task-level run is a pass when the bug-revealing oracle evaluates
  true. Suite-level acceptance for the release is that the system runs to
  completion on every task without uncaught exceptions; effectiveness (the
  proportion of bug-revealing successes) is reported quantitatively in the
  Experiment Report and is not a binary gate in this STD.
- **Release gate:** All unit and integration suites must pass on at least one
  reference provider before a benchmark run is considered valid.

### 2.7 Test Environment

| Element | Specification |
|---|---|
| Operating system | Linux or macOS (POSIX), Python 3.11 |
| Runtime | Python virtual environment with project dependencies |
| Test framework | pytest |
| Required packages | pytest, pydantic, pyyaml; provider SDKs as applicable |
| Provider access (system tests) | At least one reachable LLM provider via prefix routing (`claude:`, `nvidia:`, `anthropic:`, `openai:`, `google_genai:`) |
| Credentials | API keys via environment variables (`NVIDIA_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`); Claude CLI inherits local credentials |
| Isolation | Per-task temporary workspace directories, created and torn down per run |
| Configurable timeouts | `DEEPTEST_CLAUDE_TIMEOUT` (CLI subprocess cap), per-task step/time budgets |

Unit and integration tests require **no** live provider: they use fixtures and a
Stub/mock LLM, so they are fully deterministic and runnable offline.

### 2.8 Test Deliverables

- This STD (test plan, design, cases, procedures, traceability, reporting).
- The automated test suite under `tests/`.
- A test log per execution (pytest output / CI record).
- A Test Summary Report instance produced after each verification cycle (§7.2).

### 2.9 Responsibilities and Schedule

| Activity | Responsible | Window (per SRS WP) |
|---|---|---|
| Unit & integration test authoring | Project team | WP2 Prototyping (Feb–Mar 2026) |
| System verification on BugTest | Project team | WP3 Experimentation (Apr–May 2026) |
| Test reporting & final consolidation | Project team | WP4 Reporting (Jun 2026) |

### 2.10 Testing Risks and Contingencies

| Risk | Impact | Contingency |
|---|---|---|
| Provider rate limits during system tests | Spurious failures | Dedicated rate-limit detection (§4.4) + configurable retries; CLI timeout raised via `DEEPTEST_CLAUDE_TIMEOUT` |
| LLM non-determinism | Flaky system results | Unit/integration use Stub LLM; system effectiveness reported statistically, not as a binary gate |
| Subprocess timeout on heavy tasks | False failure (TimeoutExpired, `total_attempts=0`) | Re-run affected task at a raised timeout; distinguish infrastructure timeouts from genuine test failures in the log |
| Environment drift (missing pytest) | Every run reads as failure | Pre-flight check that pytest is importable in the validator environment |

---

## 3. Test Design Specification

### 3.1 Unit-Level Design

Each unit suite isolates one component behind fixtures. Design intents:

- **SafeEditor (`test_safe_edit_file.py`).** Drive every branch of the safety
  policy and the edit-mode dispatch using a temporary workspace seeded with a
  baseline import test. Assert acceptance, rejection, revert, and failure-mode
  tagging.
- **Agent loop (`test_agent_loop.py`).** Replace the LLM with a Stub that emits a
  scripted tool-call sequence; assert termination conditions, instrumentation
  propagation (tokens, capabilities, failure-mode counts, `reasoning_filled`),
  parallel-call handling, and the stop-on-bug short-circuit.
- **Capabilities (`test_capabilities.py`).** Assert every model in the YAML
  registry resolves to a complete capability row and that tool naming matches the
  provider class (Claude CLI native names vs. orchestrator names).
- **Rate-limit detection (`test_claude_limit_detection.py`).** Assert genuine
  provider limit signals are detected while limit-like strings embedded in
  generated test code are **not** misclassified.
- **Data models (`test_models_compat.py`).** Assert v1 records still load (backward
  compat), v2 records round-trip, and invalid enum values are rejected.
- **Prompt rendering (`test_prompt_render.py`).** Assert deterministic hashing,
  version stamping, required sections, and cross-module failure-mode-name
  consistency (the fairness contract).

### 3.2 Integration-Level Design

`test_v2_integration.py` composes the prompt stack, capability layer, and
orchestrator across **every** registered model: it renders prompts, builds an
orchestrator, selects the tool registry from the problem string, asserts
failure-mode-name agreement across modules, and confirms the non-deep pipeline
stamps the prompt version onto its run records.

### 3.3 System-Level Design

`test_benchmark.py` exercises a representative bug-revealing scenario
end-to-end against a known buggy/fixed pair, asserting the oracle predicate. At
full scale, the benchmark runner executes the BugTest surface per task with
per-task workspace isolation and emits one run artefact per task (SDD §5.2.3);
the deterministic oracle classifies each.

---

## 4. Test Case Specifications

Test case identifiers use the scheme `TC-<group>-<n>`. Each row is a realised,
executable pytest case. "Trace" links to the SDD §7.1 requirement(s).

### 4.1 SafeEditor and ReasoningEnvelope — `tests/test_safe_edit_file.py`

Objective: verify the safe-edit policy and reasoning-gate contract.
Pre-condition: temporary workspace seeded with a baseline import test.
Trace: **FR-03, FR-04, NFR-02, NFR-03.**

| TC ID | Case (pytest) | Expected result |
|---|---|---|
| TC-SE-01 | `test_append_path_adds_after_baseline` | New test appended after the baseline; both present |
| TC-SE-02 | `test_append_is_default_mode` | Absent mode flag defaults to append |
| TC-SE-03 | `test_replace_mode_substitutes_old_string` | `old_string` replaced by `new_string` |
| TC-SE-04 | `test_replace_with_missing_old_string_returns_diagnostic` | Edit rejected with a diagnostic, workspace unchanged |
| TC-SE-05 | `test_invalid_mode_string_tags_mode_conflict` | `mode_conflict` failure tag |
| TC-SE-06 | `test_append_with_old_string_tags_mode_conflict` | `mode_conflict` failure tag |
| TC-SE-07 | `test_replace_without_new_string_tags_mode_conflict` | `mode_conflict` failure tag |
| TC-SE-08 | `test_append_without_append_param_tags_mode_conflict` | `mode_conflict` failure tag |
| TC-SE-09 | `test_path_outside_tests_tags_path_failure` | Out-of-bounds path rejected (workspace confinement) |
| TC-SE-10 | `test_syntax_error_reverts_and_tags_revert_syntax` | Syntactically invalid edit reverted; `revert_syntax` tag |
| TC-SE-11 | `test_reasoning_filled_true_when_any_field_set` | `reasoning_filled = true` when any envelope field is set |
| TC-SE-12 | `test_reasoning_filled_false_when_all_fields_empty` | `reasoning_filled = false` when envelope is empty |
| TC-SE-13 | `test_no_context_does_not_crash` | Missing reasoning context degrades gracefully, no crash |

(The suite contains 13 test functions, enumerated above; all must pass.)

### 4.2 Agent ReAct Loop — `tests/test_agent_loop.py`

Objective: verify loop termination, instrumentation, and guardrails using a Stub
LLM. Trace: **FR-05.**

| TC ID | Case (pytest) | Expected result |
|---|---|---|
| TC-AG-01 | `test_no_tool_calls_completes_immediately` | Response with no tool calls → status `completed` |
| TC-AG-02 | `test_capabilities_used_propagates_to_result` | Capability usage recorded on `AgentResult` |
| TC-AG-03 | `test_parallel_tool_calls_kept_when_capability_allows` | Parallel calls preserved when capability permits |
| TC-AG-04 | `test_parallel_calls_truncated_when_capability_forbids` | Parallel calls truncated to one when forbidden |
| TC-AG-05 | `test_stop_on_bug_revealed_short_circuits` | Loop short-circuits once a bug is revealed |
| TC-AG-06 | `test_reasoning_filled_propagates_when_any_call_sets_it` | `reasoning_filled` propagates to the result |
| TC-AG-07 | `test_failure_mode_counts_propagate_to_result` | Tool failure-mode counts recorded on the result |
| TC-AG-08 | `test_max_steps_exit_keeps_instrumentation` | `max_steps` exit still carries token/step instrumentation |

### 4.3 Provider Capabilities and Routing — `tests/test_capabilities.py`

Objective: verify capability resolution and prefix routing. Trace: **FR-09,
NFR-05.**

| TC ID | Case (pytest) | Expected result |
|---|---|---|
| TC-CAP-01 | `test_for_model_returns_complete_dict_for_default` | Default model resolves to a complete capability row |
| TC-CAP-02 | `test_every_yaml_model_has_capability_row` | Every registered model has a capability row (parametrised) |
| TC-CAP-03 | `test_claude_cli_uses_native_tool_names` | Claude CLI provider exposes native tool names |
| TC-CAP-04 | `test_orchestrator_models_use_orchestrator_tool_names` | Orchestrator providers use orchestrator tool names |
| TC-CAP-05 | `test_gpt_oss_120b_is_non_parallel_non_structured` | Capability flags correct for a known model |
| TC-CAP-06 | `test_resolution_is_case_insensitive` | Model-id resolution is case-insensitive |
| TC-CAP-07 | `test_unknown_id_emits_warning_once` | Unknown id warns exactly once |
| TC-CAP-08 | `test_known_provider_prefix_does_not_warn` | Known prefix produces no warning |

### 4.4 Reliability and Rate-Limit Detection — `tests/test_claude_limit_detection.py`

Objective: detect genuine provider limits without false positives from generated
code. Trace: **NFR-07.**

| TC ID | Case (pytest) | Expected result |
|---|---|---|
| TC-REL-01 | `test_response_containing_quota_in_docstring_is_not_limit` | "quota" inside a docstring is **not** a limit |
| TC-REL-02 | `test_response_containing_429_in_test_code_is_not_limit` | "429" inside test code is **not** a limit |
| TC-REL-03 | `test_response_with_too_many_requests_in_description_is_not_limit` | Limit-like text in a description is **not** a limit |
| TC-REL-04 | `test_plain_success_with_no_signals_is_not_limit` | Clean success is **not** a limit |
| TC-REL-05 | `test_stderr_signal_always_counts` | A limit signal on stderr always counts |
| TC-REL-06 | `test_nonzero_returncode_plus_signal_anywhere_counts` | Non-zero return code + signal counts |
| TC-REL-07 | `test_json_with_is_error_true_and_signal_counts` | JSON `is_error=true` + signal counts |
| TC-REL-08 | `test_json_with_is_error_true_but_no_limit_signal_does_not_count` | `is_error=true` without a limit signal does not count |
| TC-REL-09 | `test_malformed_json_with_no_stderr_signal_is_not_limit` | Malformed JSON without a signal is not a limit |

### 4.5 Data Models and Compatibility — `tests/test_models_compat.py`

Objective: verify (de)serialisation compatibility and validation. Trace: **Data
Design §5; supports FR-08, NFR-06.**

| TC ID | Case (pytest) | Expected result |
|---|---|---|
| TC-DM-01 | `test_v1_attempt_record_still_loads` | v1 attempt record deserialises under the v2 schema |
| TC-DM-02 | `test_v1_run_record_still_loads` | v1 run record deserialises under the v2 schema |
| TC-DM-03 | `test_v2_round_trip` | v2 record serialises and re-loads unchanged |
| TC-DM-04 | `test_tool_choice_mode_rejects_unknown_value` | Unknown `tool_choice_mode` value rejected by validation |

### 4.6 Prompt Rendering and Fairness — `tests/test_prompt_render.py`

Objective: verify deterministic, version-stamped, fairness-preserving prompts.
Trace: **FR-05, FR-06, FR-07 (shared failure-mode taxonomy).**

| TC ID | Case (pytest) | Expected result |
|---|---|---|
| TC-PR-01 | `test_prompt_version_is_v2` | Prompt version stamp is v2 |
| TC-PR-02 | `test_hash_is_deterministic` | Identical inputs → identical template hash |
| TC-PR-03 | `test_hash_changes_with_max_steps` | Hash changes when the step budget changes |
| TC-PR-04 | `test_hash_changes_with_tool_names` | Hash changes when tool names change |
| TC-PR-05 | `test_two_renders_differ_only_by_tool_name_substitution` | Cross-provider renders differ only by tool-name tokens |
| TC-PR-06 | `test_prompt_contains_required_sections` | All required sections present |
| TC-PR-07 | `test_prompt_announces_step_budget` | Step budget announced in the prompt |
| TC-PR-08 | `test_prompt_mentions_failure_modes_by_name` | Failure modes named in the main prompt |
| TC-PR-09 | `test_critic_prompt_uses_same_failure_mode_names` | Critic prompt uses the same failure-mode names |
| TC-PR-10 | `test_test_writer_prompt_mentions_failure_modes` | TestWriter prompt names the failure modes |
| TC-PR-11 | `test_analyzer_prompt_requires_json_only` | Analyzer prompt enforces JSON-only output |

### 4.7 Integration — `tests/test_v2_integration.py`

Objective: verify cross-component composition for every registered model. Trace:
**FR-05, FR-06, FR-07, FR-09.**

| TC ID | Case (pytest) | Expected result |
|---|---|---|
| TC-INT-01 | `test_render_works_for_every_yaml_model` | Prompt renders for every registered model (parametrised) |
| TC-INT-02 | `test_renders_are_either_identical_or_match_provider_class` | Renders match the provider class consistently |
| TC-INT-03 | `test_orchestrator_can_be_built_for_every_model` | Orchestrator constructs for every model |
| TC-INT-04 | `test_tool_registry_choice_by_problem_string` | Tool surface selected correctly from the problem string |
| TC-INT-05 | `test_failure_mode_names_match_across_modules` | Failure-mode names agree across all modules |
| TC-INT-06 | `test_pipeline_stamps_prompt_version_on_non_deep_runs` | Non-deep pipeline stamps the prompt version |

### 4.8 System and Bug-Revealing Verification — `tests/test_benchmark.py`

Objective: verify the bug-revealing predicate end-to-end on a representative
task. Trace: **FR-01, FR-08, NFR-01.**

| TC ID | Case (pytest) | Expected result |
|---|---|---|
| TC-SYS-01 | `test_bitcount_multiple_bits` | A generated test fails on the buggy implementation and passes on the fix (bug-revealing oracle true) |

System-level execution at scale is driven by the benchmark runner (§5), which
applies the same oracle per BugTest task and emits per-run artefacts.

### 4.9 Results Tagging Utility — `tests/test_tag_v1_results.py`

Objective: verify the results-tagging utility is correct, idempotent, and
side-effect-free. Trace: **NFR-06 (evaluation tooling).**

| TC ID | Case (pytest) | Expected result |
|---|---|---|
| TC-RT-01 | `test_runrecord_shape_is_recordlike` | Run-record shape recognised |
| TC-RT-02 | `test_summary_shape_is_recordlike` | Summary shape recognised |
| TC-RT-03 | `test_random_dict_is_not_recordlike` | Arbitrary dict not misrecognised |
| TC-RT-04 | `test_tagging_is_idempotent` | Re-tagging produces no change |
| TC-RT-05 | `test_nested_records_are_tagged` | Nested records tagged recursively |
| TC-RT-06 | `test_non_record_keys_left_alone` | Non-record keys untouched |
| TC-RT-07 | `test_dry_run_does_not_write` | Dry-run performs no writes |

---

## 5. Test Procedure Specification

**Pre-conditions.** Python 3.11 virtual environment with `pytest` and project
dependencies installed; repository checked out; for system tests, at least one
provider reachable and its API key exported.

**Procedure — full automated suite (unit + integration + system sample):**

```bash
# from the repository root, inside the project virtual environment
python -m pytest tests/ -q
```

**Procedure — a single suite (example: SafeEditor):**

```bash
python -m pytest tests/test_safe_edit_file.py -v
```

**Procedure — system run at scale (BugTest surface):**

```bash
# deterministic verdict via the bug-revealing oracle; one artefact per task
python run_benchmark_v2.py [--task NAME] [--model PROVIDER:ID] [--all] [-v]
# raise the CLI subprocess cap for slow-but-valid runs when needed:
DEEPTEST_CLAUDE_TIMEOUT=300 python run_benchmark_v2.py --model claude:sonnet
```

**Post-conditions.** pytest exit code 0 for unit/integration/system-sample
suites; for the benchmark runner, one JSON artefact per task under the results
directory and a one-line summary on standard output. Temporary workspaces are
torn down automatically.

**Stopping rule.** Halt on the first uncaught exception in unit/integration
suites (treated as a blocking defect). System runs continue per task; a task that
raises is recorded with `status = error` and does not abort the batch (NFR-07).

---

## 6. Requirements Traceability Matrix

Mapping of SDD v2.0 §7.1 requirements to the test cases that verify them.

### Functional Requirements

| Req | Description (abridged) | Verifying Test Cases |
|---|---|---|
| FR-01 | Execute pytest in isolation, report structured results | TC-SYS-01 (and the TestRunner exercised by every suite) |
| FR-02 | Extract structural project model from source | Exercised via orchestrator build (TC-INT-03) and analyzer prompt (TC-PR-11) |
| FR-03 | Guarded test writing that rejects regressions | TC-SE-01 … TC-SE-10 |
| FR-04 | Require hypothesis/justification/expected outcome | TC-SE-11, TC-SE-12, TC-SE-13 |
| FR-05 | ReAct loop with step/time budget | TC-AG-01 … TC-AG-08; TC-PR-07; TC-INT-06 |
| FR-06 | Delegate understanding to Analyzer subagent | TC-PR-11; TC-INT-01, TC-INT-02 |
| FR-07 | Review tests via Critic subagent | TC-PR-09; TC-INT-05 |
| FR-08 | Batch execution + per-run artefacts | TC-DM-01 … TC-DM-03; §5 benchmark runner |
| FR-09 | Route same loop to multiple providers | TC-CAP-01 … TC-CAP-08; TC-INT-01 … TC-INT-03 |

### Non-Functional Requirements

| Req | Description (abridged) | Verifying Test Cases |
|---|---|---|
| NFR-01 | Effectiveness (bug-revealing tests produced) | TC-SYS-01; Experiment Report (quantitative) |
| NFR-02 | Safety (confinement, no regressions) | TC-SE-09, TC-SE-10; TC-SE-01 … TC-SE-08 |
| NFR-03 | Auditability (reconstructable rationale) | TC-SE-11, TC-SE-12; TC-AG-06 |
| NFR-04 | Reproducibility (re-executable runs) | Per-task fixtures; deterministic hash TC-PR-02 |
| NFR-05 | Provider independence | TC-CAP-01 … TC-CAP-08; TC-INT-02 |
| NFR-06 | Scalability (batch evaluation) | TC-DM-01 … TC-DM-03; TC-RT-01 … TC-RT-07 |
| NFR-07 | Reliability (transient failures don't crash a batch) | TC-REL-01 … TC-REL-09; §5 stopping rule |

---

## 7. Test Reporting

### 7.1 Test Log

Each execution produces a test log. The minimum recorded fields:

| Field | Meaning |
|---|---|
| Execution date/time | When the suite ran |
| Environment | OS, Python version, provider(s), commit hash |
| Suite / case id | The TC executed |
| Result | pass / fail / error / skipped |
| Duration | Wall-clock per case |
| Evidence | pytest output; for system runs, the run artefact path |

pytest's own console/`--junitxml` output satisfies this log for the automated
suites; benchmark runs additionally emit per-task JSON artefacts (SDD §5.2.3).

### 7.2 Test Summary Report (template)

To be instantiated after each verification cycle:

| Field | Value |
|---|---|
| Cycle date | _date_ |
| Build / commit | _hash_ |
| Suites executed | _n_ of 9 |
| Cases executed / passed / failed | _x / y / z_ |
| Unit result | pass / fail |
| Integration result | pass / fail |
| System sample result | pass / fail |
| Open defects | _list_ |
| Release gate (all unit+integration pass on a reference provider) | met / not met |
| Notes | infrastructure timeouts re-run, environment caveats, etc. |

### 7.3 Defect Reporting

Each failed case is logged as a defect with: id, title, the failing TC id, the
expected vs. actual result, severity (blocking / major / minor), reproduction
steps (the pytest invocation), and the linked requirement. Infrastructure
failures (e.g. a `claude -p` `TimeoutExpired` with `total_attempts=0`) are
classified separately from genuine assertion failures and are resolved by
re-running at a raised `DEEPTEST_CLAUDE_TIMEOUT`, not counted as product defects.

---

## 8. Supporting Information

### 8.1 Glossary

See §1.4 above and SDD §8.1 for the full domain glossary. Test-specific terms:
STD, SUT, TC, Fixture, Stub LLM, Oracle, Bug-Revealing Test.

### 8.2 Appendices

**Appendix A — Test Suite Inventory.** Nine automated suites under `tests/`,
totalling the cases specified in Section 4:

| Suite | Cases | Level |
|---|---|---|
| `test_safe_edit_file.py` | 13 | Unit |
| `test_agent_loop.py` | 8 | Unit |
| `test_capabilities.py` | 8 | Unit |
| `test_claude_limit_detection.py` | 9 | Unit |
| `test_models_compat.py` | 4 | Unit |
| `test_prompt_render.py` | 11 | Unit |
| `test_v2_integration.py` | 6 | Integration |
| `test_benchmark.py` | 1 | System |
| `test_tag_v1_results.py` | 7 | Unit (tooling) |
| **Total** | **67** | — |

**Appendix B — Tools.** pytest (execution), pydantic (model validation in data
tests), pyyaml (model registry), and the provider SDKs (exercised indirectly).
The bug-revealing oracle is implemented in `bugtest/validator.py`.

**Appendix C — Relationship to other documents.** This STD realises SDD v2.0
§7.2 (Verification Strategy) and traces to SDD §7.1 (Requirements Mapping).
Measured results are reported in the project's Experiment Report.
