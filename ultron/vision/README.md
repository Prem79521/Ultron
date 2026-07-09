# ULTRON Vision Module

## Purpose
The Vision module acts as the image, video, and UI screen analyzer of the ULTRON Cognitive Operating System. It enables multi-modal input processing.

## Responsibilities
*   **Frame Capture**: Interfaces with system video cameras or screenshot streams to capture state frames.
*   **Element Segmentation**: Locates UI items, buttons, fields, and text regions.
*   **Object Identification**: Detects objects, outlines, and structures in visual inputs.

## Public Interfaces
*   `class VisionAnalyzer`: Captures and inspects images or visual feeds.
    *   `async def capture_screen() -> Any`
    *   `async def analyze_image(image_path: str, prompt: str) -> str`

## Dependencies
*   `ultron.core` for error reporting.

## Future Expansion
*   Implement real-time screen parsing.
*   Integrate model pipelines (e.g. Gemini Vision or CLIP) to run local UI element detection.

## Design Notes
*   **Privacy Guard**: Screen and frame captures must be explicitly permitted by the security policies defined in the Permissions module.
