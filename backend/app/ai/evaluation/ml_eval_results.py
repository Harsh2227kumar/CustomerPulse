"""
ML Model Evaluation Results Tracker for CustomerPulse.

Tracks test runs and evaluation results for four ML modules:
- sentiment (predict_sentiment)
- classifier (classify_category)
- urgency (estimate_urgency)
- confidence (combine_confidence)
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ModelTestResult:
    """Result from a single ML model test run."""
    
    version_name: str
    test_input: Any
    expected_output: Any
    actual_output: Any
    confidence_score: float
    reason_codes: list[str] = field(default_factory=list)
    notes: str = ""
    passed: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MLEvaluationStore:
    """Centralized store for ML model evaluation results."""
    
    def __init__(self) -> None:
        """Initialize empty results store for all modules."""
        self.results: dict[str, list[ModelTestResult]] = {
            "sentiment": [],
            "classifier": [],
            "urgency": [],
            "confidence": [],
        }
    
    def add_result(
        self,
        module: str,
        version_name: str,
        test_input: Any,
        expected_output: Any,
        actual_output: Any,
        confidence_score: float,
        passed: bool,
        reason_codes: list[str] | None = None,
        notes: str = "",
    ) -> None:
        """
        Add a test result to the evaluation store.
        
        Args:
            module: One of ["sentiment", "classifier", "urgency", "confidence"]
            version_name: Version identifier (e.g., "v1.0", "approach_a")
            test_input: The input provided to the model
            expected_output: The expected output
            actual_output: The actual output from the model
            confidence_score: Model confidence (0.0 to 1.0)
            passed: Whether the test passed
            reason_codes: Optional list of reason codes explaining the result
            notes: Optional notes about the test
        
        Raises:
            ValueError: If module is not valid
        """
        if module not in self.results:
            raise ValueError(
                f"Invalid module: {module}. Must be one of {list(self.results.keys())}"
            )
        
        result = ModelTestResult(
            version_name=version_name,
            test_input=test_input,
            expected_output=expected_output,
            actual_output=actual_output,
            confidence_score=confidence_score,
            reason_codes=reason_codes or [],
            notes=notes,
            passed=passed,
        )
        
        self.results[module].append(result)
    
    def print_summary(self) -> None:
        """
        Print a comprehensive summary of evaluation results per module.
        
        Displays:
        - Total tests run per module
        - Pass rate percentage
        - Average confidence score
        - List of failed cases with inputs and outputs
        """
        print("\n" + "=" * 80)
        print("ML MODEL EVALUATION SUMMARY")
        print("=" * 80)
        
        for module, results in self.results.items():
            print(f"\n{module.upper()} Module")
            print("-" * 80)
            
            if not results:
                print("  No test results found.\n")
                continue
            
            total = len(results)
            passed = sum(1 for r in results if r.passed)
            pass_rate = (passed / total * 100) if total > 0 else 0.0
            avg_confidence = (
                sum(r.confidence_score for r in results) / total if total > 0 else 0.0
            )
            
            print(f"  Total tests run: {total}")
            print(f"  Pass rate: {pass_rate:.1f}% ({passed}/{total})")
            print(f"  Average confidence score: {avg_confidence:.3f}")
            
            failed = [r for r in results if not r.passed]
            if failed:
                print(f"\n  Failed cases ({len(failed)}):")
                for i, result in enumerate(failed, 1):
                    print(f"\n    [{i}] {result.version_name}")
                    print(f"        Input: {result.test_input}")
                    print(f"        Expected: {result.expected_output}")
                    print(f"        Actual: {result.actual_output}")
                    print(f"        Confidence: {result.confidence_score:.3f}")
                    if result.reason_codes:
                        print(f"        Reason codes: {', '.join(result.reason_codes)}")
                    if result.notes:
                        print(f"        Notes: {result.notes}")
            else:
                print("  All tests passed! ✓")
            
            print()
        
        print("=" * 80 + "\n")
    
    def export_to_json(self, filepath: str) -> None:
        """
        Export all evaluation results to a JSON file.
        
        Args:
            filepath: Destination file path for JSON export
        
        Raises:
            IOError: If file cannot be written
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        export_data = {
            module: [asdict(result) for result in results]
            for module, results in self.results.items()
        }
        
        with open(path, "w") as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Evaluation results exported to: {path}")
    
    def get_module_stats(self, module: str) -> dict[str, Any]:
        """
        Get statistics for a specific module.
        
        Args:
            module: Module name
        
        Returns:
            Dictionary with total, passed, pass_rate, and avg_confidence
        
        Raises:
            ValueError: If module is not valid
        """
        if module not in self.results:
            raise ValueError(
                f"Invalid module: {module}. Must be one of {list(self.results.keys())}"
            )
        
        results = self.results[module]
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        pass_rate = (passed / total * 100) if total > 0 else 0.0
        avg_confidence = (
            sum(r.confidence_score for r in results) / total if total > 0 else 0.0
        )
        
        return {
            "total": total,
            "passed": passed,
            "pass_rate": pass_rate,
            "avg_confidence": avg_confidence,
        }


# Global evaluation store instance
evaluation_store = MLEvaluationStore()


if __name__ == "__main__":
    # Example usage with dummy entries
    
    # v1_bfsi_phrases sentiment test cases
    evaluation_store.add_result(
        module="sentiment",
        version_name="v1_bfsi_phrases",
        test_input="My account has been locked due to suspicious activity.",
        expected_output="negative",
        actual_output="negative",
        confidence_score=0.89,
        passed=True,
        reason_codes=["negative_keywords", "account_issue"],
        notes="Correctly identified negative sentiment for account security issue",
    )
    
    evaluation_store.add_result(
        module="sentiment",
        version_name="v1_bfsi_phrases",
        test_input="I received my loan approval and I'm very happy!",
        expected_output="positive",
        actual_output="positive",
        confidence_score=0.91,
        passed=True,
        reason_codes=["positive_keywords", "approval"],
        notes="Positive sentiment for successful loan application",
    )
    
    evaluation_store.add_result(
        module="sentiment",
        version_name="v1_bfsi_phrases",
        test_input="The interest rate is still too high compared to competitors.",
        expected_output="negative",
        actual_output="negative",
        confidence_score=0.85,
        passed=True,
        reason_codes=["complaint_tone", "comparison"],
        notes="Correctly detected negative sentiment in rate complaint",
    )
    
    evaluation_store.add_result(
        module="sentiment",
        version_name="v1_bfsi_phrases",
        test_input="I need to update my account details and verify my identity.",
        expected_output="neutral",
        actual_output="neutral",
        confidence_score=0.78,
        passed=True,
        reason_codes=["procedural_language", "factual"],
        notes="Correctly identified neutral sentiment for procedural request",
    )
    
    evaluation_store.add_result(
        module="sentiment",
        version_name="v1_bfsi_phrases",
        test_input="Payment failed but I got good customer support to resolve it.",
        expected_output="positive",
        actual_output="positive",
        confidence_score=0.82,
        passed=True,
        reason_codes=["payment_failed", "positive_service"],
        notes="Mixed case — POSITIVE acceptable, payment_failed reason code preserved",
    )
    
    # v1_cfpb_mapping classifier test cases
    evaluation_store.add_result(
        module="classifier",
        version_name="v1_cfpb_mapping",
        test_input="My credit card payment wasn't processed and I was charged twice.",
        expected_output="billing",
        actual_output="billing",
        confidence_score=0.70,
        passed=True,
        reason_codes=["payment_keywords", "double_charge"],
        notes="confidence 0.70 acceptable, conservative scoring",
    )
    
    evaluation_store.add_result(
        module="classifier",
        version_name="v1_cfpb_mapping",
        test_input="Unauthorized transactions appeared on my account.",
        expected_output="fraud",
        actual_output="fraud",
        confidence_score=0.92,
        passed=True,
        reason_codes=["unauthorized", "fraudulent_activity"],
        notes="Clear fraud pattern detected with high confidence",
    )
    
    evaluation_store.add_result(
        module="classifier",
        version_name="v1_cfpb_mapping",
        test_input="My loan was denied without proper explanation.",
        expected_output="lending",
        actual_output="lending",
        confidence_score=0.85,
        passed=True,
        reason_codes=["loan_keywords", "denial"],
        notes="Lending category correctly identified",
    )
    
    evaluation_store.add_result(
        module="classifier",
        version_name="v1_cfpb_mapping",
        test_input="My credit report contains errors and incorrect accounts.",
        expected_output="credit_reporting",
        actual_output="credit_reporting",
        confidence_score=0.88,
        passed=True,
        reason_codes=["credit_report", "errors"],
        notes="Credit reporting issue correctly classified",
    )
    
    evaluation_store.add_result(
        module="classifier",
        version_name="v1_cfpb_mapping",
        test_input="I cannot reach customer service by phone or email.",
        expected_output="customer_service",
        actual_output="customer_service",
        confidence_score=0.79,
        passed=True,
        reason_codes=["communication_issue", "service_access"],
        notes="Customer service issue properly categorized",
    )
    
    evaluation_store.add_result(
        module="classifier",
        version_name="v1_cfpb_mapping",
        test_input="The bank is not complying with regulatory requirements.",
        expected_output="regulatory_compliance",
        actual_output="regulatory_compliance",
        confidence_score=0.84,
        passed=True,
        reason_codes=["compliance", "regulatory_terms"],
        notes="Compliance issue successfully detected",
    )
    
    # v1_case_risk urgency test cases
    evaluation_store.add_result(
        module="urgency",
        version_name="v1_case_risk",
        test_input="My account was compromised due to identity theft.",
        expected_output=85,
        actual_output=85,
        confidence_score=0.70,
        passed=True,
        reason_codes=["financial_harm", "identity_theft", "case_risk_high"],
        notes="churn_risk replaced with case_risk. Score+reason based risk derivation working correctly.",
    )
    
    evaluation_store.add_result(
        module="urgency",
        version_name="v1_case_risk",
        test_input="I cannot access my account for 3 days.",
        expected_output=70,
        actual_output=70,
        confidence_score=0.65,
        passed=True,
        reason_codes=["account_access", "waiting_terms", "case_risk_medium"],
        notes="Service disruption correctly escalated",
    )
    
    evaluation_store.add_result(
        module="urgency",
        version_name="v1_case_risk",
        test_input="Foreclosure proceedings have started.",
        expected_output=80,
        actual_output=80,
        confidence_score=0.72,
        passed=True,
        reason_codes=["foreclosure", "legal_terms", "case_risk_critical"],
        notes="Critical legal matter properly prioritized",
    )
    
    evaluation_store.add_result(
        module="urgency",
        version_name="v1_case_risk",
        test_input="I filed for bankruptcy.",
        expected_output=75,
        actual_output=75,
        confidence_score=0.70,
        passed=True,
        reason_codes=["bankruptcy", "legal_terms", "case_risk_high"],
        notes="Bankruptcy case correctly identified and escalated",
    )
    
    evaluation_store.add_result(
        module="urgency",
        version_name="v1_case_risk",
        test_input="Multiple unauthorized charges and I need immediate help.",
        expected_output=78,
        actual_output=78,
        confidence_score=0.68,
        passed=True,
        reason_codes=["financial_harm", "escalation_terms", "case_risk_high"],
        notes="Escalation language with financial impact correctly scored",
    )
    
    evaluation_store.add_result(
        module="urgency",
        version_name="v1_case_risk",
        test_input="I would like to update my mailing address.",
        expected_output=30,
        actual_output=30,
        confidence_score=0.55,
        passed=True,
        reason_codes=["administrative", "case_risk_low"],
        notes="Routine administrative request correctly deprioritized",
    )
    
    # Print summary report
    evaluation_store.print_summary()
    
    # Export to JSON
    evaluation_store.export_to_json("/tmp/ml_evaluation_results.json")
    
    # Get individual module stats
    sentiment_stats = evaluation_store.get_module_stats("sentiment")
    print(f"Sentiment module stats: {sentiment_stats}")
