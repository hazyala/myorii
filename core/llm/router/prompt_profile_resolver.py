from __future__ import annotations

from core.llm.prompt_loader import load_prompt


class PromptProfileResolver:
    """Builds a short system prompt from common and intent-specific profiles."""

    _PROFILE_BY_INTENT = {
        "simple_chat": ("simple_chat.md",),
        "translate": ("translate.md",),
        "command": ("command.md",),
        "commit_message": ("commit_message.md",),
        "pr_description": ("pr_description.md",),
        "code_explain": ("code_explain.md",),
        "code_fix": ("code_fix.md",),
        "image_question": ("image_question.md",),
        "image_code_transcription": ("image_code_transcription.md",),
        "document_question": ("document_question.md",),
        "spreadsheet_question": ("document_question.md",),
    }

    _NAMING_SPECIFIC_PROFILES = {
        "naming_function": "naming_function.md",
        "naming_variable": "naming_variable.md",
        "naming_class": "naming_class.md",
        "naming_file": "naming_file.md",
    }

    def resolve(self, intent: str) -> str:
        prompt_parts = [load_prompt("system.md")]

        if intent.startswith("naming_"):
            profile_names = ["naming_common.md"]
            specific_profile = self._NAMING_SPECIFIC_PROFILES.get(intent)
            if specific_profile is not None:
                profile_names.append(specific_profile)
        else:
            profile_names = list(self._PROFILE_BY_INTENT.get(intent, ("simple_chat.md",)))

        for profile_name in profile_names:
            prompt_parts.append(load_prompt("profiles", profile_name))

        return "\n\n".join(part for part in prompt_parts if part)
