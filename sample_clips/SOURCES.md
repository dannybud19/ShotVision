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
