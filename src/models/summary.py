from pydantic import BaseModel, field_validator


class NextSteps(BaseModel):
    company: str
    other: str = "None"


class VehicleDamage(BaseModel):
    vehicle_status: str
    towage: str = "None"
    car_hire: str = "None"


class CallSummary(BaseModel):
    caller: str
    subject: str
    executive_summary: str
    next_steps: NextSteps
    follow_up_required: bool = False
    follow_up_reason: str | None = None
    liability_summary: str | None = None
    negotiation_summary: str | None = None
    vehicle_damage: VehicleDamage | None = None
    injury: str | None = None
    property_damage: str | None = None

    @field_validator("caller")
    @classmethod
    def caller_must_have_structure(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Caller field cannot be empty")
        return v

    def render(self) -> str:
        """Render summary in the required output format."""
        lines = []
        lines.append(f"Caller: {self.caller}")
        lines.append("")
        lines.append("Subject:")
        lines.append(self.subject)
        lines.append("")
        lines.append("Executive Summary:")
        lines.append(self.executive_summary)
        lines.append("")
        lines.append("Next Steps:")
        lines.append(f"COMPANY: {self.next_steps.company}")
        lines.append(f"Other: {self.next_steps.other}")

        if self.follow_up_required:
            lines.append("")
            lines.append("Follow-Up Required: Yes")
            if self.follow_up_reason:
                lines.append(f"Reason: {self.follow_up_reason}")

        if self.liability_summary:
            lines.append("")
            lines.append("Liability Summary:")
            lines.append(self.liability_summary)

        if self.negotiation_summary:
            lines.append("")
            lines.append("Negotiation Summary:")
            lines.append(self.negotiation_summary)

        if self.vehicle_damage:
            lines.append("")
            lines.append("Vehicle Damage:")
            lines.append(f"Vehicle Status: {self.vehicle_damage.vehicle_status}")
            lines.append(f"Towage: {self.vehicle_damage.towage}")
            lines.append(f"Car hire: {self.vehicle_damage.car_hire}")

        if self.injury:
            lines.append("")
            lines.append("Injury:")
            lines.append(f"Treatment: {self.injury}")

        if self.property_damage:
            lines.append("")
            lines.append("Property:")
            lines.append(self.property_damage)

        return "\n".join(lines)

    def char_count(self) -> int:
        return len(self.render())

    def is_within_limit(self) -> bool:
        return self.char_count() <= 1500
