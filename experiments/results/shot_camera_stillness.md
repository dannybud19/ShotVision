## Table A: shots taken while the camera was still, by the clip's camera class

| camera class | makes still / total | misses still / total |
| --- | --- | --- |
| fixed/single | 54/60 | 8/8 |
| moving/single | 8/102 | 9/60 |
| moving/multi | 57/86 | 13/17 |
| **all** | 119/248 | 30/85 |

## Table B: still shots only, by clip

| clip | camera class | still makes counted / still makes | false makes / still misses |
| --- | --- | --- | --- |
| aggie_NathanBBall.mov | fixed/single | 4/4 | 0/1 |
| artur_vid29.mp4 | fixed/single | 2/2 | 0/1 |
| chonyy_one_score_one_miss.mp4 | fixed/single | 1/1 | 0/1 |
| chonyy_sample_video.mp4 | fixed/single | 1/1 | 0/0 |
| chonyy_two_score_three_miss.mp4 | fixed/single | 2/2 | 0/3 |
| kyle_test_video.mp4 | moving/single | 0/1 | 0/0 |
| lf_alan.mp4 | moving/single | 1/2 | 0/0 |
| lf_back.mp4 | fixed/single | 9/9 | 0/1 |
| lf_shot_detection.mp4 | fixed/single | 8/9 | 0/1 |
| public/commons_bandits/bandits_practice_02.webm | moving/multi | 26/28 | 0/6 |
| public/commons_bandits/bandits_practice_03.webm | moving/multi | 19/29 | 0/7 |
| public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | moving/single | 2/3 | 0/4 |
| public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | moving/single | 2/2 | 0/5 |
| video_test_5.mp4 | fixed/single | 22/26 | 0/0 |

## Table C: still misses by miss type

| miss type | still misses | false makes |
| --- | --- | --- |
| back_rim | 6 | 0 |
| front_rim | 13 | 0 |
| other | 5 | 0 |
| side_rim_out | 6 | 0 |
| **all** | 30 | 0 |

## Headline

Still-camera misses outside fixed/single clips: 22 (false makes: 0)
If counted in scope: in-scope misses would be 8 + 22 = 30

## Sanity checks

Totals: labelled makes 248 (scoreboard 248), labelled misses 85 (scoreboard 85).
Scoreboard cross-check: makes counted 162/248, labelled misses scored MAKE 0/85, spurious makes 1.
fixed/single shots that are not still: 6/68.

| fixed/single clip | shots not still / shots |
| --- | --- |
| aggie_NathanBBall.mov | 1/6 |
| artur_vid29.mp4 | 1/4 |
| video_test_5.mp4 | 4/30 |

## Still misses (all classes), for spot-checking

| clip | camera class | start | end | miss_type | card | ShotVision resolved |
| --- | --- | --- | --- | --- | --- | --- |
| aggie_NathanBBall.mov | fixed/single | 66 | 117 | back_rim | aggie_NathanBBall_1 | MISS @f105 (miss_rim_out_sideways) |
| artur_vid29.mp4 | fixed/single | 725 | 772 | front_rim | artur_vid29_5 | MISS @f760 (miss_below_without_inner) |
| chonyy_one_score_one_miss.mp4 | fixed/single | 50 | 86 | front_rim |  | MISS @f84 (miss_below_without_inner) |
| chonyy_two_score_three_miss.mp4 | fixed/single | 55 | 90 | front_rim |  | MISS @f86 (miss_below_without_inner) |
| chonyy_two_score_three_miss.mp4 | fixed/single | 150 | 195 | side_rim_out |  | MISS @f190 (miss_below_without_inner) |
| chonyy_two_score_three_miss.mp4 | fixed/single | 262 | 292 | front_rim |  | MISS @f288 (miss_below_without_inner) |
| lf_back.mp4 | fixed/single | 948 | 994 | side_rim_out | lf_back_7 | MISS @f995 (miss_below_without_inner) |
| lf_shot_detection.mp4 | fixed/single | 959 | 1015 | back_rim | lf_shot_detection_9 | MISS @f1004 (miss_rim_out_sideways) |
| public/commons_bandits/bandits_practice_02.webm | moving/multi | 4406 | 4436 | front_rim | 4 | MISS @f4445 (miss_below_without_inner) |
| public/commons_bandits/bandits_practice_02.webm | moving/multi | 6268 | 6310 | front_rim | 11 | MISS @f6307 (miss_below_without_inner) |
| public/commons_bandits/bandits_practice_02.webm | moving/multi | 6645 | 6705 | back_rim | 13 | MISS @f6702 (miss_below_without_inner) |
| public/commons_bandits/bandits_practice_02.webm | moving/multi | 8872 | 8914 | front_rim | 20 | MISS @f8907 (miss_below_without_inner) |
| public/commons_bandits/bandits_practice_02.webm | moving/multi | 10730 | 10772 | back_rim | 26 | MISS @f10766 (miss_below_without_inner) |
| public/commons_bandits/bandits_practice_02.webm | moving/multi | 11095 | 11167 | back_rim | 28 | MISS @f11157 (miss_occlusion_gap) |
| public/commons_bandits/bandits_practice_03.webm | moving/multi | 1374 | 1392 | other | 8 | MISS @f1389 (miss_below_without_inner) |
| public/commons_bandits/bandits_practice_03.webm | moving/multi | 2747 | 2771 | side_rim_out | 16 | MISS @f2770 (miss_below_without_inner) |
| public/commons_bandits/bandits_practice_03.webm | moving/multi | 3660 | 3696 | side_rim_out | 21 | MISS @f3717 (miss_below_without_inner) |
| public/commons_bandits/bandits_practice_03.webm | moving/multi | 6443 | 6485 | side_rim_out | 28 | MISS @f6491 (miss_below_without_inner) |
| public/commons_bandits/bandits_practice_03.webm | moving/multi | 12745 | 12787 | side_rim_out | 62 | MISS @f12778 (miss_below_without_inner) |
| public/commons_bandits/bandits_practice_03.webm | moving/multi | 13403 | 13427 | other | 66 | MISS @f13418 (miss_below_without_inner) |
| public/commons_bandits/bandits_practice_03.webm | moving/multi | 23405 | 23465 | other | 95 | NOT RESOLVED |
| public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | moving/single | 96298 | 96376 | front_rim | 44 | MISS @f96367 (miss_rim_out_sideways) |
| public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | moving/single | 181487 | 181523 | other | 94 | MISS @f181521 (miss_below_without_inner) |
| public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | moving/single | 265496 | 265550 | front_rim | 160 | MISS @f265553 (miss_below_without_inner) |
| public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | moving/single | 266842 | 266890 | front_rim | 162 | MISS @f266895 (miss_below_without_inner) |
| public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | moving/single | 46620 | 46680 | front_rim | 23 | NOT RESOLVED |
| public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | moving/single | 47684 | 47720 | back_rim | 24 | MISS @f47715 (miss_below_without_inner) |
| public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | moving/single | 59551 | 59599 | other | 35 | MISS @f59596 (miss_below_without_inner) |
| public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | moving/single | 259183 | 259255 | front_rim | 159 | MISS @f259254 (miss_below_without_inner) |
| public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | moving/single | 266484 | 266532 | front_rim | 171 | NOT RESOLVED |
