"""Shared inventory page renderer."""
from datetime import datetime, timezone
import pandas as pd
import plotly.express as px
import streamlit as st

FIELDS = [
    "common_name",
    "scientific_name",
    "primary_habitat",
    "mean_centroid_hz",
    "rms_energy_mean",
    "zero_crossing_rate_mean",
    "min_frequency_hz",
    "max_frequency_hz",
    "avg_duration_sec",
    "conservation_status",
    "recorded_location",
]
NUMERIC = {
    "mean_centroid_hz",
    "rms_energy_mean",
    "zero_crossing_rate_mean",
    "min_frequency_hz",
    "max_frequency_hz",
    "avg_duration_sec",
}
FIELD_LABELS = {
    "mean_centroid_hz": "Mean spectral centroid (Hz)",
    "rms_energy_mean": "Mean RMS energy",
    "zero_crossing_rate_mean": "Mean zero-crossing rate (0–1)",
    "min_frequency_hz": "Minimum frequency (Hz)",
    "max_frequency_hz": "Maximum frequency (Hz)",
    "avg_duration_sec": "Average duration (seconds)",
}


def _label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " ").title())


def _numeric_input(field: str, value: float, key: str | None = None) -> float:
    options = {"min_value": 0.0, "value": value, "step": 0.01, "format": "%.4f"}
    if field == "zero_crossing_rate_mean":
        options["max_value"] = 1.0
    if key:
        options["key"] = key
    return st.number_input(_label(field), **options)

def render_inventory(manager, title: str, description: str):
    st.title(title)
    st.caption(description)
    if getattr(manager, "last_error", ""):
        st.error(f"Inventory could not be loaded: {manager.last_error}")
    stats = manager.get_summary_stats()
    cols = st.columns(4)
    cols[0].metric("Records", stats["records"])
    cols[1].metric("Habitats", stats["habitats"])
    cols[2].metric("Status categories", stats["conservation_categories"])
    cols[3].metric("Mean call length", f"{stats['mean_duration_sec']:.2f} s")
    tabs = st.tabs(["View & Filter", "Add Entry", "Edit / Delete", "Visualizations", "Audit & Export"])
    with tabs[0]:
        c1, c2, c3 = st.columns([2, 1, 1])
        query = c1.text_input("Search all fields", key=f"{title}_query")
        habitats = ["All habitats"] + sorted([x for x in manager.data["primary_habitat"].astype(str).unique() if x])
        habitat = c2.selectbox("Habitat", habitats, key=f"{title}_habitat")
        sort = c3.selectbox("Sort by", manager.schema_columns, index=1, key=f"{title}_sort")
        ascending = st.checkbox("Ascending", value=True, key=f"{title}_asc")
        filtered = manager.read_records(query, habitat, sort, ascending)
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(filtered)} of {len(manager.data)} records")
    with tabs[1]:
        with st.form(f"{title}_create", clear_on_submit=True):
            entry = {"id": st.text_input("Unique record ID *")}
            values = {}
            for field in FIELDS:
                if field in NUMERIC:
                    values[field] = _numeric_input(field, 0.0)
                else:
                    values[field] = st.text_input(_label(field))
            if st.form_submit_button("Add record", type="primary"):
                if not entry["id"].strip() or not values["common_name"].strip() or not values["scientific_name"].strip():
                    st.error("ID, common name, and scientific name are required.")
                else:
                    ok, message = manager.create_record({**entry, **values})
                    (st.success if ok else st.error)(message)
    with tabs[2]:
        data = manager.data
        if data.empty:
            st.info("There are no records to edit.")
        else:
            selected_id = st.selectbox("Select record", data["id"].astype(str).tolist(), key=f"{title}_record")
            row = data.loc[data["id"].astype(str).eq(selected_id)].iloc[0]
            with st.form(f"{title}_update"):
                updates = {}
                for field in FIELDS:
                    value = row[field]
                    if field in NUMERIC:
                        try: value = float(value)
                        except (TypeError, ValueError): value = 0.0
                        updates[field] = _numeric_input(field, value)
                    else:
                        updates[field] = st.text_input(_label(field), value=str(value))
                if st.form_submit_button("Save changes", type="primary"):
                    if not updates["common_name"].strip() or not updates["scientific_name"].strip():
                        st.error("Common name and scientific name are required.")
                    else:
                        ok, message = manager.update_record(selected_id, updates)
                        (st.success if ok else st.error)(message)
            st.divider()
            st.warning(f"Delete {row['common_name']} (ID {selected_id})? This cannot be undone.")
            confirmed = st.checkbox("Yes, delete", key=f"{title}_confirm")
            if st.button("Delete selected record", disabled=not confirmed, key=f"{title}_delete"):
                ok, message = manager.delete_record(selected_id)
                (st.success if ok else st.error)(message)
                if ok: st.rerun()
    with tabs[3]:
        if manager.data.empty:
            st.info("Add inventory entries to see charts.")
        else:
            chart_data = manager.read_records(query if 'query' in locals() else "", habitat if 'habitat' in locals() else "All habitats")
            numeric = chart_data.copy()
            for field in ["mean_centroid_hz", "min_frequency_hz", "max_frequency_hz"]:
                numeric[field] = pd.to_numeric(numeric[field], errors="coerce")
            st.plotly_chart(px.scatter(numeric, x="min_frequency_hz", y="max_frequency_hz", color="conservation_status", hover_name="common_name", title="Recorded frequency ranges"), use_container_width=True)
            distribution = chart_data["conservation_status"].value_counts().rename_axis("status").reset_index(name="records")
            st.plotly_chart(px.bar(distribution, x="status", y="records", color="status", title="Conservation status distribution"), use_container_width=True)
    with tabs[4]:
        active_filters = {"search": query, "habitat": habitat, "sort_by": sort, "ascending": ascending}
        report = f"BioEcho Inventory Report\nGenerated (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}\nRows in report: {len(filtered)}\nActive filters: {active_filters}\n\n{filtered.to_csv(index=False)}"
        st.code(f"Report rows: {len(filtered)}\nFilters: {active_filters}")
        base = title.lower().replace(" ", "_").replace("&", "and")
        st.download_button("Download formatted text report", report, file_name=f"{base}_report.txt", mime="text/plain")
        st.download_button("Download filtered CSV", filtered.to_csv(index=False), file_name=f"{base}_inventory.csv", mime="text/csv")
