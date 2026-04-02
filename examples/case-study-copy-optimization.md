# Case Study: Landing Page Copy Optimization

**Tool:** AutoResearch CLI (autoresearch-cli v0.2.5)
**Model:** gpt-4o-mini (OpenAI)
**Template:** copy-opt
**Experiments:** 15
**Duration:** ~3 minutes
**Estimated API cost:** ~$0.02

---

## Results

| Metric | Value |
|--------|-------|
| Baseline score | 58.8/100 |
| Best score | 82.5/100 |
| Improvement | **+40.3%** |
| Experiments run | 15 |
| Improvements kept | 4 |
| Crashed | 0 |

---

## Score Progression

```
Exp  1: 72.5 (+13.7) KEPT    — Added storytelling narrative
Exp  2: 77.5 (+18.7) KEPT    — Focused on emotional journey and empowerment
Exp  3: 81.2 (+22.4) KEPT    — Added vivid scenario showing team impact
Exp  4: 81.2  (0.0)  revert  — Similar scenario, no improvement
Exp  5: 81.2  (0.0)  revert  — Refined scenario, no improvement
...  (Exploit mode: 8 consecutive reverts — model stuck at local maximum)
Exp 11: 81.2  (0.0)  revert  — MODE SWITCH: Exploit -> Explore
Exp 12: 81.2  (0.0)  revert  — Narrative reframe, no improvement
Exp 13: 82.5 (+23.7) KEPT    — User-centric storytelling + team dynamics
Exp 14: 75.0  (-7.5) revert  — Too conversational, quality dropped
Exp 15: 81.2  (-1.3) revert  — Good but didn't beat best
```

**Key insight:** The explore/exploit strategy worked — after getting stuck at 81.2 for 8 experiments in exploit mode, the system switched back to explore mode and found a new improvement to 82.5.

---

## BEFORE (Original Copy) — Score: 58.8/100

```
TaskFlow Pro - Project Management Software

Manage your projects better with TaskFlow Pro. Our software helps teams
stay organized and get things done on time.

Features:
- Task management
- Team collaboration
- Time tracking
- Reporting

TaskFlow Pro is used by many companies around the world. It's easy to use
and has all the features you need.

Start your free trial today and see the difference.

Pricing starts at $12/month per user.
```

**AI Judge Assessment:** Generic, vague, no emotional appeal, no specificity, weak CTA.

---

## AFTER (Optimized Copy) — Score: 82.5/100

```
Unlock Your Team's True Potential with TaskFlow Pro

Imagine stepping into a world where project chaos transforms into seamless
collaboration. With TaskFlow Pro, you hold the key to this transformation.
Visualize your team not just managing tasks, but thriving together, where
every challenge turns into a shared victory and each milestone paves the
way for celebration.

Picture this: a lively workspace buzzing with ideas, where every team
member feels empowered and connected. As deadlines approach, your team
navigates through obstacles not just as colleagues, but as champions of a
common goal. This is the experience with TaskFlow Pro — it's more than
just software; it's your partner in crafting success stories together.

**What Makes TaskFlow Pro Your Best Choice?**
- **Seamless Team Collaboration:** Foster an atmosphere where real-time
  feedback and communication empower every voice.
- **Dynamic Task Management:** Tailor your project workflow with ease.
  Assign, schedule, and prioritize tasks intuitively.
- **Data-Driven Insights:** Leverage powerful analytics to gain a clear
  understanding of productivity trends.
- **Effortless Time Tracking:** Turn time management into a breeze.
  Automatically log hours, allowing your team to focus on goals.

Join countless teams who have experienced the remarkable shift in their
project management approach. With TaskFlow Pro, it's time to stop working
hard and start working smart.

Are you ready to embark on this journey of transformation? Begin your free
trial today and feel the renewed energy that TaskFlow Pro brings.

**Affordable Pricing for Empowered Teams:**
Invest in your team's evolution at just $12/month per user.
```

---

## What the AI Changed (4 Kept Improvements)

1. **Experiment 1 (58.8 -> 72.5):** Replaced feature-list format with storytelling narrative
2. **Experiment 2 (72.5 -> 77.5):** Added emotional journey and user empowerment framing
3. **Experiment 3 (77.5 -> 81.2):** Added vivid scenario showing positive team impact
4. **Experiment 13 (81.2 -> 82.5):** Reframed around user-centric storytelling and team dynamics

---

## Smart Loop Features Demonstrated

- **Explore mode** (experiments 1-2): Bold rewrites of the copy structure
- **Exploit mode** (experiments 3-11): Refinement of the winning approach
- **Auto mode switch** (experiment 11): System detected 8 consecutive failures and switched back to explore
- **Second breakthrough** (experiment 13): Explore mode found a new improvement after exploitation plateau

---

## CLI Commands Used

```bash
# Setup
pip install autoresearch-cli
ars init --template copy-opt
export OPENAI_API_KEY=sk-...

# Run
ars run --max-experiments 15 --provider openai --model gpt-4o-mini

# Review
ars results          # Full experiment table
ars diff             # Before/after comparison
ars apply --yes      # Write best version to file
```

---

## Cost Breakdown

- 15 LLM proposals (gpt-4o-mini): ~$0.01
- 15 LLM judge evaluations (gpt-4o-mini): ~$0.01
- **Total: ~$0.02**
- Time: ~3 minutes

---

*This case study was generated using autoresearch-cli v0.2.5 on April 2, 2026.*
