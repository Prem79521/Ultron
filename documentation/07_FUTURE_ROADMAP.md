# ULTRON Future Roadmap

This document outlines the planned future development phases of the ULTRON Cognitive OS.

---

## Phase 5 — Local LLM Integration
- **Objective**: Replace placeholder mock engines with offline local LLM execution.
- **Milestones**:
  - Integrate Llama.cpp or ONNX runtime backend loaders.
  - Implement streaming token outputs connected to the event bus.
  - Setup model quantization presets (e.g. 4-bit Llama-3-8B) to run efficiently on consumer GPUs.

---

## Phase 6 — Vision Capabilities
- **Objective**: Connect active vision analysis tools.
- **Milestones**:
  - Hook OpenCV camera captures.
  - Set up offline image classification (e.g. MobileNet or YOLO models) for object detection.
  - Support screenshot-to-text context lookups.

---

## Phase 7 — Plugin Marketplace
- **Objective**: Standardize extension registries.
- **Milestones**:
  - Implement a web-based schema for sharing custom manifest definitions.
  - Support automatic sandboxed execution for third-party extensions.
  - Build UI package manager dashboard inside the Tools page.

---

## Phase 8 — Autonomous Agents & Scheduling
- **Objective**: Support multi-step execution.
- **Milestones**:
  - Implement cron-like task scheduling inside the Core OS layer.
  - Support recursive planning (where agents can define, execute, and reflect on sub-tasks independently).
  - Add native robotics drivers (e.g., ROS2 bindings) to control hardware components.

---

## Phase 9 — Cloud Sync (Optional)
- **Objective**: End-to-end encrypted backup.
- **Milestones**:
  - Build encrypted sync bridges.
  - Ensure data remains local-first, treating the cloud simply as an encrypted backup vault.
