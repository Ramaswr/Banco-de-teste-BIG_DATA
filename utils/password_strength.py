"""Password strength checker using zxcvbn."""
from zxcvbn import zxcvbn


def check_password_strength(password: str, user_inputs: list = None) -> dict:
    """
    Analyze password strength using zxcvbn.
    Returns dict with:
    - score (0-4): 0=very weak, 4=very strong
    - feedback: list of suggestions
    - estimated_seconds: time to crack
    """
    if user_inputs is None:
        user_inputs = []

    result = zxcvbn(password, user_inputs=user_inputs)
    return {
        "score": result["score"],
        "feedback": result["feedback"]["suggestions"],
        "warning": result["feedback"].get("warning", ""),
        "estimated_seconds": result.get("crack_times_seconds", {}).get("online_throttling_100_per_hour", 0),
    }


def get_strength_label(score: int) -> str:
    """Convert score (0-4) to label."""
    labels = ["Muito fraca", "Fraca", "Razoável", "Forte", "Muito forte"]
    return labels[min(score, 4)]


def get_strength_color(score: int) -> str:
    """Convert score to HTML color."""
    colors = ["#ef4444", "#f97316", "#eab308", "#84cc16", "#22c55e"]
    return colors[min(score, 4)]
