# Release moment from the ball's arc (PLAN_5 A2)

Ball: the tracker's followed ball from the scoreboard replay (weak observations included). Window: 3.0 s before the label's start to its end. No model. Report only: no release frame has been checked against the footage yet.

| camera class | shots | got a release | no release | median flight (s) | p90 flight (s) | median tracked points in window |
| --- | --- | --- | --- | --- | --- | --- |
| fixed/single | 68 | 68 | 0 | 0.63 | 0.73 | 74 |
| moving/single | 162 | 147 | 15 | 0.17 | 0.45 | 84 |
| moving/multi | 103 | 97 | 6 | 0.00 | 0.52 | 127 |
| **all** | 333 | 312 | 21 | 0.20 | 0.67 | 96 |

## Failure reasons (no release), by camera class

| camera class | no_apex |
| --- | --- |
| fixed/single | 0 |
| moving/single | 15 |
| moving/multi | 6 |
| **all** | 21 |

## Why the fit stopped (shots with a release)

| stop reason | shots |
| --- | --- |
| curvature | 55 |
| gap | 94 |
| ran_out | 8 |
| residual | 155 |

Shots processed: 333 (248 makes, 85 misses).
