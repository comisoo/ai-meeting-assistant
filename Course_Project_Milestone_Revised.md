# AI Meeting Minutes Assistant

## Course Project Milestone

SUN Hanyi 21270270 hsunbk@connect.ust.hk  
GAO Yuan 21252838 ygaodk@connect.ust.hk  
LI Zonghan 21270244 zlilr@connect.ust.hk

Group 9  
MAIE 5531  
March 20, 2025

## Project Overview

The AI Meeting Minutes Assistant is an intelligent meeting-understanding system that converts raw meeting audio or transcripts into structured, decision-oriented meeting minutes. Rather than only generating a generic summary, the system is designed as a multi-stage AI pipeline that performs transcription, transcript normalization, meeting summarization, and action-item extraction in sequence. The project targets enterprise and educational scenarios in which conversations are often noisy, semi-structured, and code-switched between English and Chinese.

The key innovation of this project lies in its focus on realistic multilingual meeting environments. In practice, many off-the-shelf meeting summarization tools underperform when speakers switch languages, use domain-specific jargon, or speak with localized accents. Our system addresses this challenge by combining high-speed speech recognition with LLM-based transcript cleaning and template-aware downstream reasoning. In addition, the system supports customizable meeting templates, enabling it to produce outputs tailored to stand-ups, brainstorming sessions, client discussions, and general meetings.

## Completed Work

Our team has moved beyond the proposal stage and built a working end-to-end prototype with a clear separation between frontend, backend, and AI orchestration logic.

On the frontend side, we implemented a lightweight but polished single-page interface using Vanilla HTML, CSS, and JavaScript. The interface supports drag-and-drop file upload, template selection, dynamic processing-state visualization, and structured result rendering. Compared with a heavier framework-based implementation, this design keeps the system responsive and easy to maintain while still providing a modern user experience.

On the backend side, we built a FastAPI service that accepts uploaded meeting audio or transcript files, validates the input format, performs temporary file handling, and returns structured inference results through a clean REST API. This backend currently works in a stateless mode, which simplifies deployment and reduces storage overhead during early-stage experimentation.

Most importantly, we implemented the core AI workflow using LangGraph. Instead of treating the task as a single prompt to a general-purpose model, we decomposed the problem into multiple specialized stages:

1. A transcription stage converts audio into raw text using `whisper-large-v3` through Groq.
2. A transcript-cleaning stage improves readability and repairs code-switching artifacts.
3. A summarization stage generates structured meeting minutes according to the selected meeting template.
4. An action-item extraction stage converts discussion content into machine-readable task objects with assignees and deadlines.

This modular design increases interpretability, allows targeted prompt optimization for each stage, and makes the system easier to extend with future components such as speaker diarization, quality scoring, or retrieval of historical meetings.

We also migrated our inference stack from OpenAI-based calls to Groq-based inference. This architectural adjustment significantly reduced end-to-end latency and made multi-step LLM orchestration more feasible in an interactive application setting. From a systems perspective, this migration was important because low latency is essential when multiple AI calls must be chained together in one user request.

## Technical Contributions and Project Value

The technical value of this project is not only in using large models, but in engineering them into a practical workflow for a challenging real-world setting.

First, the project demonstrates **multi-agent orchestration** rather than simple one-shot prompting. LangGraph is used to represent the meeting-processing pipeline as an explicit computation graph with typed state transitions. This provides a cleaner abstraction for sequential reasoning, debugging, and future extension.

Second, the project focuses on **code-switched multilingual meeting intelligence**, which is substantially harder than plain English summarization. Our design explicitly separates raw ASR output from downstream reasoning, allowing a dedicated cleaning stage to normalize bilingual transcripts before they are summarized or mined for action items.

Third, the project includes **structured information extraction** instead of only free-form text generation. By using schema-guided output for action items, the system produces data that can later be integrated into project management tools, searchable archives, or analytics dashboards.

Fourth, the project reflects **practical systems engineering tradeoffs**. We made an explicit design shift from a heavier frontend stack to a lightweight interface, and from a slower inference provider to a lower-latency one, prioritizing usability and responsiveness without sacrificing core functionality.

Finally, the architecture is intentionally **extensible**. Because the system is modular, it can be upgraded incrementally with speaker-aware transcription, persistent storage, evaluation tooling, or richer meeting-specific templates.

## Application Screenshots

Below are the screenshots demonstrating the current prototype:

- **Screenshot 1: Initial UI and File Upload.** The main dashboard presents the upload area, template selector, and a polished visual interface for user interaction.
- **Screenshot 2: Multi-Stage Processing Workflow.** The frontend displays step-by-step execution status while the backend pipeline performs transcription, cleaning, summarization, and extraction.
- **Screenshot 3: Final Structured Output.** The system returns a formatted summary, extracted action items, and the cleaned transcript for inspection.

## Technical Approach

The system follows a decoupled client-server architecture.

- **Frontend:** A custom interface built with Vanilla HTML, CSS, and JavaScript handles file upload, template selection, and result presentation.
- **Backend API:** FastAPI manages file ingestion, request validation, temporary storage, and communication with external AI services.
- **Speech-to-Text Layer:** Groq `whisper-large-v3` is used for multilingual transcription of uploaded meeting audio.
- **LLM Reasoning Layer:** Groq `llama-3.3-70b-versatile` powers transcript cleaning, summarization, and action-item extraction.
- **Workflow Orchestration:** LangGraph defines the sequential execution of the pipeline and manages intermediate state passing between stages.
- **Structured Output Layer:** Pydantic schemas enforce a consistent format for extracted action items, improving downstream usability and reducing parsing ambiguity.

This design allows the system to separate concerns cleanly: ASR handles low-level audio understanding, LLM nodes handle semantic reasoning, and the workflow layer coordinates execution in a maintainable way.

## Major Challenges and Solutions

### Challenge 1: High Latency in Multi-Step AI Processing

An end-to-end meeting assistant requires several dependent model calls. Early versions of the pipeline suffered from high response times, making the user experience less practical.

**Solution:** We migrated the inference stack to Groq, whose lower-latency execution significantly improved responsiveness. This change made multi-stage orchestration viable for an interactive application.

### Challenge 2: Code-Switched and Noisy Meeting Transcripts

Meetings often contain mixed English-Chinese speech, incomplete utterances, and ASR artifacts. Directly summarizing this raw output leads to lower-quality meeting minutes.

**Solution:** We introduced a dedicated transcript-cleaning stage before summarization. This allows the system to normalize code-switching, repair obvious recognition errors, and pass cleaner context into downstream reasoning modules.

### Challenge 3: Converting Unstructured Discussion into Actionable Data

A major challenge is not just summarizing the discussion, but identifying concrete tasks, owners, and deadlines from informal conversation.

**Solution:** We used schema-constrained extraction with Pydantic to produce structured action-item outputs. This makes the output more reliable and easier to integrate with other systems later.

## Remaining Work and Areas for Improvement

Although the prototype is functional, several high-value components remain to be completed. These improvements will strengthen both the technical rigor and the real-world usefulness of the final project.

### 1. Improve Transcription Robustness for Long or Complex Audio

The current prototype already performs transcription, but its reliability can still be improved for long meetings, noisy recordings, and overlapping speech. A more advanced version should add audio chunking, timestamp-level processing, and stronger handling of partial or incomplete transcription.

### 2. Add Speaker Diarization

At present, the system summarizes the full transcript as a whole and does not reliably distinguish who said what. Speaker diarization would significantly improve the practical value of the output by enabling speaker-attributed notes, clearer responsibility tracking, and more accurate action-item assignment.

### 3. Build a Stronger Evaluation Framework

The current prototype demonstrates functionality, but the final project should also include measurable evaluation. We plan to assess:

- transcription quality on bilingual/code-switched audio,
- summary quality and completeness,
- action-item extraction precision and recall,
- latency under realistic usage conditions.

This will help move the project from a working demo toward a technically justified system.

### 4. Decide on Persistence and Historical Retrieval

The current architecture is stateless. This is suitable for fast prototyping, but persistent storage would enable meeting history, searchable archives, repeated access to past summaries, and longitudinal task tracking. We need to decide whether to remain stateless for simplicity or add a lightweight database such as SQLite/PostgreSQL for better product completeness.

### 5. Expand Template Intelligence

Our current system already supports multiple meeting templates, but these can be made more sophisticated. Future work includes richer template-specific prompts, domain-specific terminology support, and output formats tailored to different use cases such as academic meetings, project stand-ups, stakeholder reviews, or brainstorming sessions.

### 6. Strengthen Testing, Reliability, and Deployment

The final version should include unit tests, API-level integration tests, and broader user testing. In addition, we still need to finalize deployment, production configuration, and monitoring. This includes handling error cases more gracefully, validating unsupported files more clearly, and ensuring stable public access for demonstration.

## Next Steps and Estimated Timeline

### Week 1 (Apr 16 - Apr 22)

- Resolve dependency and environment issues in the backend.
- Refactor the transcription pipeline to support richer timestamps and more robust handling of longer audio files.
- Finalize the persistence decision: remain stateless or introduce a lightweight database.

### Week 2 (Apr 23 - Apr 29)

- Implement a first version of speaker diarization or speaker-aware transcript alignment.
- Add backend unit tests and API integration tests.
- Improve validation and error handling for file upload and processing failures.

### Week 3 (Apr 30 - May 6)

- Refine prompt design for template-based summarization and action-item extraction.
- Expand template coverage for different meeting scenarios.
- Introduce basic evaluation metrics for transcription and extraction quality.

### Week 4 (May 7 - May 13)

- Deploy the frontend and backend to public hosting.
- Conduct end-to-end user testing and performance checks.
- Polish the interface and prepare the final presentation with a clear technical demonstration and evaluation summary.

## Conclusion

At the milestone stage, our project has already achieved a functional prototype with a clear AI workflow, responsive frontend, and practical meeting-understanding capabilities. More importantly, the project is technically meaningful because it combines speech recognition, multilingual transcript normalization, LLM orchestration, structured extraction, and system-level latency optimization into a single application. The remaining work is not about building from scratch, but about strengthening robustness, evaluation, and speaker-aware intelligence so that the final system is both impressive as a demo and defensible as an engineering project.
