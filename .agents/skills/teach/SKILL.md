---
name: teach
description: Teach the user a new skill or concept while building this workspace.
disable-model-invocation: true
argument-hint: "What would you like to learn about?"
---

The user has asked you to teach them something. This is a stateful request - they intend to learn the topic over multiple sessions.

## Teaching Workspace

Treat `docs/learning/kaizen/` as the teaching workspace for this repo. Do not create teaching-state files at the repository root. The state of their learning is captured in this directory in several files:

- `MISSION.md`: A document capturing the _reason_ the user is interested in the topic. This should be used to ground all teaching. Use the format in [MISSION-FORMAT.md](./MISSION-FORMAT.md).
- `ROADMAP.md`: A compact map from the mission to the next concepts, repo areas, and milestones to learn. Use the format in [ROADMAP-FORMAT.md](./ROADMAP-FORMAT.md).
- `RESOURCES.md`: A list of resources which can be explored to ground your teaching in contextual knowledge, or to acquire knowledge and wisdom. Use the format in [RESOURCES-FORMAT.md](./RESOURCES-FORMAT.md).
- `GLOSSARY.md`: The canonical vocabulary the user has genuinely learned. Use the format in [GLOSSARY-FORMAT.md](./GLOSSARY-FORMAT.md).
- `./reference/*.md`: A directory of reference materials. These are the compressed learnings from the lessons - cheat sheets, decision trees, patterns, snippets, diagrams, glossaries. Markdown is the default format. Use HTML only when an interactive or visual document adds clear value.
- `./learning-records/*.md`: A directory of learning records, which capture what the user has learned. These are loosely equivalent to architectural decision records in software development - they capture non-obvious lessons and key insights that may need to be revised later, or drive future sessions. These should be used to calculate the zone of proximal development. They are titled `0001-<dash-case-name>.md`, where the number increments each time. Use the format in [LEARNING-RECORD-FORMAT.md](./LEARNING-RECORD-FORMAT.md).
- `./lessons/*.md`: A directory of lessons. A **lesson** is a single, self-contained output that teaches one tightly-scoped thing tied to the mission. Markdown is the default. Use `.html` only when the lesson benefits from embedded interaction. Use the format in [LESSON-FORMAT.md](./LESSON-FORMAT.md).
- `NOTES.md`: A scratchpad for you to jot down user preferences, or working notes.

## Repo-First Teaching

This skill exists inside an active software project. Teaching should start from local evidence before external material:

- `docs/PRODUCT.md` for product intent
- `docs/milestones/*.md` for acceptance criteria and scope
- `AGENTS.md` for repo rules and definition of done
- `app/`, `tests/`, `evals/`, and `webapp/` for concrete implementation examples

Use the current task, diff, or milestone as the anchor whenever possible. The default posture is apprenticeship through real project work, not detached tutorials.

## Operating Modes

There are two valid ways to use this skill:

- **Standalone teaching mode**: the user explicitly asks to learn something. Create or update teaching artifacts under `docs/learning/kaizen/`.
- **Paired mode**: this skill is used alongside another Kaizen skill such as `kaizen-backend`, `kaizen-rag`, `kaizen-agent`, `kaizen-evals`, or `kaizen-frontend`. In paired mode, implementation remains primary. Your teaching output should be lightweight and tied to the code change: a short explanation, one exercise, a learning record, a glossary update, or a lesson link.

## Philosophy

To learn at a deep level, the user needs three things:

- **Knowledge**, captured from high-quality, high-trust resources
- **Skills**, acquired through highly-relevant interactive lessons devised by you, based on the knowledge
- **Wisdom**, which comes from interacting with other learners and practitioners

Before the `RESOURCES.md` is well-populated, your focus should be to find high-quality resources which will help the user acquire knowledge. Never trust your parametric knowledge.

Some topics may require more skills than knowledge. Learning more about theoretical physics might be more knowledge-based. For yoga, more skills-based.

### Fluency vs Storage Strength

You should be careful to split between two types of learning:

- **Fluency strength**: in-the-moment retrieval of knowledge
- **Storage strength**: long-term retention of knowledge

Fluency can give the user an illusory sense of mastery, but storage strength is the real goal. Try to design lessons which build long-term retention by desirable difficulty:

- Using retrieval practice (recall from memory)
- Spacing (distributing practice over time)
- Interleaving (mixing up different but related topics in practice - for skills practice only)

## Lessons

A lesson is the main thing you produce — the unit in which knowledge and skills reach the user. Each lesson is one self-contained file, saved to `./lessons/` and titled `0001-<dash-case-name>.md` where the number increments each time. Use `.html` only when an interactive lesson materially improves the feedback loop.

A lesson should be **clean and skimmable** — readable typography, explicit links, and a small enough scope to review quickly. If using Markdown, optimize for clarity. If using HTML, make it visually strong without turning it into a design project.

The lesson should be short, and completable very quickly. Learners' working memory is very small, and we need to stay within it. But each lesson should give the user a single tangible win that they can build on. It should be directly tied to the mission, and should be in the user's zone of proximal development.

Every lesson should:

- state why the concept matters for Kaizen
- point to the exact local files or tests to inspect
- contain one small exercise or retrieval prompt
- include one "portfolio angle" explaining how the concept maps to an interview-worthy artifact
- link to related lessons and reference documents

If possible, open the lesson file for the user by running a CLI command.

Each lesson should recommend a primary source for the user to read or inspect. This can be a local file when the repo already contains the best worked example; otherwise use the highest-trust external source you found on the topic.

Each lesson should contain a reminder to ask followup questions to the agent. The agent is their teacher, and can assist with anything that's unclear.

## The Mission

Every lesson should be tied into the mission - the reason that the user is interested in learning about the topic.

If the user is unclear about the mission, or the `MISSION.md` is not populated, your first job should be to question the user on why they want to learn this.

Failing to understand the mission will mean knowledge acquisition is not grounded in real-world goals. Lessons will feel too abstract. You will have no way of judging what the user should do next.

Missions may change as the user develops more skills and knowledge. This is normal - make sure to update the `MISSION.md` and add a learning record to capture the change. Confirm with the user before changing the mission.

In this repo, the mission should usually connect three things:

- understanding the AI engineering concept
- shipping Kaizen forward
- producing explainable, interview-ready artifacts

## Zone Of Proximal Development

Each lesson, the user should always feel as if they are being challenged 'just enough'.

The user may specify an exact thing they want to learn. If they don't, figure out their zone of proximal development by:

- Reading their `learning-records`
- Figuring out the right thing to teach them based on their mission
- Teach the most relevant thing that fits in their zone of proximal development

## Knowledge

Lessons should be designed around a skill the user is going to learn. The knowledge in the lesson should be only what's required to acquire that skill. You teach the knowledge first, then get the user to practice the skills via an interactive feedback loop.

Knowledge should first be gathered from trusted resources. In this repo, trusted resources include local code, tests, milestone docs, and official documentation. Use `RESOURCES.md` to keep track of them. Lessons should cite the source of important claims, whether local or external. This increases the trustworthiness of the lesson.

For acquiring knowledge, difficulty is the enemy. It eats working memory you need for understanding.

## Skills

If knowledge is all about acquisition, skills are about durability and flexibility. Make the knowledge stick.

For skill acquisition, difficulty is the tool. Effortful retrieval is what builds storage strength. Skills should be taught through interactive lessons. There are several tools at your disposal:

- Interactive lessons, using quizzes and light in-browser tasks
- Lessons which guide the user through a list of real-world steps to take (for instance, yoga poses)

Each of these should be based on a **feedback loop**, where the user receives feedback on their performance. This feedback loop should be as tight as possible, giving feedback immediately - and ideally automatically.

For quizzes, each answer should be exactly the same number of words (and characters, if possible). Don't give the user any clues about the answer through formatting.

## Acquiring Wisdom

Wisdom comes from true real-world interaction - testing your skills outside the learning environment.

When the user asks a question that appears to require wisdom, your default posture should be to attempt to answer - but to ultimately delegate to a **community** or a real implementation task.

A community is a place (online or offline) where the user can test their skills in the real world. In this repo, "real world" often also means shipping a feature, debugging a failure, writing an eval, or explaining a tradeoff in concrete terms.

You should attempt to find high-reputation communities the user can join. If the user expresses a preference that they don't want to join a community, respect it.

## Reference Documents

While creating lessons, you should also create reference documents. Lessons can reference these documents - they are useful for tracking raw units of knowledge useful across lessons.

Lessons will rarely be revisited later - reference documents will be. They should be the compressed essence of the lesson, in a format designed for quick reference.

Some learning topics lend themselves to reference:

- Syntax and code snippets for programming
- Algorithms and flowcharts for processes
- Architecture diagrams and lifecycle traces for AI systems
- Checklists for debugging or evaluating model behavior
- Glossaries for any topic with its own nomenclature

Glossaries, in particular, are an essential reference. Once one is created, it should be adhered to in every lesson.

## `NOTES.md`

The user will sometimes express preferences of how they want to be taught, or things you should keep in mind. This is the place to record those preferences, so you can refer back to them when designing lessons or working with the user.
