"""Gemini API wrapper for insights & reasoning generation."""

import json
from typing import Optional

import google.generativeai as genai

from config import GEMINI_API_KEY


class LLMService:
    """Wrapper for Gemini API calls with fallback handling."""

    def __init__(self):
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.model = None

    def generate_insights(self, financial_context: dict) -> list[dict]:
        """
        Generate actionable insights from financial context via Gemini.

        Args:
            financial_context: dict with keys like total_cash, days_to_zero,
                daily_burn, total_payables, total_receivables, etc.

        Returns:
            List of insight dicts with keys: type, priority, title, description,
            potential_savings
        """
        if not self.model:
            return self._fallback_insights(financial_context)

        prompt = self._build_insights_prompt(financial_context)

        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text.strip()

            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                lines = raw_text.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw_text = "\n".join(lines)

            insights = json.loads(raw_text)
            if isinstance(insights, list):
                return insights
            return self._fallback_insights(financial_context)
        except Exception:
            return self._fallback_insights(financial_context)

    def generate_action_reasoning(self, action_context: dict) -> str:
        """
        Generate a 2-sentence explanation for an action recommendation.

        Falls back to template reasoning if Gemini is unavailable.
        """
        if not self.model:
            return action_context.get("fallback_reasoning", "Action recommended based on priority scoring.")

        prompt = (
            f"In 2 sentences, explain why a tiffin business owner should "
            f"{action_context.get('recommendation', 'take action')} for "
            f"\"{action_context.get('payable_name', 'this payment')}\" "
            f"(₹{action_context.get('amount', 0):,.0f}, due {action_context.get('due_date', 'soon')}).\n"
            f"Current cash: ₹{action_context.get('cash', 0):,.0f}. "
            f"Days to zero: {action_context.get('dtz', 'unknown')}. "
            f"Keep it simple and practical."
        )

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return action_context.get("fallback_reasoning", "Action recommended based on priority scoring.")

    def _build_insights_prompt(self, ctx: dict) -> str:
        """Build the insights generation prompt with financial context."""
        obligations_json = json.dumps(ctx.get("top_obligations", []), default=str, indent=2)
        news_json = json.dumps(ctx.get("recent_news", []), default=str, indent=2)

        return f"""You are a financial advisor for a small tiffin/catering business in India.

Current financial state:
- Cash on hand: ₹{ctx.get('total_cash', 0):,.0f}
- Days until cash runs out: {ctx.get('days_to_zero', 'unknown')}
- Daily burn rate: ₹{ctx.get('daily_burn', 0):,.0f}
- Pending payables: ₹{ctx.get('total_payables', 0):,.0f} ({ctx.get('payables_count', 0)} items)
- Pending receivables: ₹{ctx.get('total_receivables', 0):,.0f} ({ctx.get('receivables_count', 0)} items)
- Overdue receivables: {ctx.get('overdue_count', 0)} items worth ₹{ctx.get('overdue_amount', 0):,.0f}

Top 5 obligations (by priority):
{obligations_json}

Recent food industry news:
{news_json}

Generate 5-7 actionable insights as JSON array. Each insight must have:
- type: "action" | "warning" | "opportunity" | "critical"
- priority: "urgent" | "moderate" | "low"
- title: short headline (max 8 words)
- description: 2-3 sentences, practical advice in simple language
- potential_savings: number or null

Think like a practical business advisor. The owner reads Tamil newspapers and manages a kitchen — keep language simple.
Respond ONLY with the JSON array, no markdown."""

    def _fallback_insights(self, ctx: dict) -> list[dict]:
        """Generate deterministic fallback insights when LLM is unavailable."""
        insights = []
        dtz = ctx.get("days_to_zero", 30)
        total_cash = ctx.get("total_cash", 0)
        total_payables = ctx.get("total_payables", 0)
        daily_burn = ctx.get("daily_burn", 0)

        if dtz <= 3:
            insights.append({
                "type": "critical",
                "priority": "urgent",
                "title": "Cash crisis imminent",
                "description": (
                    f"Your cash will run out in {dtz} days at current spending. "
                    f"Delay non-essential payments and chase pending receivables immediately."
                ),
                "potential_savings": None,
            })

        if total_payables > total_cash:
            deficit = total_payables - total_cash
            insights.append({
                "type": "warning",
                "priority": "urgent",
                "title": f"₹{deficit:,.0f} payment deficit",
                "description": (
                    f"You owe ₹{total_payables:,.0f} but only have ₹{total_cash:,.0f}. "
                    f"Prioritize high-obligation payments and negotiate delays on others."
                ),
                "potential_savings": None,
            })

        if ctx.get("overdue_count", 0) > 0:
            insights.append({
                "type": "action",
                "priority": "urgent",
                "title": "Chase overdue receivables",
                "description": (
                    f"You have {ctx['overdue_count']} overdue receivables worth "
                    f"₹{ctx.get('overdue_amount', 0):,.0f}. Follow up today to improve cash position."
                ),
                "potential_savings": ctx.get("overdue_amount", 0),
            })

        # Subscription optimization
        for ob in ctx.get("top_obligations", []):
            if ob.get("category") == "subscription" and ob.get("flexibility", 0) >= 70:
                insights.append({
                    "type": "action",
                    "priority": "moderate",
                    "title": f"Cancel {ob.get('name', 'subscription')}",
                    "description": (
                        f"This subscription costs ₹{ob.get('amount', 0):,.0f}/month and has low "
                        f"operational importance. Consider pausing it during this cash crunch."
                    ),
                    "potential_savings": ob.get("amount", 0),
                })

        if daily_burn > 0 and dtz <= 7:
            insights.append({
                "type": "opportunity",
                "priority": "moderate",
                "title": "Reduce daily burn rate",
                "description": (
                    f"Your daily expenses are ₹{daily_burn:,.0f}. Even a 10% reduction "
                    f"saves ₹{daily_burn * 0.1 * 7:,.0f}/week and extends your runway."
                ),
                "potential_savings": round(daily_burn * 0.1 * 30, 2),
            })

        # Always provide at least one insight
        if not insights:
            insights.append({
                "type": "opportunity",
                "priority": "low",
                "title": "Cash position is healthy",
                "description": (
                    "Your finances look stable. Keep monitoring daily and maintain a buffer "
                    "for unexpected expenses."
                ),
                "potential_savings": None,
            })

        return insights


# Singleton instance
llm_service = LLMService()
