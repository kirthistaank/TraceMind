# RAGAS Test Suite Results

**Date:** 2026-06-03 23:02:59

## Summary Statistics

- Total scenarios tested: 10
- Valid results: 10
- Correct dispositions: 4/10
- Mean RAGAS Score: 0.314
- Mean Clinical Score: 0.522
- Mean Extraction Accuracy: 0.720

## Per-Scenario Results

| scenario_id                            | expected_disposition   | predicted_disposition   | disposition_correct   |   ragas_score |   clinical_score |   extraction_accuracy |   faithfulness |
|:---------------------------------------|:-----------------------|:------------------------|:----------------------|--------------:|-----------------:|----------------------:|---------------:|
| scenario_1_home_management             | HOME_MANAGEMENT        | HOME_MANAGEMENT         | True                  |         0.444 |            0.917 |                 0.667 |              3 |
| scenario_2_er_now                      | ER_NOW                 | ER_NOW                  | True                  |         0.5   |            1     |                 1     |              3 |
| scenario_3_urgent_same_day             | URGENT_SAME_DAY        | URGENT_SAME_DAY         | True                  |         0.5   |            0.917 |                 1     |              3 |
| scenario_4_gray_zone_throat_pain       | OUT_OF_SCOPE           | ER_NOW                  | False                 |         0.389 |            0.667 |                 0.667 |              3 |
| scenario_5_incomplete_intake           | OUT_OF_SCOPE           | OUT_OF_SCOPE            | True                  |         0.5   |            0.583 |                 1     |              1 |
| scenario_6_newborn_fever               | ER_NOW                 | OUT_OF_SCOPE            | False                 |         0.122 |            0.183 |                 0.4   |              1 |
| scenario_7_mild_cold                   | HOME_MANAGEMENT        | OUT_OF_SCOPE            | False                 |         0.189 |            0.283 |                 0.8   |              1 |
| scenario_8_diarrhea_dehydration        | URGENT_SAME_DAY        | OUT_OF_SCOPE            | False                 |         0.194 |            0.208 |                 0.5   |              1 |
| scenario_9_acetaminophen_overdose_risk | URGENT_SAME_DAY        | OUT_OF_SCOPE            | False                 |         0.139 |            0.208 |                 0.5   |              1 |
| scenario_10_post_immunization_fever    | HOME_MANAGEMENT        | OUT_OF_SCOPE            | False                 |         0.167 |            0.25  |                 0.667 |              1 |

## Metric Breakdown

- **extraction_accuracy**: 0.720
- **faithfulness**: 1.800
- **answer_relevance**: 1.400
- **context_relevance**: 0.000
- **context_recall**: 0.100
- **context_precision**: 0.000
