"""Tone-specific message templates for nudge scenarios."""

from __future__ import annotations

MESSAGE_TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
    "professional_friendly": {
        "reminder": {
            "missing_payments": (
                "Your payment of £{amount} is due on {due_date}. "
                "You're on track — keep it up to protect your credit score."
            ),
            "direct_debit_setup": (
                "Set up a Direct Debit to never miss a payment. "
                "It only takes a few minutes and helps you stay on top of your balance."
            ),
            "reward_criteria": (
                "Great progress — you've made {on_time_count} on-time payment(s). "
                "Make {payments_needed} more to earn your £20 reward."
            ),
        },
        "warning": {
            "missing_payments": (
                "Your account has {missing_count} missed payment(s) in recent cycles. "
                "Please pay £{amount} by {due_date} to avoid further charges and protect your credit file."
            ),
            "direct_debit_setup": (
                "Missing payments can affect your credit score. "
                "Setting up a Direct Debit is the easiest way to stay current."
            ),
            "reward_criteria": (
                "You won't qualify for the £20 reward while payments are missed or late. "
                "Pay £{amount} on time by {due_date} to get back on track."
            ),
        },
        "motivational": {
            "missing_payments": (
                "A late payment was recorded last cycle — but you can turn this around. "
                "Pay £{amount} by {due_date} and rebuild your payment streak."
            ),
            "direct_debit_setup": (
                "Life gets busy. A Direct Debit means one less thing to remember each month."
            ),
            "reward_criteria": (
                "You're close to your £20 reward — just {payments_needed} more on-time payment(s) needed. "
                "You've got this."
            ),
        },
        "reward_led": {
            "missing_payments": (
                "You've earned your £20 reward for consistent on-time payments. "
                "Keep paying on time to maintain your good standing."
            ),
            "direct_debit_setup": (
                "You've qualified for your £20 reward! "
                "Set up a Direct Debit to keep your streak going effortlessly."
            ),
            "reward_criteria": (
                "Congratulations — you've made 3 on-time payments and earned your £20 reward! "
                "It will be credited to your account shortly."
            ),
        },
        "direct_debit_setup": {
            "missing_payments": (
                "Your payment of £{amount} is due on {due_date}. "
                "Set up a Direct Debit now so you never have to worry about missing a date."
            ),
            "direct_debit_setup": (
                "You're paying manually each month. "
                "Switch to Direct Debit — choose full or minimum payment — in just a few taps."
            ),
            "reward_criteria": (
                "Make {payments_needed} more on-time payment(s) to earn £20. "
                "Setting up a Direct Debit makes it effortless."
            ),
        },
    },
    "casual_energetic": {
        "reminder": {
            "missing_payments": (
                "Heads up — £{amount} due {due_date}. You're doing great, keep the streak going!"
            ),
            "direct_debit_setup": (
                "Pro tip: set up Direct Debit and forget about due dates. Takes 2 mins."
            ),
            "reward_criteria": (
                "You're {on_time_count}/3 on-time payments in — {payments_needed} more and you bag £20!"
            ),
        },
        "warning": {
            "missing_payments": (
                "You've missed {missing_count} payment(s) recently. "
                "Pay £{amount} by {due_date} before it gets worse."
            ),
            "direct_debit_setup": (
                "Missed payments hurt your credit score. Direct Debit = sorted. Set it up now."
            ),
            "reward_criteria": (
                "No £20 reward while payments are late or missed. "
                "Pay £{amount} on time by {due_date} to fix that."
            ),
        },
        "motivational": {
            "missing_payments": (
                "One slip last cycle — no stress. Pay £{amount} by {due_date} and bounce back."
            ),
            "direct_debit_setup": (
                "Too much going on? Let Direct Debit handle your payments automatically."
            ),
            "reward_criteria": (
                "So close to £20! Just {payments_needed} more on-time payment(s). You can do it."
            ),
        },
        "reward_led": {
            "missing_payments": (
                "You smashed it — £20 reward unlocked! Keep those on-time payments rolling."
            ),
            "direct_debit_setup": (
                "£20 in the bag! Set up Direct Debit to keep winning every month."
            ),
            "reward_criteria": (
                "Yes! 3 on-time payments done — your £20 reward is on its way."
            ),
        },
        "direct_debit_setup": {
            "missing_payments": (
                "£{amount} due {due_date}. Set up Direct Debit and never miss again."
            ),
            "direct_debit_setup": (
                "Still paying manually? Switch to Direct Debit — full or min payment, your call."
            ),
            "reward_criteria": (
                "{payments_needed} more on-time payment(s) = £20. Direct Debit makes it easy."
            ),
        },
    },
    "supportive_clear": {
        "reminder": {
            "missing_payments": (
                "A friendly reminder that £{amount} is due on {due_date}. "
                "Your consistent payments are helping build a strong credit history."
            ),
            "direct_debit_setup": (
                "Consider setting up a Direct Debit for peace of mind. "
                "You can choose to pay the full balance or the minimum each month."
            ),
            "reward_criteria": (
                "You've made {on_time_count} qualifying on-time payment(s). "
                "Just {payments_needed} more within your first six months to receive £20."
            ),
        },
        "warning": {
            "missing_payments": (
                "We noticed {missing_count} missed payment(s) on your account. "
                "Please arrange payment of £{amount} by {due_date} to avoid additional fees."
            ),
            "direct_debit_setup": (
                "To protect your credit rating, we recommend setting up a Direct Debit "
                "so payments are never overlooked."
            ),
            "reward_criteria": (
                "Unfortunately, missed or late payments mean the £20 reward isn't available right now. "
                "Paying £{amount} on time by {due_date} will help restore your good standing."
            ),
        },
        "motivational": {
            "missing_payments": (
                "Your last payment was late, but it's not too late to get back on track. "
                "Paying £{amount} by {due_date} will help protect your financial wellbeing."
            ),
            "direct_debit_setup": (
                "Managing household finances is demanding. "
                "A Direct Debit ensures your credit card payment is always taken care of."
            ),
            "reward_criteria": (
                "You're nearly there — {payments_needed} more on-time payment(s) "
                "and you'll qualify for your £20 reward."
            ),
        },
        "reward_led": {
            "missing_payments": (
                "Well done — your £20 reward has been earned through consistent, on-time payments."
            ),
            "direct_debit_setup": (
                "You've earned your £20 reward. "
                "Setting up a Direct Debit will help you maintain this positive payment habit."
            ),
            "reward_criteria": (
                "Congratulations on making three on-time payments within your first six months. "
                "Your £20 reward will be applied to your account."
            ),
        },
        "direct_debit_setup": {
            "missing_payments": (
                "Your payment of £{amount} is due on {due_date}. "
                "Setting up a Direct Debit is a simple step towards worry-free payments."
            ),
            "direct_debit_setup": (
                "You're currently making manual payments. "
                "Direct Debit is available for full or minimum payments — set it up in minutes."
            ),
            "reward_criteria": (
                "{payments_needed} more on-time payment(s) will qualify you for the £20 reward. "
                "Direct Debit can help you reach that goal reliably."
            ),
        },
    },
}


def message_scenario_key(
    nudge_type: str,
    reward_eligible: bool,
    reward_near: bool,
    has_missing: bool,
    dd_active: bool,
) -> str:
    """Pick the message sub-scenario for template lookup."""
    if reward_eligible or (nudge_type == "reward_led" and reward_near):
        return "reward_criteria"
    if not dd_active and nudge_type == "direct_debit_setup":
        return "direct_debit_setup"
    if has_missing or nudge_type == "warning":
        return "missing_payments"
    if nudge_type == "direct_debit_setup":
        return "direct_debit_setup"
    return "missing_payments"


def format_message(
    tone: str,
    nudge_type: str,
    scenario_key: str,
    account: dict,
    reward_info: dict,
) -> str:
    """Format a message template with account-specific values."""
    templates = MESSAGE_TEMPLATES.get(tone, MESSAGE_TEMPLATES["supportive_clear"])
    nudge_templates = templates.get(nudge_type, templates["reminder"])
    template = nudge_templates.get(scenario_key, nudge_templates["missing_payments"])

    return template.format(
        amount=account.get("payment_current_due_amount", 25.0),
        due_date=account.get("payment_due_date", ""),
        missing_count=account.get("missing_payments_last_6_cycles", 0),
        on_time_count=reward_info.get("on_time_payments_count", 0),
        payments_needed=reward_info.get("payments_needed", 0),
    )
