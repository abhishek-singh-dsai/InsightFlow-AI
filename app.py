"""Chainlit UI for InsightFlow AI. Start with: chainlit run app.py -w"""

from __future__ import annotations

import logging

import chainlit as cl

from insightflow.ai import answer_question, describe_dataset, enabled, interpret_chart
from insightflow.analysis import DatasetError, dataset_profile, format_profile, load_csv
from insightflow.visuals import create_charts

logger = logging.getLogger(__name__)


@cl.on_chat_start
async def on_chat_start():
    await cl.Message(content=(
        "# InsightFlow AI 📊\n"
        "Upload a CSV for reproducible EDA, charts, and optional Gemini explanations. "
        "No API key is required for the statistical analysis."
    )).send()
    uploads = await cl.AskFileMessage(
        content="Upload one UTF-8 CSV (10 MB maximum).",
        accept=["text/csv", "application/vnd.ms-excel"],
        max_size_mb=10, max_files=1, timeout=180,
    ).send()
    if not uploads:
        await cl.Message(content="No CSV uploaded. Start a new chat when you're ready.").send()
        return

    status = cl.Message(content="Analyzing your dataset…")
    await status.send()
    try:
        df = load_csv(uploads[0].path)
        profile = dataset_profile(df)
        cl.user_session.set("profile", profile)
        await cl.Message(content=format_profile(profile)).send()
        charts = create_charts(df)
        if charts:
            for chart in charts:
                await cl.Message(
                    content=f"### {chart.title}\n{chart.description}",
                    elements=[cl.Image(name=chart.title, content=chart.png, display="inline")],
                ).send()
        else:
            await cl.Message(content="No suitable numeric or categorical features for automatic charts.").send()

        if enabled():
            try:
                interpretation = await describe_dataset(profile)
                await cl.Message(content=f"### AI exploratory report\n{interpretation}").send()
            except Exception:
                logger.exception("AI report failed")
                await cl.Message(content="AI report unavailable. Statistics and charts remain valid.").send()
            for chart in charts[:2]:  # Avoid excessive API usage and latency.
                try:
                    narrative = await interpret_chart(chart.png, chart.title, profile)
                    await cl.Message(content=f"**AI chart notes — {chart.title}**\n{narrative}").send()
                except Exception:
                    logger.warning("AI chart interpretation failed for %s", chart.title)
        else:
            await cl.Message(content=(
                "**AI is disabled.** Statistical profiling and charts run locally. "
                "Set `GOOGLE_API_KEY` to enable narrative insights and grounded Q&A."
            )).send()
        status.content = "✅ EDA complete. Ask a question about the dataset's aggregated statistics."
        await status.update()
    except DatasetError as exc:
        status.content = f"Could not analyze the CSV: {exc}"
        await status.update()
    except Exception:
        logger.exception("Unexpected analysis error")
        status.content = "Unexpected analysis error. Check application logs (no dataset content is logged)."
        await status.update()


@cl.on_message
async def on_message(message: cl.Message):
    profile = cl.user_session.get("profile")
    if not profile:
        await cl.Message(content="Please start a new chat and upload a CSV first.").send()
        return
    if not message.content.strip():
        await cl.Message(content="Please enter a question about your dataset.").send()
        return
    try:
        response = await answer_question(message.content, profile)
    except Exception:
        logger.exception("AI question failed")
        response = "AI unavailable right now. The descriptive statistics above are still available."
    await cl.Message(content=response).send()
