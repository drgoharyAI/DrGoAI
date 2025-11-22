"""
Integration Example: How to use pipeline improvements in your main process_request
----------------------------------------------------------------------------------
This shows the key changes to make in your async_approval_pipeline.py
"""

# Add these imports at the top of async_approval_pipeline.py:
from scripts.pipeline_improvements import (
    pre_filter_checks,
    get_few_shot_examples,
    build_enhanced_decision_prompt,
    validate_and_fix_decisions,
    route_by_confidence
)


# Replace/modify the relevant sections in process_request():

async def process_request_improved(payload: Dict[str, Any], *, verbose: int = 0) -> Dict[str, Any]:
    """
    Improved version of process_request with accuracy enhancements.
    """
    # ... [keep existing code for loading resources and extracting fields] ...

    #####################################################################
    # NEW STEP: Apply rule-based pre-filters BEFORE any LLM calls
    #####################################################################
    pre_filter_results = pre_filter_checks(payload, items)

    # Separate items that need LLM evaluation from those already decided
    items_for_llm = []
    rule_based_decisions = []

    for i, (item, pre_result) in enumerate(zip(items, pre_filter_results)):
        if pre_result is not None:
            # Deterministic decision made
            rule_based_decisions.append(pre_result)
            logger.info(f"Item {i} decided by rule: {pre_result['decision']} - {pre_result['rejection_code']}")
        else:
            # Needs LLM evaluation
            items_for_llm.append(item)
            rule_based_decisions.append(None)  # Placeholder

    # If all items were decided by rules, skip LLM
    if not items_for_llm:
        parsed_blocks = [d for d in rule_based_decisions if d is not None]
        # ... continue to output assembly ...

    #####################################################################
    # MODIFIED: Build items_narrative only for items needing LLM
    #####################################################################
    items_narrative_for_llm = format_items_narrative(
        items_for_llm,
        approval_no,
        icd_info,
        chief_complaint,
        attachments_texts
    )

    #####################################################################
    # EXISTING: Run prerequisite prompts (policy, underwriting, etc.)
    # Keep this section as-is
    #####################################################################
    results = await llm_async_many(prompts)

    # Extract results
    policy_findings = results.get('policy', [''])[0]
    underwriting_findings = results.get('underwriting', [''])[0]
    current_conditions = results.get('current_conditions', [''])[0]
    patient_history_summary = results.get('history', [''])[0]
    radiology_findings = results.get('radiology', [''])[0]
    lab_findings = results.get('lab', [''])[0]
    health_declaration_findings = results.get('health_declaration', [''])[0] if 'health_declaration' in results else ''
    service_category = results.get('category', [''])[0].strip()

    #####################################################################
    # NEW: Use enhanced decision prompt with few-shot examples
    #####################################################################
    decision_prompt = build_enhanced_decision_prompt(
        service_category=service_category,
        items_narrative=items_narrative_for_llm,
        current_conditions=current_conditions,
        patient_history_summary=patient_history_summary,
        radiology_findings=radiology_findings,
        lab_findings=lab_findings,
        health_declaration_findings=health_declaration_findings,
        policy_findings=policy_findings,
        underwriting_findings=underwriting_findings,
        rejection_codes=rejection_codes
    )

    #####################################################################
    # Execute decision prompt (same as before)
    #####################################################################
    decision_text, _ = await llm_async(decision_prompt, max_tokens=1500, temperature=0.0)
    decision_json = extract_json(decision_text)

    #####################################################################
    # NEW: Validate and fix LLM decisions
    #####################################################################
    validated_decisions = validate_and_fix_decisions(
        decisions=decision_json,
        items=items_for_llm,
        health_declaration_findings=health_declaration_findings,
        policy_findings=policy_findings
    )

    #####################################################################
    # NEW: Merge rule-based and LLM decisions
    #####################################################################
    llm_decision_iter = iter(validated_decisions)
    final_decisions = []

    for rule_decision in rule_based_decisions:
        if rule_decision is not None:
            # Use rule-based decision
            final_decisions.append({
                "Service Name": rule_decision['service_name'],
                "Internal Code": rule_decision['internal_code'],
                "Decision": rule_decision['decision'],
                "Justification": rule_decision['justification'],
                "approval_no": approval_no,
                "predict_label": rule_decision['decision'],
                "target_label": "",
                "rejection_code": rule_decision['rejection_code'],
                "item_sequence": rule_decision['item_sequence'],
                "confidence": rule_decision.get('confidence', 1.0),
                "rule_based": True
            })
        else:
            # Use LLM decision
            llm_decision = next(llm_decision_iter)
            final_decisions.append({
                "Service Name": llm_decision.get('service_name'),
                "Internal Code": llm_decision.get('internal_code'),
                "Decision": llm_decision.get('decision'),
                "Justification": llm_decision.get('justification'),
                "approval_no": approval_no,
                "predict_label": llm_decision.get('decision'),
                "target_label": "",
                "rejection_code": llm_decision.get('rejection_code', ''),
                "item_sequence": llm_decision.get('item_sequence'),
                "confidence": llm_decision.get('confidence', 0.8),
                "needs_review": llm_decision.get('needs_review', False),
                "rule_based": False
            })

    #####################################################################
    # NEW: Route by confidence for human review workflow
    #####################################################################
    routed = route_by_confidence(final_decisions)

    # Log routing statistics
    logger.info(f"Decision routing: {len(routed['auto_approve'])} auto-approve, "
                f"{len(routed['auto_deny'])} auto-deny, "
                f"{len(routed['needs_review'])} needs review")

    #####################################################################
    # Use final_decisions as parsed_blocks for output
    #####################################################################
    parsed_blocks = final_decisions
    ui_output_8 = parsed_blocks

    # Add routing info to outputs
    outputs = {
        # ... existing outputs ...
        'ui_output_8': ui_output_8,
        'routing': routed,  # NEW: for workflow integration
    }

    return {
        'outputs': outputs,
        'metrics': metrics,
        'logs': logs,
        'errors': errors,
    }


#############################################################################
# TESTING: Accuracy evaluation on labeled test set
#############################################################################

async def evaluate_accuracy(test_cases: List[Dict], verbose: bool = False):
    """
    Run pipeline on labeled test cases and compute accuracy.

    test_cases format:
    [
        {
            "payload": {...},
            "expected": [
                {
                    "service_name": "...",
                    "decision": "Approved" | "Disapproved",
                    "rejection_code": "..." (if disapproved)
                }
            ]
        }
    ]
    """
    from scripts.pipeline_improvements import evaluate_prediction, aggregate_evaluation

    all_evaluations = []
    category_evaluations = {}

    for i, case in enumerate(test_cases):
        # Run pipeline
        result = await process_request_improved(case['payload'], verbose=0)
        predictions = result['outputs'].get('ui_output_8', [])
        expected = case['expected']
        category = result['outputs'].get('ui_output_9', 'Unknown')

        # Evaluate each service
        for pred, exp in zip(predictions, expected):
            eval_result = evaluate_prediction(pred, exp)
            eval_result['category'] = category
            all_evaluations.append(eval_result)

            # Track by category
            if category not in category_evaluations:
                category_evaluations[category] = []
            category_evaluations[category].append(eval_result)

            if verbose and not eval_result['is_correct']:
                print(f"ERROR in case {i}: {pred['Service Name']}")
                print(f"  Predicted: {pred['Decision']} ({pred.get('rejection_code', '')})")
                print(f"  Expected: {exp['decision']} ({exp.get('rejection_code', '')})")
                print(f"  Confidence: {pred.get('confidence', 'N/A')}")
                print()

    # Aggregate results
    overall = aggregate_evaluation(all_evaluations)
    by_category = {cat: aggregate_evaluation(evals) for cat, evals in category_evaluations.items()}

    print("\n" + "="*60)
    print("ACCURACY EVALUATION RESULTS")
    print("="*60)
    print(f"Overall Accuracy: {overall['accuracy']*100:.1f}%")
    print(f"Total Cases: {overall['total']}")
    print(f"Correct: {overall['correct']}")
    print(f"False Positives (wrongly approved): {overall['false_positives']}")
    print(f"False Negatives (wrongly denied): {overall['false_negatives']}")
    print(f"Rejection Code Accuracy: {overall['code_accuracy']*100:.1f}%")
    print(f"High Confidence (>=0.9) Accuracy: {overall['high_confidence_accuracy']*100:.1f}%")
    print()

    print("By Category:")
    for cat, metrics in sorted(by_category.items()):
        print(f"  {cat}: {metrics['accuracy']*100:.1f}% ({metrics['correct']}/{metrics['total']})")

    return {
        'overall': overall,
        'by_category': by_category,
        'evaluations': all_evaluations
    }


#############################################################################
# EXAMPLE: Running evaluation
#############################################################################

if __name__ == '__main__':
    import asyncio
    import json

    # Load your test cases
    # test_cases = json.load(open('test_cases_labeled.json'))

    # Example test case structure:
    test_cases = [
        {
            "payload": {
                "approval_no": "TEST001",
                "member_name": "Test Patient",
                "birth_date": "2024-06-15",  # 5 months old
                "sex": "M",
                "items": [
                    {
                        "product_service_display": "SIMILAC ALIMENTUM 400G",
                        "item_sequence": 1,
                        "item_quantity": 6
                    }
                ],
                "icd": {
                    "diagnosis_free_desc": "Cow milk protein allergy"
                },
                "chief_complaint": "Infant with confirmed CMPA requiring special formula",
                "supporting_info": []
            },
            "expected": [
                {
                    "service_name": "SIMILAC ALIMENTUM 400G",
                    "decision": "Approved",
                    "rejection_code": ""
                }
            ]
        }
    ]

    # Run evaluation
    # results = asyncio.run(evaluate_accuracy(test_cases, verbose=True))
    print("Integration example loaded. Modify process_request() with these improvements.")
