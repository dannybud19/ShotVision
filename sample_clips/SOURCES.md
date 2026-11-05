# Sample clip corpus — provenance

Third-party basketball clips used **locally** for detection tuning and
make/miss evaluation. Not committed to the repo (gitignored) and not
redistributed — downloaded from public GitHub repositories for development use
only. See each source repo for its own license before doing anything beyond
local experimentation.

| Local file | Source repo | Path in repo | Res |
|---|---|---|---|
| video_test_5.mp4 | avishah3/AI-Basketball-Shot-Detection-Tracker | video_test_5.mp4 | 960x540 |
| chonyy_sample_video.mp4 | chonyy/AI-basketball-analysis | static/uploads/sample_video.mp4 | 960x540 |
| chonyy_one_score_one_miss.mp4 | chonyy/AI-basketball-analysis | static/uploads/one_score_one_miss.mp4 | 960x540 |
| chonyy_two_score_two_miss.mp4 | chonyy/AI-basketball-analysis | static/uploads/two_score_two_miss.mp4 | 960x540 |
| chonyy_two_score_three_miss.mp4 | chonyy/AI-basketball-analysis | static/uploads/two_score_three_miss.mp4 | 960x540 |
| lf_shot_detection.mp4 | LittleFish-Coder/basketball-sports-ai | src/shot_detection.mp4 | 1280x720 |
| lf_side.mp4 | LittleFish-Coder/basketball-sports-ai | testing-datasets/side.mp4 | 1280x720 |
| lf_back.mp4 | LittleFish-Coder/basketball-sports-ai | testing-datasets/back.mp4 | 1280x720 |
| lf_alan.mp4 | LittleFish-Coder/basketball-sports-ai | testing-datasets/alan.mp4 | 640x360 |
| lf_ball_rim_detection.mp4 | LittleFish-Coder/basketball-sports-ai | src/ball_rim_detection.mp4 | 1280x720 |
| artur_vid29.mp4 | arturchichorro/bballvision | input_vids/vid29.mp4 | 720x1280 |
| kyle_test_video.mp4 | kylephan5/basketball-shot-tracker | videos/test_video.mp4 | 1920x1080 |
| kyle_validation_video.mp4 | kylephan5/basketball-shot-tracker | videos/validation_video.mp4 | 1080x1920 |
| aggie_NathanBBall.mov | AggieSportsAnalytics/ShotTracker | NathanBBall.mov | 852x480 |

Notes:
- The `chonyy_*` files encode make/miss counts in their names — reserved as
  implied ground truth for the later make/miss scoring-verification step.
- `lf_shot_detection.mp4`, `lf_side.mp4`, `lf_ball_rim_detection.mp4` share the
  same 1116-frame / 1280x720 source and are near-duplicates; treat as one.

## Openly licensed public footage (development data, added 2026-11-05)

Downloaded to `sample_clips/public/<source>/` (gitignored like the rest of
sample_clips/). Every file below has a license stated on its source page, all
allowing reuse with attribution. All of it is **development data** (`"split":
"dev"` in labels.json), never a held-out test set: it's someone else's camera,
and we may tune on it.

| Local file | Source page | License (as stated) | Attribution | Res / fps / length | Camera |
|---|---|---|---|---|---|
| public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | https://commons.wikimedia.org/wiki/File:Girls_Varsity_Basketball_v._Lyndon_-_February_4,_2026.webm | CC BY 4.0 | Hardwick Community Television (HCTV) | 1920x1080, 60 fps, 77 min | elevated sideline broadcast camera; pans and zooms with play; hoop small and near the frame edge; includes pregame warm-ups |
| public/commons_bandits/bandits_practice_01.webm | https://commons.wikimedia.org/wiki/File:ShotBug_Press_LIVE!_at_the_Langley_Event_Centre_for_the_Vancouver_Bandits_first_practice_of_the_year_01.webm | CC BY 3.0 | Shotbug Press | 1280x720, 60 fps, 66 s | handheld/tripod at floor level, behind or beside the hoop; some zoom |
| public/commons_bandits/bandits_practice_02.webm | https://commons.wikimedia.org/wiki/File:ShotBug_Press_LIVE!_at_the_Langley_Event_Centre_for_the_Vancouver_Bandits_first_practice_of_the_year_02.webm | CC BY 3.0 | Shotbug Press | 1280x720, 60 fps, 219 s | as above; part tight on the rim |
| public/commons_bandits/bandits_practice_03.webm | https://commons.wikimedia.org/wiki/File:ShotBug_Press_LIVE!_at_the_Langley_Event_Centre_for_the_Vancouver_Bandits_first_practice_of_the_year_03.webm | CC BY 3.0 | Shotbug Press | 1280x720, 60 fps, 397 s | floor level, mostly behind the shooter; pans |

Looked at and rejected (license fine, footage unusable for make/miss):
- Kunsan Basketball Tryouts 1023746/7/8 (public domain): edited b-roll, and the three files are the same video.
- Shoot Around with the Lady Huskies (public domain): handheld, hoop never in frame.
- archive.org basketball-shooting-machine (public domain mark): talking head with a hoop behind.
- Nabua street basketball (CC BY-SA 4.0): no hoop in view.

Skipped on license grounds: archive.org uploads such as "Full Game: … Michael Jordan …" carry a CC BY 4.0 tag, but they look like re-uploaded NBA broadcasts, so the uploader likely had no right to license them. Not used. YouTube was not used (terms of service), even for CC-licensed videos.
