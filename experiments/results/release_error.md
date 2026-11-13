# Release finder error (PLAN_5 Part B)

Error = finder frame minus owner frame. Negative means the finder is early.

- Owner rows scored: 20
- Owner rows where the finder gave no release: 0
- Owner rows with no finder record: 0
- CANT_TELL rows: 0

| Measure | Frames | Milliseconds |
| --- | --- | --- |
| Median absolute error | 4.0 | 133 |
| p90 absolute error | 5.0 | 167 |
| Signed mean (early < 0 < late) | -2.75 | -92 |

| Within | Shots | Share |
| --- | --- | --- |
| ±2 frames | 2/20 | 10% |
| ±5 frames | 20/20 | 100% |

Worst 3:

| Clip | Label start-end | Owner | Finder | Error | Stop reason |
| --- | --- | --- | --- | --- | --- |
| aggie_NathanBBall.mov | 66-117 | 48 | 43 | -5 | residual |
| aggie_NathanBBall.mov | 205-239 | 186 | 181 | -5 | residual |
| chonyy_two_score_three_miss.mp4 | 55-90 | 29 | 24 | -5 | residual |

All rows:

| Clip | Label start-end | Owner | Finder | Error | Stop reason |
| --- | --- | --- | --- | --- | --- |
| lf_shot_detection.mp4 | 55-82 | 43 | 45 | +2 | gap |
| lf_shot_detection.mp4 | 161-195 | 148 | 151 | +3 | gap |
| lf_shot_detection.mp4 | 272-303 | 261 | 258 | -3 | gap |
| lf_shot_detection.mp4 | 370-413 | 359 | 356 | -3 | gap |
| lf_shot_detection.mp4 | 503-532 | 491 | 494 | +3 | gap |
| lf_shot_detection.mp4 | 600-640 | 588 | 591 | +3 | gap |
| lf_back.mp4 | 44-75 | 33 | 29 | -4 | residual |
| lf_back.mp4 | 140-182 | 138 | 135 | -3 | residual |
| lf_back.mp4 | 261-297 | 251 | 247 | -4 | residual |
| lf_back.mp4 | 359-389 | 349 | 345 | -4 | residual |
| lf_back.mp4 | 491-525 | 482 | 477 | -5 | residual |
| lf_back.mp4 | 588-626 | 579 | 574 | -5 | residual |
| chonyy_two_score_three_miss.mp4 | 55-90 | 29 | 24 | -5 | residual |
| chonyy_two_score_three_miss.mp4 | 150-195 | 133 | 128 | -5 | residual |
| chonyy_two_score_three_miss.mp4 | 262-292 | 242 | 237 | -5 | residual |
| chonyy_two_score_three_miss.mp4 | 362-390 | 343 | 338 | -5 | residual |
| chonyy_two_score_three_miss.mp4 | 460-486 | 443 | 438 | -5 | residual |
| aggie_NathanBBall.mov | 66-117 | 48 | 43 | -5 | residual |
| aggie_NathanBBall.mov | 205-239 | 186 | 181 | -5 | residual |
| aggie_NathanBBall.mov | 308-351 | 289 | 289 | +0 | gap |
