from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SettingsPayload(ApiModel):
    ai_provider: Literal["sweety", "openai"] = Field(alias="aiProvider")
    openai_api_key: str = Field(default="", alias="openAiApiKey")
    openai_model: str = Field(default="gpt-5.5", min_length=1, alias="openAiModel")
    check_interval_seconds: int = Field(ge=1, le=3600, alias="checkIntervalSeconds")
    reply_delay_min_seconds: int = Field(ge=0, le=3600, alias="replyDelayMinSeconds")
    reply_delay_max_seconds: int = Field(ge=0, le=3600, alias="replyDelayMaxSeconds")

    @model_validator(mode="after")
    def validate_delay_range(self) -> "SettingsPayload":
        if self.reply_delay_max_seconds < self.reply_delay_min_seconds:
            raise ValueError("replyDelayMaxSeconds must be greater than or equal to replyDelayMinSeconds")
        return self


class TargetPayload(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    age_group: Literal["20-35", "35-50", "50-65", "65+"] = Field(alias="ageGroup")
    gender: Literal["female", "male"]
    persona_id: str = Field(min_length=1, alias="personaId")
    persona_source: Literal["base", "custom"] = Field(alias="personaSource")
    weapon_id: str = Field(default="persona-only", min_length=1, alias="weaponId")
    weapon_source: Literal["base", "custom"] = Field(default="base", alias="weaponSource")
    reply_enabled: bool = Field(default=False, alias="replyEnabled")


class CustomItemPayload(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=12000)
    image_data_url: str | None = Field(default=None, alias="imageDataUrl")
    source_base_id: str | None = Field(default=None, alias="sourceBaseId")
