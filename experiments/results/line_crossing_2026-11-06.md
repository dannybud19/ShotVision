# Line-through-the-rim side by side (PLAN 2)

## Summary

| variant | makes counted / makes | false makes / misses | spurious makes | 95% upper bound | in-scope makes counted | in-scope false+spurious | legacy GitHub clips |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SV | 158/244 | 0/85 | 5 | 12.0% | 0/0 | 0 | 56/63 makes, 0 false+spur |
| L0 | 160/244 | 18/85 | 28 | 63.4% | 0/0 | 0 | 56/63 makes, 5 false+spur |
| L1 | 155/244 | 17/85 | 23 | 56.5% | 0/0 | 0 | 56/63 makes, 4 false+spur |
| L2 | 148/244 | 17/85 | 21 | 54.2% | 0/0 | 0 | 51/63 makes, 4 false+spur |
| L3 | 138/244 | 11/85 | 18 | 43.5% | 0/0 | 0 | 51/63 makes, 3 false+spur |
| L4 | 118/244 | 12/85 | 16 | 42.3% | 0/0 | 0 | 50/63 makes, 2 false+spur |
| H1 | 163/244 | 2/85 | 6 | 16.3% | 0/0 | 0 | 56/63 makes, 0 false+spur |
| H2 | 177/244 | 3/85 | 16 | 31.1% | 0/0 | 0 | 58/63 makes, 1 false+spur |
| H3 | 175/244 | 4/85 | 15 | 31.1% | 0/0 | 0 | 58/63 makes, 1 false+spur |

_In-scope columns are empty: labels.json has no camera_class / ball_count fields, so every clip reports as unclassified._

## Gate A per variant

_Note: the "Lost makes by exit reason" lines in the L0-L4 Gate A blocks are placeholders (all L0-L4 misses carry MISS_BELOW_WITHOUT_INNER and all makes MAKE_CONFIRMED). The real decision-path breakdown is in the section below and in the JSON._

### SV
```
=== Gate A ===
Makes counted: 158/244 (64.8%)  [need >= 90%]
False makes: 0/85 labeled misses, + 5 spurious makes -> 95% upper bound on false-make rate 12.0%  [need 0 false makes]
By miss type (misses, false makes, resolved as MISS, 95% UB):
  airball           1    0    1   95.0%
  back_rim         23    0   19   12.2%
  front_rim        36    0   26    8.0%
  other            13    0    7   20.6%
  side_rim_out     12    0   10   22.1%
By source (makes counted/makes, false makes/misses):
  commons:bandits_practice   53/87     1/18  
  commons:hardwick_game    23/43     0/31  
  commons:hardwick_game_HELDOUT_for_tracker_fix   26/51     4/28  
  github:aggie              5/5      0/1   
  github:artur              3/3      0/1   
  github:chonyy             4/4      0/4   
  github:kyle               0/1      0/0   
  github:lf                18/20     0/2   
  github:video_test_5      26/30     0/0   
Lost makes by exit reason:
  make lost: never armed                   57
  make lost: miss_occlusion_gap            12
  make lost: miss_below_without_inner      10
  make lost: miss_rim_out_sideways         6
  make lost: miss_in_and_out               1
GATE A: FAIL
```

### L0
```
=== Gate A ===
Makes counted: 160/244 (65.6%)  [need >= 90%]
False makes: 18/85 labeled misses, + 28 spurious makes -> 95% upper bound on false-make rate 63.4%  [need 0 false makes]
By miss type (misses, false makes, resolved as MISS, 95% UB):
  airball           1    1    0  100.0%
  back_rim         23    4   16   35.5%
  front_rim        36    7   24   33.4%
  other            13    4    6   57.3%
  side_rim_out     12    2    6   43.8%
By source (makes counted/makes, false makes/misses):
  commons:bandits_practice   47/87    16/18  
  commons:hardwick_game    26/43    13/31  
  commons:hardwick_game_HELDOUT_for_tracker_fix   31/51    12/28  
  github:aggie              5/5      1/1   
  github:artur              3/3      0/1   
  github:chonyy             4/4      0/4   
  github:kyle               0/1      2/0   
  github:lf                20/20     2/2   
  github:video_test_5      24/30     0/0   
Lost makes by exit reason:
  make lost: never armed                   46
  make lost: miss_below_without_inner      38
GATE A: FAIL
```

### L1
```
=== Gate A ===
Makes counted: 155/244 (63.5%)  [need >= 90%]
False makes: 17/85 labeled misses, + 23 spurious makes -> 95% upper bound on false-make rate 56.5%  [need 0 false makes]
By miss type (misses, false makes, resolved as MISS, 95% UB):
  airball           1    1    0  100.0%
  back_rim         23    4   17   35.5%
  front_rim        36    6   24   30.3%
  other            13    4    7   57.3%
  side_rim_out     12    2    6   43.8%
By source (makes counted/makes, false makes/misses):
  commons:bandits_practice   44/87    14/18  
  commons:hardwick_game    25/43    11/31  
  commons:hardwick_game_HELDOUT_for_tracker_fix   30/51    11/28  
  github:aggie              5/5      1/1   
  github:artur              3/3      0/1   
  github:chonyy             4/4      0/4   
  github:kyle               0/1      1/0   
  github:lf                20/20     2/2   
  github:video_test_5      24/30     0/0   
Lost makes by exit reason:
  make lost: never armed                   45
  make lost: miss_below_without_inner      44
GATE A: FAIL
```

### L2
```
=== Gate A ===
Makes counted: 148/244 (60.7%)  [need >= 90%]
False makes: 17/85 labeled misses, + 21 spurious makes -> 95% upper bound on false-make rate 54.2%  [need 0 false makes]
By miss type (misses, false makes, resolved as MISS, 95% UB):
  airball           1    1    0  100.0%
  back_rim         23    4   17   35.5%
  front_rim        36    6   24   30.3%
  other            13    4    7   57.3%
  side_rim_out     12    2    6   43.8%
By source (makes counted/makes, false makes/misses):
  commons:bandits_practice   44/87    14/18  
  commons:hardwick_game    24/43     9/31  
  commons:hardwick_game_HELDOUT_for_tracker_fix   29/51    11/28  
  github:aggie              3/5      1/1   
  github:artur              3/3      0/1   
  github:chonyy             4/4      0/4   
  github:kyle               0/1      1/0   
  github:lf                17/20     2/2   
  github:video_test_5      24/30     0/0   
Lost makes by exit reason:
  make lost: miss_below_without_inner      51
  make lost: never armed                   45
GATE A: FAIL
```

### L3
```
=== Gate A ===
Makes counted: 138/244 (56.6%)  [need >= 90%]
False makes: 11/85 labeled misses, + 18 spurious makes -> 95% upper bound on false-make rate 43.5%  [need 0 false makes]
By miss type (misses, false makes, resolved as MISS, 95% UB):
  airball           1    1    0  100.0%
  back_rim         23    4   17   35.5%
  front_rim        36    3   27   20.2%
  other            13    3    8   49.5%
  side_rim_out     12    0    8   22.1%
By source (makes counted/makes, false makes/misses):
  commons:bandits_practice   40/87    12/18  
  commons:hardwick_game    23/43     6/31  
  commons:hardwick_game_HELDOUT_for_tracker_fix   24/51     8/28  
  github:aggie              3/5      1/1   
  github:artur              3/3      0/1   
  github:chonyy             4/4      0/4   
  github:kyle               0/1      1/0   
  github:lf                17/20     1/2   
  github:video_test_5      24/30     0/0   
Lost makes by exit reason:
  make lost: miss_below_without_inner      61
  make lost: never armed                   45
GATE A: FAIL
```

### L4
```
=== Gate A ===
Makes counted: 118/244 (48.4%)  [need >= 90%]
False makes: 12/85 labeled misses, + 16 spurious makes -> 95% upper bound on false-make rate 42.3%  [need 0 false makes]
By miss type (misses, false makes, resolved as MISS, 95% UB):
  airball           1    1    0  100.0%
  back_rim         23    4   17   35.5%
  front_rim        36    4   26   23.6%
  other            13    3    8   49.5%
  side_rim_out     12    0    8   22.1%
By source (makes counted/makes, false makes/misses):
  commons:bandits_practice   29/87    10/18  
  commons:hardwick_game    19/43     8/31  
  commons:hardwick_game_HELDOUT_for_tracker_fix   20/51     8/28  
  github:aggie              3/5      0/1   
  github:artur              3/3      0/1   
  github:chonyy             4/4      0/4   
  github:kyle               0/1      1/0   
  github:lf                16/20     1/2   
  github:video_test_5      24/30     0/0   
Lost makes by exit reason:
  make lost: miss_below_without_inner      81
  make lost: never armed                   45
GATE A: FAIL
```

### H1
```
=== Gate A ===
Makes counted: 163/244 (66.8%)  [need >= 90%]
False makes: 2/85 labeled misses, + 6 spurious makes -> 95% upper bound on false-make rate 16.3%  [need 0 false makes]
By miss type (misses, false makes, resolved as MISS, 95% UB):
  airball           1    0    1   95.0%
  back_rim         23    1   18   19.0%
  front_rim        36    1   25   12.5%
  other            13    0    7   20.6%
  side_rim_out     12    0   10   22.1%
By source (makes counted/makes, false makes/misses):
  commons:bandits_practice   56/87     3/18  
  commons:hardwick_game    23/43     0/31  
  commons:hardwick_game_HELDOUT_for_tracker_fix   28/51     5/28  
  github:aggie              5/5      0/1   
  github:artur              3/3      0/1   
  github:chonyy             4/4      0/4   
  github:kyle               0/1      0/0   
  github:lf                18/20     0/2   
  github:video_test_5      26/30     0/0   
Lost makes by exit reason:
  make lost: never armed                   57
  make lost: miss_below_without_inner      10
  make lost: miss_occlusion_gap            7
  make lost: miss_rim_out_sideways         6
  make lost: miss_in_and_out               1
GATE A: FAIL
```

### H2
```
=== Gate A ===
Makes counted: 177/244 (72.5%)  [need >= 90%]
False makes: 3/85 labeled misses, + 16 spurious makes -> 95% upper bound on false-make rate 31.1%  [need 0 false makes]
By miss type (misses, false makes, resolved as MISS, 95% UB):
  airball           1    0    1   95.0%
  back_rim         23    2   18   24.9%
  front_rim        36    1   25   12.5%
  other            13    0    7   20.6%
  side_rim_out     12    0   10   22.1%
By source (makes counted/makes, false makes/misses):
  commons:bandits_practice   58/87     8/18  
  commons:hardwick_game    28/43     3/31  
  commons:hardwick_game_HELDOUT_for_tracker_fix   33/51     7/28  
  github:aggie              5/5      0/1   
  github:artur              3/3      0/1   
  github:chonyy             4/4      0/4   
  github:kyle               0/1      1/0   
  github:lf                19/20     0/2   
  github:video_test_5      27/30     0/0   
Lost makes by exit reason:
  make lost: never armed                   43
  make lost: miss_below_without_inner      10
  make lost: miss_occlusion_gap            7
  make lost: miss_rim_out_sideways         6
  make lost: miss_in_and_out               1
GATE A: FAIL
```

### H3
```
=== Gate A ===
Makes counted: 175/244 (71.7%)  [need >= 90%]
False makes: 4/85 labeled misses, + 15 spurious makes -> 95% upper bound on false-make rate 31.1%  [need 0 false makes]
By miss type (misses, false makes, resolved as MISS, 95% UB):
  airball           1    0    1   95.0%
  back_rim         23    2   18   24.9%
  front_rim        36    1   25   12.5%
  other            13    1    7   31.6%
  side_rim_out     12    0   10   22.1%
By source (makes counted/makes, false makes/misses):
  commons:bandits_practice   57/87     7/18  
  commons:hardwick_game    27/43     4/31  
  commons:hardwick_game_HELDOUT_for_tracker_fix   33/51     7/28  
  github:aggie              5/5      0/1   
  github:artur              3/3      0/1   
  github:chonyy             4/4      0/4   
  github:kyle               0/1      1/0   
  github:lf                19/20     0/2   
  github:video_test_5      27/30     0/0   
Lost makes by exit reason:
  make lost: never armed                   45
  make lost: miss_below_without_inner      10
  make lost: miss_occlusion_gap            7
  make lost: miss_rim_out_sideways         6
  make lost: miss_in_and_out               1
GATE A: FAIL
```

## False makes and spurious makes

| variant | clip | card | label frames | result frame | gap_frames | predicted_x (hoop widths) | miss type |
| --- | --- | --- | --- | --- | --- | --- | --- |
| L0 | aggie_NathanBBall.mov | aggie_NathanBBall_1 | 66-117 | 110 | 5 | 0.39 | back_rim |
| L1 | aggie_NathanBBall.mov | aggie_NathanBBall_1 | 66-117 | 110 | 5 | 0.39 | back_rim |
| L2 | aggie_NathanBBall.mov | aggie_NathanBBall_1 | 66-117 | 110 | 5 | 0.39 | back_rim |
| L3 | aggie_NathanBBall.mov | aggie_NathanBBall_1 | 66-117 | 110 | 5 | 0.39 | back_rim |
| H2 | kyle_test_video.mp4 | spurious | spurious | 210 | 14 | 0.12 | spurious |
| H3 | kyle_test_video.mp4 | spurious | spurious | 210 | 14 | 0.12 | spurious |
| L0 | kyle_test_video.mp4 | spurious | spurious | 210 | 14 | 0.12 | spurious |
| L1 | kyle_test_video.mp4 | spurious | spurious | 210 | 14 | 0.12 | spurious |
| L2 | kyle_test_video.mp4 | spurious | spurious | 210 | 14 | 0.12 | spurious |
| L3 | kyle_test_video.mp4 | spurious | spurious | 210 | 14 | 0.12 | spurious |
| L4 | kyle_test_video.mp4 | spurious | spurious | 210 | 14 | 0.12 | spurious |
| L0 | kyle_test_video.mp4 | spurious | spurious | 290 | 14 | 0.34 | spurious |
| L0 | lf_back.mp4 | lf_back_7 | 948-994 | 1000 | 9 | 0.48 | side_rim_out |
| L1 | lf_back.mp4 | lf_back_7 | 948-994 | 1000 | 9 | 0.48 | side_rim_out |
| L2 | lf_back.mp4 | lf_back_7 | 948-994 | 1000 | 9 | 0.48 | side_rim_out |
| L0 | lf_shot_detection.mp4 | lf_shot_detection_9 | 959-1015 | 1007 | 5 | 0.32 | back_rim |
| L1 | lf_shot_detection.mp4 | lf_shot_detection_9 | 959-1015 | 1007 | 5 | 0.32 | back_rim |
| L2 | lf_shot_detection.mp4 | lf_shot_detection_9 | 959-1015 | 1007 | 5 | 0.32 | back_rim |
| L3 | lf_shot_detection.mp4 | lf_shot_detection_9 | 959-1015 | 1007 | 5 | 0.32 | back_rim |
| L4 | lf_shot_detection.mp4 | lf_shot_detection_9 | 959-1015 | 1007 | 5 | 0.34 | back_rim |
| L0 | public/commons_bandits/bandits_practice_01.webm | spurious | spurious | 1449 | 9 | 0.37 | spurious |
| H2 | public/commons_bandits/bandits_practice_01.webm | spurious | spurious | 3293 | 1 | 0.10 | spurious |
| H3 | public/commons_bandits/bandits_practice_01.webm | spurious | spurious | 3293 | 1 | 0.11 | spurious |
| L0 | public/commons_bandits/bandits_practice_01.webm | spurious | spurious | 3293 | 1 | 0.10 | spurious |
| L1 | public/commons_bandits/bandits_practice_01.webm | spurious | spurious | 3293 | 1 | 0.10 | spurious |
| L2 | public/commons_bandits/bandits_practice_01.webm | spurious | spurious | 3293 | 1 | 0.10 | spurious |
| L3 | public/commons_bandits/bandits_practice_01.webm | spurious | spurious | 3293 | 1 | 0.10 | spurious |
| L4 | public/commons_bandits/bandits_practice_01.webm | spurious | spurious | 3293 | 1 | 0.11 | spurious |
| L4 | public/commons_bandits/bandits_practice_02.webm | 26 | 10730-10772 | 10780 | 6 | 0.33 | back_rim |
| H1 | public/commons_bandits/bandits_practice_02.webm | 28 | 11095-11167 | 11157 | 1 | -0.08 | back_rim |
| H2 | public/commons_bandits/bandits_practice_02.webm | 28 | 11095-11167 | 11157 | 1 | -0.08 | back_rim |
| H3 | public/commons_bandits/bandits_practice_02.webm | 28 | 11095-11167 | 11157 | 1 | 0.08 | back_rim |
| H2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 1799 | 14 | 0.12 | spurious |
| H3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 1799 | 14 | -0.03 | spurious |
| L0 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 1799 | 14 | 0.12 | spurious |
| L1 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 1799 | 14 | 0.12 | spurious |
| L2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 1799 | 14 | 0.12 | spurious |
| L3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 1799 | 14 | 0.12 | spurious |
| L4 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 1799 | 14 | -0.03 | spurious |
| L0 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 1840 | 0 | -0.31 | spurious |
| L0 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 2500 | 24 | 0.39 | spurious |
| L1 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 2500 | 24 | 0.39 | spurious |
| L2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 2500 | 24 | 0.39 | spurious |
| L3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 2500 | 24 | 0.39 | spurious |
| H1 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 2518 | 24 | 0.39 | spurious |
| H2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 2518 | 24 | 0.39 | spurious |
| L0 | public/commons_bandits/bandits_practice_03.webm | 16 | 2747-2771 | 2760 | 0 | -0.50 | side_rim_out |
| L1 | public/commons_bandits/bandits_practice_03.webm | 16 | 2747-2771 | 2760 | 1 | -0.49 | side_rim_out |
| L2 | public/commons_bandits/bandits_practice_03.webm | 16 | 2747-2771 | 2760 | 1 | -0.49 | side_rim_out |
| H2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 5427 | 3 | 0.00 | spurious |
| H3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 5427 | 3 | 0.00 | spurious |
| L0 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 5427 | 3 | 0.00 | spurious |
| L1 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 5427 | 3 | 0.00 | spurious |
| L2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 5427 | 3 | 0.00 | spurious |
| L3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 5427 | 3 | 0.00 | spurious |
| L4 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 5427 | 3 | 0.00 | spurious |
| H3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 9068 | 14 | -0.21 | spurious |
| L4 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 9068 | 14 | -0.21 | spurious |
| H2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 9313 | 10 | 0.30 | spurious |
| L0 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 9313 | 10 | 0.30 | spurious |
| L1 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 9313 | 10 | 0.30 | spurious |
| L2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 9313 | 10 | 0.30 | spurious |
| L3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 9313 | 10 | 0.30 | spurious |
| L0 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 9932 | 18 | 0.40 | spurious |
| L1 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 9932 | 18 | 0.40 | spurious |
| L2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 9932 | 18 | 0.40 | spurious |
| L3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 9932 | 18 | 0.40 | spurious |
| H2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 10280 | 7 | -0.30 | spurious |
| H3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 10280 | 7 | 0.11 | spurious |
| L0 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 10280 | 7 | -0.30 | spurious |
| L1 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 10280 | 7 | -0.30 | spurious |
| L2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 10280 | 7 | -0.30 | spurious |
| L3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 10280 | 7 | -0.30 | spurious |
| L4 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 10280 | 7 | 0.11 | spurious |
| H1 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 10473 |  |  | spurious |
| H2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 10473 |  |  | spurious |
| H3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 10473 |  |  | spurious |
| SV | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 10473 |  |  | spurious |
| L4 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 10519 | 2 | -0.23 | spurious |
| L0 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 11340 | 10 | -0.44 | spurious |
| L0 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 11699 | 10 | 0.07 | spurious |
| L1 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 11699 | 10 | 0.07 | spurious |
| L2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 11699 | 10 | 0.07 | spurious |
| L3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 11699 | 10 | 0.07 | spurious |
| L0 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 12376 | 10 | -0.46 | spurious |
| L1 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 12376 | 10 | -0.46 | spurious |
| L2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 12376 | 10 | -0.46 | spurious |
| L0 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 15374 | 11 | -0.23 | spurious |
| L1 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 15374 | 11 | -0.23 | spurious |
| L2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 15374 | 11 | -0.23 | spurious |
| L3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 15374 | 11 | -0.23 | spurious |
| L4 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 15374 | 11 | -0.25 | spurious |
| L0 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 15599 | 13 | -0.30 | spurious |
| L1 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 15599 | 13 | -0.30 | spurious |
| L2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 15599 | 13 | -0.30 | spurious |
| L3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 15599 | 13 | -0.30 | spurious |
| L4 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 15599 | 13 | -0.31 | spurious |
| L1 | public/commons_bandits/bandits_practice_03.webm | 82 | 16127-16181 | 16184 | 6 | 0.03 | other |
| L2 | public/commons_bandits/bandits_practice_03.webm | 82 | 16127-16181 | 16184 | 6 | 0.03 | other |
| L3 | public/commons_bandits/bandits_practice_03.webm | 82 | 16127-16181 | 16184 | 6 | 0.03 | other |
| L4 | public/commons_bandits/bandits_practice_03.webm | 82 | 16127-16181 | 16184 | 6 | 0.22 | other |
| L0 | public/commons_bandits/bandits_practice_03.webm | 82 | 16127-16181 | 16185 | 6 | 0.03 | other |
| L1 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 23040 | 13 | -0.02 | spurious |
| L2 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 23040 | 13 | -0.02 | spurious |
| L3 | public/commons_bandits/bandits_practice_03.webm | spurious | spurious | 23040 | 13 | -0.02 | spurious |
| H1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 35060 |  |  | spurious |
| H2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 35060 |  |  | spurious |
| H3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 35060 |  |  | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 35060 | 1 | 0.12 | spurious |
| L1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 35060 | 1 | 0.12 | spurious |
| L2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 35060 | 1 | 0.12 | spurious |
| L3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 35060 | 1 | 0.12 | spurious |
| L4 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 35060 | 1 | 0.12 | spurious |
| SV | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 35060 |  |  | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 39619 | 5 | 0.42 | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 94960 | 1 | -0.48 | spurious |
| L1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 94960 | 1 | -0.48 | spurious |
| L2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 94960 | 1 | -0.48 | spurious |
| L4 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 94960 | 1 | -0.33 | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 44 | 96298-96376 | 96372 | 9 | -0.34 | front_rim |
| L1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 44 | 96298-96376 | 96372 | 9 | -0.34 | front_rim |
| L2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 44 | 96298-96376 | 96372 | 9 | -0.34 | front_rim |
| L3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 44 | 96298-96376 | 96372 | 9 | -0.34 | front_rim |
| L4 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 44 | 96298-96376 | 96372 | 9 | -0.27 | front_rim |
| H1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 125017 |  |  | spurious |
| H2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 125017 |  |  | spurious |
| H3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 125017 |  |  | spurious |
| SV | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 125017 |  |  | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 125020 | 15 | 0.05 | spurious |
| L1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 125020 | 15 | 0.05 | spurious |
| L2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 125020 | 15 | 0.05 | spurious |
| L3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 125020 | 15 | 0.05 | spurious |
| L4 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 125020 | 15 | 0.21 | spurious |
| H2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 74 | 127281-127335 | 127333 | 9 | 0.17 | back_rim |
| H3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 74 | 127281-127335 | 127333 | 9 | -0.38 | back_rim |
| L0 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 74 | 127281-127335 | 127333 | 9 | 0.17 | back_rim |
| L1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 74 | 127281-127335 | 127333 | 9 | 0.17 | back_rim |
| L2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 74 | 127281-127335 | 127333 | 9 | 0.17 | back_rim |
| L3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 74 | 127281-127335 | 127333 | 9 | 0.17 | back_rim |
| L4 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 74 | 127281-127335 | 127333 | 9 | -0.38 | back_rim |
| L0 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 77 | 128926-128950 | 128958 | 11 | -0.06 | front_rim |
| L1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 77 | 128926-128950 | 128958 | 11 | -0.06 | front_rim |
| L2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 77 | 128926-128950 | 128958 | 11 | -0.06 | front_rim |
| L3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 77 | 128926-128950 | 128958 | 11 | -0.06 | front_rim |
| L4 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 77 | 128926-128950 | 128958 | 11 | -0.11 | front_rim |
| H1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 77 | 128926-128950 | 128991 | 11 | -0.06 | front_rim |
| H2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 77 | 128926-128950 | 128991 | 11 | -0.06 | front_rim |
| H3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 77 | 128926-128950 | 128991 | 11 | -0.11 | front_rim |
| L0 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 94 | 181487-181523 | 181540 | 15 | 0.35 | other |
| L1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 94 | 181487-181523 | 181540 | 15 | 0.35 | other |
| L2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 94 | 181487-181523 | 181540 | 15 | 0.35 | other |
| L3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 94 | 181487-181523 | 181540 | 15 | 0.35 | other |
| L0 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 104 | 197319-197361 | 197371 | 1 | 0.03 | front_rim |
| L1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 104 | 197319-197361 | 197371 | 1 | 0.03 | front_rim |
| L2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 104 | 197319-197361 | 197371 | 1 | 0.03 | front_rim |
| L3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 104 | 197319-197361 | 197371 | 1 | 0.03 | front_rim |
| L4 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 104 | 197319-197361 | 197371 | 1 | -0.01 | front_rim |
| H1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 201606 |  |  | spurious |
| H2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 201606 |  |  | spurious |
| H3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 201606 |  |  | spurious |
| SV | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 201606 |  |  | spurious |
| H1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 207518 |  |  | spurious |
| H2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 207518 |  |  | spurious |
| H3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 207518 |  |  | spurious |
| SV | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 207518 |  |  | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 154 | 260023-260053 | 260059 | 13 | -0.43 | front_rim |
| L1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 154 | 260023-260053 | 260059 | 13 | -0.43 | front_rim |
| L2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 154 | 260023-260053 | 260059 | 13 | -0.43 | front_rim |
| H2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 268207 | 12 | -0.21 | spurious |
| H3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 268207 | 12 | -0.21 | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 268207 | 12 | -0.21 | spurious |
| L1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 268207 | 12 | -0.21 | spurious |
| L2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 268207 | 12 | -0.21 | spurious |
| L3 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 268207 | 12 | -0.21 | spurious |
| L4 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | spurious | spurious | 268207 | 12 | -0.21 | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 166 | 268251-268293 | 268300 | 7 | 0.48 | front_rim |
| L1 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 166 | 268251-268293 | 268300 | 7 | 0.48 | front_rim |
| L2 | public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | 166 | 268251-268293 | 268300 | 7 | 0.48 | front_rim |
| H2 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 34160 | 15 | 0.09 | spurious |
| H3 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 34160 | 15 | -0.04 | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 34160 | 15 | 0.09 | spurious |
| L1 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 34160 | 15 | 0.09 | spurious |
| L2 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 34160 | 15 | 0.09 | spurious |
| L3 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 34160 | 15 | 0.09 | spurious |
| L4 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 34160 | 15 | -0.04 | spurious |
| H2 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 35049 | 11 | 0.30 | spurious |
| H3 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 35049 | 11 | 0.25 | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 35049 | 11 | 0.30 | spurious |
| L1 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 35049 | 11 | 0.30 | spurious |
| L2 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 35049 | 11 | 0.30 | spurious |
| L3 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 35049 | 11 | 0.30 | spurious |
| L4 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 35049 | 11 | 0.25 | spurious |
| H3 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 18 | 39311-39380 | 39367 | 21 | 0.17 | other |
| L0 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 18 | 39311-39380 | 39367 | 21 | 0.42 | other |
| L1 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 18 | 39311-39380 | 39367 | 21 | 0.42 | other |
| L2 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 18 | 39311-39380 | 39367 | 21 | 0.42 | other |
| L4 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 18 | 39311-39380 | 39367 | 21 | 0.17 | other |
| L0 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 39440 | 41 | -0.34 | spurious |
| L1 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 39440 | 43 | -0.35 | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 46 | 73233-73281 | 73279 | 3 | -0.06 | airball |
| L1 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 46 | 73233-73281 | 73279 | 11 | -0.05 | airball |
| L2 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 46 | 73233-73281 | 73279 | 11 | -0.05 | airball |
| L3 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 46 | 73233-73281 | 73279 | 11 | -0.05 | airball |
| L4 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 46 | 73233-73281 | 73279 | 11 | -0.06 | airball |
| L0 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 83 | 122514-122544 | 122542 | 17 | 0.45 | front_rim |
| L1 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 83 | 122514-122544 | 122542 | 17 | 0.45 | front_rim |
| L2 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 83 | 122514-122544 | 122542 | 17 | 0.45 | front_rim |
| L0 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 87 | 126786-126840 | 126842 | 16 | -0.28 | other |
| L1 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 87 | 126786-126840 | 126842 | 16 | -0.28 | other |
| L2 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 87 | 126786-126840 | 126842 | 16 | -0.28 | other |
| L3 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 87 | 126786-126840 | 126842 | 16 | -0.28 | other |
| L4 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 87 | 126786-126840 | 126842 | 16 | -0.28 | other |
| L0 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 164560 | 1 | 0.64 | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 172506 | 9 | -0.50 | spurious |
| L1 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 174214 | 21 | -0.53 | spurious |
| L2 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 174214 | 21 | -0.53 | spurious |
| H2 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 181560 | 21 | -0.19 | spurious |
| H3 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 181560 | 21 | -0.16 | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 181560 | 21 | -0.19 | spurious |
| L1 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 181560 | 21 | -0.19 | spurious |
| L2 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 181560 | 21 | -0.19 | spurious |
| L3 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 181560 | 21 | -0.19 | spurious |
| L4 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 181560 | 21 | -0.16 | spurious |
| L0 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 123 | 204700-204748 | 204750 | 15 | 0.22 | back_rim |
| L1 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 123 | 204700-204748 | 204750 | 15 | 0.22 | back_rim |
| L2 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 123 | 204700-204748 | 204750 | 15 | 0.22 | back_rim |
| L3 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 123 | 204700-204748 | 204750 | 15 | 0.22 | back_rim |
| L4 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 123 | 204700-204748 | 204750 | 15 | 0.30 | back_rim |
| L4 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 125 | 206428-206476 | 206440 | 10 | -0.20 | front_rim |
| L0 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | 125 | 206428-206476 | 206464 | 15 | 0.41 | front_rim |
| L0 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 269820 | 35 | 0.43 | spurious |
| L1 | public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | spurious | spurious | 269820 | 35 | 0.43 | spurious |

## Makes gained over SV

### L0 (34)

- video_test_5.mp4 card video_test_5_2 [211-242]: SV never armed

- lf_shot_detection.mp4 card lf_shot_detection_6 [600-640]: SV miss_rim_out_sideways

- lf_alan.mp4 card lf_alan_2 [624-653]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 27 [49693-49741]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 36 [60488-60524]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 51 [77888-77936]: SV miss_rim_out_sideways

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 52 [78875-78905]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 63 [94743-94791]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 70 [108544-108580]: SV miss_below_without_inner

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 103 [175691-175757]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 107 [183059-183119]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 177 [271517-271565]: SV never armed

- public/commons_bandits/bandits_practice_02.webm card 28 [11089-11107]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 23 [5058-5106]: SV miss_below_without_inner

- public/commons_bandits/bandits_practice_03.webm card 30 [6683-6713]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 37 [8511-8535]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 40 [8788-8836]: SV miss_below_without_inner

- public/commons_bandits/bandits_practice_03.webm card 44 [9397-9421]: SV miss_in_and_out

- public/commons_bandits/bandits_practice_03.webm card 67 [13544-13580]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 76 [15063-15093]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 82 [16031-16061]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 94 [23174-23192]: SV miss_rim_out_sideways

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 13 [43812-43860]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 18 [48977-49013]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 24 [56096-56126]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 50 [100940-101054]: SV miss_rim_out_sideways

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 69 [123447-123495]: SV miss_below_without_inner

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 86 [136300-136330]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 88 [137809-137839]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 106 [198780-198816]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 107 [199525-199567]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 129 [220801-220849]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 145 [249012-249048]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 165 [267923-267959]: SV never armed

### L1 (32)

- video_test_5.mp4 card video_test_5_2 [211-242]: SV never armed

- lf_shot_detection.mp4 card lf_shot_detection_6 [600-640]: SV miss_rim_out_sideways

- lf_alan.mp4 card lf_alan_2 [624-653]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 36 [60488-60524]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 51 [77888-77936]: SV miss_rim_out_sideways

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 52 [78875-78905]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 63 [94743-94791]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 70 [108544-108580]: SV miss_below_without_inner

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 103 [175691-175757]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 107 [183059-183119]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 177 [271517-271565]: SV never armed

- public/commons_bandits/bandits_practice_02.webm card 28 [11089-11107]: SV never armed

- public/commons_bandits/bandits_practice_01.webm card 5 [2722-2752]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 23 [5058-5106]: SV miss_below_without_inner

- public/commons_bandits/bandits_practice_03.webm card 30 [6683-6713]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 37 [8511-8535]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 40 [8788-8836]: SV miss_below_without_inner

- public/commons_bandits/bandits_practice_03.webm card 44 [9397-9421]: SV miss_in_and_out

- public/commons_bandits/bandits_practice_03.webm card 54 [10975-11011]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 67 [13544-13580]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 76 [15063-15093]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 13 [43812-43860]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 18 [48977-49013]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 24 [56096-56126]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 50 [100940-101054]: SV miss_rim_out_sideways

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 69 [123447-123495]: SV miss_below_without_inner

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 86 [136300-136330]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 88 [137809-137839]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 106 [198780-198816]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 107 [199525-199567]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 129 [220801-220849]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 165 [267923-267959]: SV never armed

### L2 (31)

- video_test_5.mp4 card video_test_5_2 [211-242]: SV never armed

- lf_shot_detection.mp4 card lf_shot_detection_6 [600-640]: SV miss_rim_out_sideways

- lf_alan.mp4 card lf_alan_2 [624-653]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 36 [60488-60524]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 51 [77888-77936]: SV miss_rim_out_sideways

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 52 [78875-78905]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 63 [94743-94791]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 70 [108544-108580]: SV miss_below_without_inner

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 103 [175691-175757]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 177 [271517-271565]: SV never armed

- public/commons_bandits/bandits_practice_02.webm card 28 [11089-11107]: SV never armed

- public/commons_bandits/bandits_practice_01.webm card 5 [2722-2752]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 23 [5058-5106]: SV miss_below_without_inner

- public/commons_bandits/bandits_practice_03.webm card 30 [6683-6713]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 37 [8511-8535]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 40 [8788-8836]: SV miss_below_without_inner

- public/commons_bandits/bandits_practice_03.webm card 44 [9397-9421]: SV miss_in_and_out

- public/commons_bandits/bandits_practice_03.webm card 54 [10975-11011]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 67 [13544-13580]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 76 [15063-15093]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 13 [43812-43860]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 18 [48977-49013]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 24 [56096-56126]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 50 [100940-101054]: SV miss_rim_out_sideways

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 69 [123447-123495]: SV miss_below_without_inner

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 86 [136300-136330]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 88 [137809-137839]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 106 [198780-198816]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 107 [199525-199567]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 129 [220801-220849]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 165 [267923-267959]: SV never armed

### L3 (24)

- video_test_5.mp4 card video_test_5_2 [211-242]: SV never armed

- lf_shot_detection.mp4 card lf_shot_detection_6 [600-640]: SV miss_rim_out_sideways

- lf_alan.mp4 card lf_alan_2 [624-653]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 36 [60488-60524]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 52 [78875-78905]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 63 [94743-94791]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 70 [108544-108580]: SV miss_below_without_inner

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 103 [175691-175757]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 177 [271517-271565]: SV never armed

- public/commons_bandits/bandits_practice_02.webm card 28 [11089-11107]: SV never armed

- public/commons_bandits/bandits_practice_01.webm card 5 [2722-2752]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 23 [5058-5106]: SV miss_below_without_inner

- public/commons_bandits/bandits_practice_03.webm card 30 [6683-6713]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 37 [8511-8535]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 44 [9397-9421]: SV miss_in_and_out

- public/commons_bandits/bandits_practice_03.webm card 67 [13544-13580]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 13 [43812-43860]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 18 [48977-49013]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 24 [56096-56126]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 69 [123447-123495]: SV miss_below_without_inner

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 86 [136300-136330]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 88 [137809-137839]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 106 [198780-198816]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 107 [199525-199567]: SV miss_occlusion_gap

### L4 (20)

- video_test_5.mp4 card video_test_5_2 [211-242]: SV never armed

- lf_shot_detection.mp4 card lf_shot_detection_6 [600-640]: SV miss_rim_out_sideways

- lf_alan.mp4 card lf_alan_2 [624-653]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 36 [60488-60524]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 52 [78875-78905]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 63 [94743-94791]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 70 [108544-108580]: SV miss_below_without_inner

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 103 [175691-175757]: SV never armed

- public/commons_bandits/bandits_practice_02.webm card 28 [11089-11107]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 30 [6683-6713]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 37 [8511-8535]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 67 [13544-13580]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 13 [43812-43860]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 18 [48977-49013]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 69 [123447-123495]: SV miss_below_without_inner

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 86 [136300-136330]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 88 [137809-137839]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 106 [198780-198816]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 107 [199525-199567]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 165 [267923-267959]: SV never armed

### H1 (5)

- public/commons_bandits/bandits_practice_03.webm card 30 [6683-6713]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 67 [13544-13580]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 79 [15614-15650]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 13 [43812-43860]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 107 [199525-199567]: SV miss_occlusion_gap

### H2 (19)

- video_test_5.mp4 card video_test_5_2 [211-242]: SV never armed

- lf_alan.mp4 card lf_alan_2 [624-653]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 36 [60488-60524]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 52 [78875-78905]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 63 [94743-94791]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 103 [175691-175757]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 177 [271517-271565]: SV never armed

- public/commons_bandits/bandits_practice_01.webm card 5 [2722-2752]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 30 [6683-6713]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 37 [8511-8535]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 67 [13544-13580]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 79 [15614-15650]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 13 [43812-43860]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 18 [48977-49013]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 24 [56096-56126]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 86 [136300-136330]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 88 [137809-137839]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 106 [198780-198816]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 107 [199525-199567]: SV miss_occlusion_gap

### H3 (17)

- video_test_5.mp4 card video_test_5_2 [211-242]: SV never armed

- lf_alan.mp4 card lf_alan_2 [624-653]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 36 [60488-60524]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 52 [78875-78905]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 63 [94743-94791]: SV never armed

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 103 [175691-175757]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 30 [6683-6713]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 37 [8511-8535]: SV never armed

- public/commons_bandits/bandits_practice_03.webm card 67 [13544-13580]: SV miss_occlusion_gap

- public/commons_bandits/bandits_practice_03.webm card 79 [15614-15650]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 13 [43812-43860]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 18 [48977-49013]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 86 [136300-136330]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 88 [137809-137839]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 106 [198780-198816]: SV never armed

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 107 [199525-199567]: SV miss_occlusion_gap

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 165 [267923-267959]: SV never armed


## Makes lost compared with SV

### L0 (32)

- video_test_5.mp4 card video_test_5_8 [1005-1047]

- video_test_5.mp4 card video_test_5_26 [2778-2811]

- video_test_5.mp4 card video_test_5_27 [2903-2931]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 3 [1858-1888]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 90 [129104-129164]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 93 [165365-165413]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 139 [237519-237585]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 168 [263955-263997]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 178 [274122-274182]

- public/commons_bandits/bandits_practice_02.webm card 5 [4739-4829]

- public/commons_bandits/bandits_practice_02.webm card 10 [6079-6103]

- public/commons_bandits/bandits_practice_02.webm card 12 [6428-6446]

- public/commons_bandits/bandits_practice_02.webm card 27 [10839-10881]

- public/commons_bandits/bandits_practice_02.webm card 30 [11355-11373]

- public/commons_bandits/bandits_practice_02.webm card 33 [11760-11778]

- public/commons_bandits/bandits_practice_02.webm card 33 [11796-11820]

- public/commons_bandits/bandits_practice_02.webm card 37 [12349-12367]

- public/commons_bandits/bandits_practice_02.webm card 38 [12571-12595]

- public/commons_bandits/bandits_practice_02.webm card 39 [12768-12798]

- public/commons_bandits/bandits_practice_03.webm card 51 [10400-10436]

- public/commons_bandits/bandits_practice_03.webm card 53 [10793-10835]

- public/commons_bandits/bandits_practice_03.webm card 57 [11716-11746]

- public/commons_bandits/bandits_practice_03.webm card 66 [13331-13355]

- public/commons_bandits/bandits_practice_03.webm card 78 [15387-15429]

- public/commons_bandits/bandits_practice_03.webm card 96 [23559-23601]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 30 [77281-77371]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 57 [106714-106786]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 121 [209807-209873]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 136 [234063-234105]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 147 [251629-251695]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 152 [259282-259312]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 178 [277907-277955]

### L1 (35)

- video_test_5.mp4 card video_test_5_8 [1005-1047]

- video_test_5.mp4 card video_test_5_26 [2778-2811]

- video_test_5.mp4 card video_test_5_27 [2903-2931]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 3 [1858-1888]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 90 [129104-129164]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 93 [165365-165413]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 139 [237519-237585]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 168 [263955-263997]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 178 [274122-274182]

- public/commons_bandits/bandits_practice_02.webm card 5 [4739-4829]

- public/commons_bandits/bandits_practice_02.webm card 10 [6079-6103]

- public/commons_bandits/bandits_practice_02.webm card 12 [6428-6446]

- public/commons_bandits/bandits_practice_02.webm card 19 [8755-8791]

- public/commons_bandits/bandits_practice_02.webm card 27 [10839-10881]

- public/commons_bandits/bandits_practice_02.webm card 30 [11355-11373]

- public/commons_bandits/bandits_practice_02.webm card 33 [11760-11778]

- public/commons_bandits/bandits_practice_02.webm card 37 [12349-12367]

- public/commons_bandits/bandits_practice_02.webm card 38 [12571-12595]

- public/commons_bandits/bandits_practice_02.webm card 39 [12768-12798]

- public/commons_bandits/bandits_practice_03.webm card 7 [1165-1195]

- public/commons_bandits/bandits_practice_03.webm card 14 [2423-2453]

- public/commons_bandits/bandits_practice_03.webm card 49 [10190-10222]

- public/commons_bandits/bandits_practice_03.webm card 51 [10400-10436]

- public/commons_bandits/bandits_practice_03.webm card 57 [11716-11746]

- public/commons_bandits/bandits_practice_03.webm card 64 [13088-13118]

- public/commons_bandits/bandits_practice_03.webm card 66 [13331-13355]

- public/commons_bandits/bandits_practice_03.webm card 78 [15387-15429]

- public/commons_bandits/bandits_practice_03.webm card 96 [23559-23601]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 30 [77281-77371]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 57 [106714-106786]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 121 [209807-209873]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 136 [234063-234105]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 147 [251629-251695]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 152 [259282-259312]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 178 [277907-277955]

### L2 (41)

- video_test_5.mp4 card video_test_5_8 [1005-1047]

- video_test_5.mp4 card video_test_5_26 [2778-2811]

- video_test_5.mp4 card video_test_5_27 [2903-2931]

- lf_shot_detection.mp4 card lf_shot_detection_4 [370-413]

- lf_shot_detection.mp4 card lf_shot_detection_7 [707-765]

- lf_shot_detection.mp4 card lf_shot_detection_10 [1081-1115]

- aggie_NathanBBall.mov card aggie_NathanBBall_3 [308-351]

- aggie_NathanBBall.mov card aggie_NathanBBall_5 [617-660]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 3 [1858-1888]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 90 [129104-129164]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 93 [165365-165413]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 139 [237519-237585]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 168 [263955-263997]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 178 [274122-274182]

- public/commons_bandits/bandits_practice_02.webm card 5 [4739-4829]

- public/commons_bandits/bandits_practice_02.webm card 10 [6079-6103]

- public/commons_bandits/bandits_practice_02.webm card 12 [6428-6446]

- public/commons_bandits/bandits_practice_02.webm card 19 [8755-8791]

- public/commons_bandits/bandits_practice_02.webm card 27 [10839-10881]

- public/commons_bandits/bandits_practice_02.webm card 30 [11355-11373]

- public/commons_bandits/bandits_practice_02.webm card 33 [11760-11778]

- public/commons_bandits/bandits_practice_02.webm card 37 [12349-12367]

- public/commons_bandits/bandits_practice_02.webm card 38 [12571-12595]

- public/commons_bandits/bandits_practice_02.webm card 39 [12768-12798]

- public/commons_bandits/bandits_practice_03.webm card 7 [1165-1195]

- public/commons_bandits/bandits_practice_03.webm card 14 [2423-2453]

- public/commons_bandits/bandits_practice_03.webm card 49 [10190-10222]

- public/commons_bandits/bandits_practice_03.webm card 51 [10400-10436]

- public/commons_bandits/bandits_practice_03.webm card 57 [11716-11746]

- public/commons_bandits/bandits_practice_03.webm card 64 [13088-13118]

- public/commons_bandits/bandits_practice_03.webm card 66 [13331-13355]

- public/commons_bandits/bandits_practice_03.webm card 78 [15387-15429]

- public/commons_bandits/bandits_practice_03.webm card 96 [23559-23601]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 6 [36913-36979]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 30 [77281-77371]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 57 [106714-106786]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 121 [209807-209873]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 136 [234063-234105]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 147 [251629-251695]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 152 [259282-259312]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 178 [277907-277955]

### L3 (44)

- video_test_5.mp4 card video_test_5_8 [1005-1047]

- video_test_5.mp4 card video_test_5_26 [2778-2811]

- video_test_5.mp4 card video_test_5_27 [2903-2931]

- lf_shot_detection.mp4 card lf_shot_detection_4 [370-413]

- lf_shot_detection.mp4 card lf_shot_detection_7 [707-765]

- lf_shot_detection.mp4 card lf_shot_detection_10 [1081-1115]

- aggie_NathanBBall.mov card aggie_NathanBBall_3 [308-351]

- aggie_NathanBBall.mov card aggie_NathanBBall_5 [617-660]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 3 [1858-1888]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 90 [129104-129164]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 93 [165365-165413]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 139 [237519-237585]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 168 [263955-263997]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 178 [274122-274182]

- public/commons_bandits/bandits_practice_02.webm card 5 [4739-4829]

- public/commons_bandits/bandits_practice_02.webm card 10 [6079-6103]

- public/commons_bandits/bandits_practice_02.webm card 12 [6428-6446]

- public/commons_bandits/bandits_practice_02.webm card 19 [8755-8791]

- public/commons_bandits/bandits_practice_02.webm card 27 [10839-10881]

- public/commons_bandits/bandits_practice_02.webm card 30 [11355-11373]

- public/commons_bandits/bandits_practice_02.webm card 33 [11760-11778]

- public/commons_bandits/bandits_practice_02.webm card 37 [12349-12367]

- public/commons_bandits/bandits_practice_02.webm card 38 [12571-12595]

- public/commons_bandits/bandits_practice_02.webm card 39 [12690-12726]

- public/commons_bandits/bandits_practice_02.webm card 39 [12768-12798]

- public/commons_bandits/bandits_practice_03.webm card 7 [1165-1195]

- public/commons_bandits/bandits_practice_03.webm card 14 [2423-2453]

- public/commons_bandits/bandits_practice_03.webm card 49 [10190-10222]

- public/commons_bandits/bandits_practice_03.webm card 51 [10400-10436]

- public/commons_bandits/bandits_practice_03.webm card 57 [11716-11746]

- public/commons_bandits/bandits_practice_03.webm card 64 [13088-13118]

- public/commons_bandits/bandits_practice_03.webm card 66 [13331-13355]

- public/commons_bandits/bandits_practice_03.webm card 78 [15387-15429]

- public/commons_bandits/bandits_practice_03.webm card 96 [23559-23601]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 6 [36913-36979]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 22 [54208-54274]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 30 [77281-77371]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 57 [106714-106786]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 121 [209807-209873]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 136 [234063-234105]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 147 [251629-251695]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 150 [258139-258175]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 152 [259282-259312]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 178 [277907-277955]

### L4 (60)

- video_test_5.mp4 card video_test_5_8 [1005-1047]

- video_test_5.mp4 card video_test_5_26 [2778-2811]

- video_test_5.mp4 card video_test_5_27 [2903-2931]

- lf_shot_detection.mp4 card lf_shot_detection_4 [370-413]

- lf_shot_detection.mp4 card lf_shot_detection_7 [707-765]

- lf_shot_detection.mp4 card lf_shot_detection_10 [1081-1115]

- lf_back.mp4 card lf_back_3 [359-389]

- aggie_NathanBBall.mov card aggie_NathanBBall_3 [308-351]

- aggie_NathanBBall.mov card aggie_NathanBBall_5 [617-660]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 3 [1858-1888]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 90 [129104-129164]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 93 [165365-165413]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 105 [179375-179423]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 139 [237519-237585]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 153 [252620-252692]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 165 [263145-263199]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 168 [263955-263997]

- public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm card 178 [274122-274182]

- public/commons_bandits/bandits_practice_02.webm card 5 [4739-4829]

- public/commons_bandits/bandits_practice_02.webm card 10 [6079-6103]

- public/commons_bandits/bandits_practice_02.webm card 12 [6428-6446]

- public/commons_bandits/bandits_practice_02.webm card 19 [8755-8791]

- public/commons_bandits/bandits_practice_02.webm card 27 [10839-10881]

- public/commons_bandits/bandits_practice_02.webm card 30 [11355-11373]

- public/commons_bandits/bandits_practice_02.webm card 33 [11760-11778]

- public/commons_bandits/bandits_practice_02.webm card 37 [12349-12367]

- public/commons_bandits/bandits_practice_02.webm card 38 [12571-12595]

- public/commons_bandits/bandits_practice_02.webm card 39 [12690-12726]

- public/commons_bandits/bandits_practice_02.webm card 39 [12768-12798]

- public/commons_bandits/bandits_practice_03.webm card 7 [1165-1195]

- public/commons_bandits/bandits_practice_03.webm card 14 [2423-2453]

- public/commons_bandits/bandits_practice_03.webm card 43 [9190-9202]

- public/commons_bandits/bandits_practice_03.webm card 45 [9490-9520]

- public/commons_bandits/bandits_practice_03.webm card 46 [9679-9709]

- public/commons_bandits/bandits_practice_03.webm card 47 [9872-9884]

- public/commons_bandits/bandits_practice_03.webm card 48 [9953-9983]

- public/commons_bandits/bandits_practice_03.webm card 49 [10190-10222]

- public/commons_bandits/bandits_practice_03.webm card 51 [10400-10436]

- public/commons_bandits/bandits_practice_03.webm card 55 [11347-11383]

- public/commons_bandits/bandits_practice_03.webm card 56 [11532-11568]

- public/commons_bandits/bandits_practice_03.webm card 57 [11716-11746]

- public/commons_bandits/bandits_practice_03.webm card 61 [12392-12428]

- public/commons_bandits/bandits_practice_03.webm card 64 [13088-13118]

- public/commons_bandits/bandits_practice_03.webm card 66 [13331-13355]

- public/commons_bandits/bandits_practice_03.webm card 78 [15387-15429]

- public/commons_bandits/bandits_practice_03.webm card 96 [23559-23601]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 6 [36913-36979]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 22 [54208-54274]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 27 [71896-71950]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 30 [77281-77371]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 34 [82472-82556]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 38 [92947-93013]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 57 [106714-106786]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 79 [131701-131737]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 121 [209807-209873]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 136 [234063-234105]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 147 [251629-251695]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 150 [258139-258175]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 152 [259282-259312]

- public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm card 178 [277907-277955]

### H1 (0)

_None._

### H2 (0)

_None._

### H3 (0)

_None._


## gap_too_long and arc_fallback counts (L2-L4)

| variant | gap_too_long | arc_fallback |
| --- | --- | --- |
| L2 | 20 | 0 |
| L3 | 20 | 0 |
| L4 | 21 | 38 |

## Hybrid change/add counts

| hybrid | changed | added |
| --- | --- | --- |
| H1 | 10 | 0 |
| H2 | 10 | 30 |
| H3 | 9 | 29 |

## Conclusion

1. Does the line method count makes that ShotVision loses because the ball is invisible at the rim?

Only just. L0 (the faithful line method) counts 160/244 makes against SV's 158/244, a net gain of 2. It gains 34 makes SV missed (list above) but loses 32 makes SV counted, so the net is +2 and the method is not a clean rescue.

2. What does it cost in false makes, and on which footage?

A lot. L0 scores 18/85 labeled misses as makes and adds 28 spurious makes (95% upper bound 63.4%), against SV's 0/85 and 5 spurious (12.0% upper bound, all spurious). The in-scope split cannot be assessed because labels.json has no camera_class / ball_count fields, so every clip is unclassified. On the legacy GitHub clips (fixed camera, single ball) the line method keeps 56/63 makes but introduces 5 false makes, where SV has 0.

3. Does the gap limit or the arc remove those false makes, and how many rescued makes does that cost?

No. The gap limit (L1 to L2) leaves false makes at 17 and drops makes 155 to 148 (7 lost). The arc (L3 to L4) raises false makes 11 to 12 and drops makes 138 to 118 (20 lost). Only the strict make zone removes false makes (L2 to L3: 17 to 11, 6 removed) and that costs 10 makes (148 to 138).

4. Is H1, H2 or H3 at 0 false makes in scope while counting more in-scope makes than SV?

No. There are no in-scope clips yet (all unclassified), so the in-scope comparison is empty (0/0 everywhere). On all clips no hybrid is at 0 false makes: H1 has 2 false makes and 6 spurious (against SV's 0 and 5), H2 has 3 and 16, H3 has 4 and 15. H1 rescues only 5 makes (163 vs 158) and still adds 2 false makes and 1 spurious make.

Overall the line-through-the-rim method, alone or as a rescue, does not add makes without adding false makes. It is not safe to adopt in Phase 1.

## Suggested next step

Re-run this experiment after PLAN_1's camera_class and ball_count fields land in labels.json, so the in-scope safety can actually be measured. On the current data the rescue is not free, so do not adopt the line method or H1-H3 into the pipeline. A more promising route for the invisible-at-rim makes is a rim-occlusion-aware crossing test inside ShotVision's own state machine or better ball detection, which needs owner agreement. This is a suggestion only, not implemented.

## Docs to add after merge

### docs/PROJECT_LOG.md entry

```
### 2026-11-06 — Line-through-the-rim method side by side with ShotVision (PLAN 2)

- Reimplemented the avishah3 "line through the rim" method from a description (no code copied) in `experiments/line_crossing_experiment.py`, with variants L0-L4 (all/best ball, gap limit, strict zone, arc) and hybrids H1-H3 (ShotVision plus a limited rescue). New tests in `tests/test_line_crossing.py`. 141 tests pass.
- Ran it against ShotVision on all 15 distinct labeled clips (244 makes, 85 misses) from cached detections.

| variant | makes | false makes / misses | spurious | 95% upper bound |
| --- | --- | --- | --- | --- |
| SV | 158/244 | 0/85 | 5 | 12.0% |
| L0 | 160/244 | 18/85 | 28 | 63.4% |
| L1 | 155/244 | 17/85 | 23 | 56.5% |
| L2 | 148/244 | 17/85 | 21 | 54.2% |
| L3 | 138/244 | 11/85 | 18 | 43.5% |
| L4 | 118/244 | 12/85 | 16 | 42.3% |
| H1 | 163/244 | 2/85 | 6 | 16.3% |
| H2 | 177/244 | 3/85 | 16 | 31.1% |
| H3 | 175/244 | 4/85 | 15 | 31.1% |

- Conclusion: the line method gains only 2 makes over SV (160 vs 158) but costs 18 false makes and 28 spurious. The gap limit and the arc do not remove those false makes. The most conservative hybrid H1 rescues 5 makes but adds 2 false makes and 1 spurious. No variant keeps 0 false makes, so the method is not safe to adopt.
```

### docs/tracking-research.md section

```
### 0d. Line-through-the-rim side by side (2026-11-06)

Reimplemented the avishah3 "line through the rim" method from a description (no code copied) and ran it side by side with ShotVision on cached detections. The line method gains only 2 makes over ShotVision (160 vs 158) but costs 18 false makes and 28 spurious (95% upper bound 63.4%). The gap limit and the arc do not remove those false makes; only the strict make zone does, and it costs 10 makes. The most conservative hybrid (H1) rescues 5 makes but adds 2 false makes and 1 spurious. No variant is at 0 false makes, so the line method is not a safe rescue for the invisible-at-rim makes. Full results: `experiments/results/line_crossing_2026-11-06.md`.
```

### CLAUDE.md next step (one line)

Proposed, needs agreement: keep ShotVision's scoring; do not adopt the line-through-the-rim method (it adds false makes); next measure the in-scope split after PLAN_1's camera_class / ball_count labels land.
