"""edgar-extract dashboard. Reads only data/dashboard.db — no LLM, no API key needed.

Run locally:
    streamlit run dashboard/app.py
"""

import altair as alt
import pandas as pd
import streamlit as st

import dashboard_data as data

st.set_page_config(page_title="edgar-extract", page_icon="📊", layout="wide")

# Categorical slots 1–2 of the validated reference palette, stepped per theme.
SERIES_COLORS = {"light": ["#2a78d6", "#eb6834"], "dark": ["#3987e5", "#d95926"]}
LABEL_INK = {"light": "#52514e", "dark": "#c3c2b7"}


def theme_type() -> str:
    theme = getattr(st.context, "theme", None)
    return "dark" if getattr(theme, "type", None) == "dark" else "light"


@st.cache_data
def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    return data.load_evaluations(), data.load_runs()


all_evals, all_runs = load()
models = sorted(all_evals["model"].unique())  # fixed order -> each model always keeps its color
mode = theme_type()
model_scale = alt.Scale(domain=models, range=SERIES_COLORS[mode][: len(models)])


def grouped_accuracy_bars(df: pd.DataFrame, x: str, x_title: str, offset: str, scale: alt.Scale, height: int = 320):
    """Grouped bars of accuracy (0–100 %) with direct labels and a hover tooltip."""
    base = alt.Chart(df).encode(
        x=alt.X(f"{x}:N", title=x_title, sort=None, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset(f"{offset}:N", sort=scale.domain),
        y=alt.Y("accuracy:Q", title="Accuracy", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%", tickCount=5)),
        tooltip=[
            alt.Tooltip(f"{offset}:N", title=offset.capitalize()),
            alt.Tooltip(f"{x}:N", title=x_title),
            alt.Tooltip("accuracy:Q", title="Accuracy", format=".0%"),
            alt.Tooltip("correct:Q", title="Correct"),
            alt.Tooltip("graded:Q", title="Graded values"),
        ],
    )
    bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, stroke=None).encode(
        color=alt.Color(f"{offset}:N", scale=scale, legend=alt.Legend(title=None, orient="top"))
    )
    labels = base.mark_text(dy=-8, fontSize=12, color=LABEL_INK[mode]).encode(text=alt.Text("accuracy:Q", format=".0%"))
    return (bars + labels).properties(height=height).configure_scale(bandPaddingInner=0.25, bandWithNestedOffsetPaddingInner=0.08)


st.title("edgar-extract")
st.caption(
    "How accurately do free local LLMs extract five metrics from SEC 10-K filings? "
    f"Every value is checked against XBRL data (0.5 % tolerance). {all_evals['accession_number'].nunique()} filings, "
    f"{all_evals['ticker'].nunique()} companies, models: {', '.join(models)}."
)

# Development companies were used to tune prompts and code; held-out companies never were.
datasets = [d for d in data.DATASETS if d in set(all_evals["dataset"])]
dataset = st.radio(
    "Data set",
    datasets,
    horizontal=True,
    key="dataset",
    format_func=lambda d: (
        f"{data.DATASETS[d]} ({all_evals.loc[all_evals['dataset'] == d, 'ticker'].nunique()} companies, "
        f"{all_evals.loc[all_evals['dataset'] == d, 'accession_number'].nunique()} filings)"
    ),
    help="Development: the companies the prompts and code were tuned on (optimistic). "
    "Held-out test: companies added afterwards and never used for tuning.",
)
evals = all_evals[all_evals["dataset"] == dataset]
runs = all_runs[all_runs["dataset"] == dataset]
summary = data.run_summary(evals, runs)
versions = sorted(evals["version"].unique())
latest = versions[-1]
dev_summary = data.run_summary(
    all_evals[all_evals["dataset"] == "development"], all_runs[all_runs["dataset"] == "development"]
)

# A radio (not st.tabs) remembers the open view when a table selection reruns the app,
# and unlike a segmented control it cannot be "unselected" by clicking the active option.
VIEWS = ["Overview", "Model A vs B", "Error browser"]
view = st.radio("View", VIEWS, horizontal=True, key="view", label_visibility="collapsed")

# ------------------------------------------------------------------ overview
if view == "Overview":
    st.subheader(f"Latest version ({latest})")
    columns = st.columns(len(models))
    for column, model in zip(columns, models):
        row = summary[(summary["model"] == model) & (summary["version"] == latest)].iloc[0]
        # Held-out data has only the latest version: compare with development instead.
        if len(versions) > 1:
            first = summary[(summary["model"] == model) & (summary["version"] == versions[0])].iloc[0]
            delta_label = f"vs {versions[0]}"
        else:
            first = dev_summary[(dev_summary["model"] == model) & (dev_summary["version"] == latest)].iloc[0]
            delta_label = "vs development"
        with column:
            st.markdown(f"**{model}**")
            a, b, c = st.columns(3)
            a.metric(
                "Accuracy",
                f"{row['accuracy']:.0%}",
                f"{(row['accuracy'] - first['accuracy']) * 100:+.0f} pp {delta_label}",
            )
            b.metric("Seconds / filing", f"{row['seconds_per_filing']:.1f}")
            c.metric("Cost / filing", f"${row['cost_per_filing']:.2f}")

    st.subheader("Accuracy by version")
    st.caption("v1: first prompt · v2: prompt with general rules · v3: v2 + unit read from the table header in code")
    st.altair_chart(grouped_accuracy_bars(summary, "version", "Version", "model", model_scale), width="stretch")

    st.subheader("Runs")
    st.dataframe(
        summary.assign(
            accuracy=summary["accuracy"] * 100,
            cost_per_filing=summary["cost_per_filing"].map(lambda v: f"${v:.2f}"),
        )[
            ["run", "accuracy", "seconds_per_filing", "format_issues", "cost_per_filing"]
        ],
        hide_index=True,
        width="stretch",
        column_config={
            "run": "Model / version",
            "accuracy": st.column_config.NumberColumn("Accuracy", format="%.0f%%"),
            "seconds_per_filing": st.column_config.NumberColumn("Sec / filing", format="%.1f"),
            "format_issues": st.column_config.NumberColumn("Format issues", help="Answers that did not follow the form, e.g. numbers as text"),
            "cost_per_filing": "Cost / filing",
        },
    )

    st.subheader("Errors by category")
    st.caption("Graded values only. Metrics a company does not report are not counted here.")
    st.dataframe(data.error_counts(evals), width="stretch")

# ------------------------------------------------------------- A vs B
elif view == "Model A vs B":
    run_names = list(summary["run"])
    default_a = data.run_label(models[-1], latest)
    default_b = data.run_label(models[0], latest)
    col_a, col_b, col_by = st.columns(3)
    run_a = col_a.selectbox("Model A", run_names, index=run_names.index(default_a))
    run_b = col_b.selectbox("Model B", run_names, index=run_names.index(default_b))
    by = col_by.radio("Compare by", ["Metric", "Company"], horizontal=True)

    column = "metric" if by == "Metric" else "ticker"
    per = data.accuracy_by(evals[evals["run"].isin([run_a, run_b])], column)
    # Each model keeps its color from the overview; two versions of the same model use both slots.
    model_a, model_b = run_a.split(" / ")[0], run_b.split(" / ")[0]
    color_a = SERIES_COLORS[mode][models.index(model_a)]
    color_b = SERIES_COLORS[mode][models.index(model_b)] if model_a != model_b else next(
        c for c in SERIES_COLORS[mode] if c != color_a
    )
    ab_scale = alt.Scale(domain=[run_a, run_b], range=[color_a, color_b])
    if run_a == run_b:
        st.info("Pick two different runs to compare.")
    else:
        if by == "Metric":
            per[column] = pd.Categorical(per[column], categories=data.METRICS, ordered=True)
            per = per.sort_values(column)
        st.altair_chart(grouped_accuracy_bars(per, column, by, "run", ab_scale), width="stretch")

        st.subheader("Where they disagree")
        diff = data.disagreements(evals, run_a, run_b)
        if diff.empty:
            st.success("Both runs are right and wrong on exactly the same values.")
        else:
            st.dataframe(
                pd.DataFrame(
                    {
                        "Company": diff["ticker"],
                        "FY": diff["fiscal_year"],
                        "Metric": diff["metric"],
                        "Correct": [data.format_usd(v, m) for v, m in zip(diff["truth"], diff["metric"])],
                        f"A: {run_a}": [data.format_usd(v, m) for v, m in zip(diff["value_usd_a"], diff["metric"])],
                        f"B: {run_b}": [data.format_usd(v, m) for v, m in zip(diff["value_usd_b"], diff["metric"])],
                        "A result": diff["category_a"].map(data.CATEGORY_LABELS),
                        "B result": diff["category_b"].map(data.CATEGORY_LABELS),
                    }
                ),
                hide_index=True,
                width="stretch",
            )

# --------------------------------------------------------------- errors
elif view == "Error browser":
    f1, f2, f3, f4 = st.columns(4)
    pick_models = f1.multiselect("Model", models, default=models)
    pick_versions = f2.multiselect("Version", versions, default=[latest])
    categories = [c for c in data.CATEGORY_LABELS if c not in ("correct", "no_truth_null")]
    pick_categories = f3.multiselect(
        "Category", categories, default=categories, format_func=lambda c: data.CATEGORY_LABELS[c]
    )
    pick_tickers = f4.multiselect("Company", sorted(evals["ticker"].unique()), default=sorted(evals["ticker"].unique()))

    errors = evals[
        evals["model"].isin(pick_models)
        & evals["version"].isin(pick_versions)
        & evals["category"].isin(pick_categories)
        & evals["ticker"].isin(pick_tickers)
    ].sort_values(["run", "ticker", "fiscal_year", "metric"]).reset_index(drop=True)

    st.caption(f"{len(errors)} values match the filters. Select a row to see the source.")
    if errors.empty:
        st.success("No errors for this selection.")
    else:
        shown = pd.DataFrame(
            {
                "Model / version": errors["run"],
                "Company": errors["ticker"],
                "FY": errors["fiscal_year"],
                "Metric": errors["metric"],
                "Correct": [data.format_usd(v, m) for v, m in zip(errors["truth"], errors["metric"])],
                "Extracted": [data.format_usd(v, m) for v, m in zip(errors["value_usd"], errors["metric"])],
                "Category": errors["category"].map(data.CATEGORY_LABELS),
            }
        )
        event = st.dataframe(
            shown, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row"
        )
        selected = event.selection.rows
        if selected:
            row = errors.iloc[selected[0]]
            st.divider()
            st.subheader(f"{row['ticker']} FY{row['fiscal_year']} · {row['metric']} · {row['run']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Correct (XBRL)", data.format_usd(row["truth"], row["metric"]))
            c2.metric("Extracted", data.format_usd(row["value_usd"], row["metric"]))
            c3.metric("Category", data.CATEGORY_LABELS[row["category"]])
            if row["detail"]:
                # "$" would start a math formula in Markdown, so escape it.
                st.markdown(f"**Why:** {row['detail'].replace('$', chr(92) + '$')}")
            quote_found = {1: "yes", 0: "no"}.get(row["quote_in_source"], "—")
            st.markdown(f"**Model's quote:** `{row['quote'] or '—'}` · found in source text: **{quote_found}**")

            st.markdown("**Source statements** — ✓ row with the correct value · ▶ row with the model's value")
            text = data.load_statement_text(row["accession_number"])
            truth = row["truth"] if pd.notna(row["truth"]) else None
            value = row["value"] if pd.notna(row["value"]) else None
            marked = data.mark_source_lines(text, truth, value, row["metric"])
            only_marked = st.toggle("Show only marked rows", value=True)
            lines = [f"{m} {line}" for m, line in marked if not only_marked or m.strip()]
            source = "\n".join(lines) or "(no matching rows)"
            if only_marked:
                st.code(source, language=None)
            else:
                with st.container(height=420):
                    st.code(source, language=None)
