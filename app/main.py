import streamlit as st
import json
import copy

# ===== Utility functions =====

def highlight_pii(text, piis):
    """Highlight PII values in text with colored spans."""
    for pii, info in sorted(piis.items(), key=lambda x: -len(x[0])):
        color = "#4a90e2" if info["relevance"] == "high" else "#ffa726"
        text = text.replace(
            pii,
            f"<span style='background-color:{color}; color:white; padding:2px 4px; border-radius:4px'>{pii}</span>"
        )
    return text


def save_current_edits(idx, entries):
    """Synchronize current UI values back into entries[idx]."""
    entry = entries[idx]
    entry["context"] = st.session_state.get(f"context_{idx}", entry["context"])
    entry["question"] = st.session_state.get(f"question_{idx}", entry["question"])

    updated_piis = {}
    for pii, info in entry["piis"].items():
        t_key = f"type_{idx}_{pii}"
        r_key = f"rel_{idx}_{pii}"
        new_type = st.session_state.get(t_key, info["type"])
        new_rel = st.session_state.get(r_key, info["relevance"])
        updated_piis[pii] = {"type": new_type, "relevance": new_rel}

    entry["piis"] = updated_piis
    entries[idx] = entry
    st.session_state.entries = entries


def refresh_pii_from_context(entry):
    """Keep only PIIs that still appear in context text."""
    context = entry["context"]
    entry["piis"] = {
        pii: info for pii, info in entry["piis"].items() if pii in context
    }
    return entry


# ===== Streamlit app =====

st.set_page_config(page_title="PII Annotation Tool", layout="wide")
st.title("🔍 Context-Aware PII Annotation Tool")

uploaded_file = st.file_uploader("Upload JSONL file", type=["jsonl"])

PII_TYPES = ["age", "contact", "education", "family", "finance", "health", "location", "name", "nationality", "occupation", "public organization", "sexual orientation"]

# ---------- Load ----------
if uploaded_file and "entries" not in st.session_state:
    lines = uploaded_file.getvalue().decode("utf-8").splitlines()
    entries = [json.loads(line) for line in lines]
    st.session_state.entries = copy.deepcopy(entries)
    st.session_state.original_entries = copy.deepcopy(entries)
    st.session_state.current_idx = 0

if "entries" in st.session_state:
    entries = st.session_state.entries
    idx = st.session_state.current_idx
    entry = entries[idx]

    # ---------- Header ----------
    if "id" in entry:
        st.markdown(
            f"### Entry {idx + 1} / {len(entries)} "
            f"<span style='color:gray;'>(<code>{entry['id']}</code>)</span>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(f"### Entry {idx + 1} / {len(entries)}")

    # ---------- Navigation ----------
    nav1, nav2, nav3 = st.columns([1.5, 3, 1.5])
    with nav1:
        if st.button("⬅️ Previous", disabled=(idx == 0)):
            save_current_edits(idx, entries)
            st.session_state.current_idx = max(0, idx - 1)
            st.rerun()
    with nav2:
        goto = st.number_input(
            "Go to entry:",
            min_value=1, max_value=len(entries), value=idx + 1, step=1,
            label_visibility="collapsed"
        )
        if st.button("Go"):
            save_current_edits(idx, entries)
            st.session_state.current_idx = int(goto) - 1
            st.rerun()
    with nav3:
        if st.button("Next ➡️", disabled=(idx == len(entries) - 1)):
            save_current_edits(idx, entries)
            st.session_state.current_idx = min(len(entries) - 1, idx + 1)
            st.rerun()

    # ---------- Context (editable) ----------
    context_key = f"context_{idx}"
    if context_key not in st.session_state:
        st.session_state[context_key] = entry["context"]

    st.markdown("**Context (editable):**")
    st.text_area("Edit context", st.session_state[context_key], height=180, key=context_key)

    # ---------- Add new PII ----------
    st.markdown("### ➕ Add New PII")
    add_col1, add_col2, add_col3, add_col4 = st.columns([2, 2, 2, 1])
    with add_col1:
        new_pii_val = st.text_input("PII value", key=f"new_val_{idx}")
    with add_col2:
        new_pii_type = st.selectbox("Type", PII_TYPES, key=f"new_type_{idx}")
    with add_col3:
        new_pii_rel = st.selectbox("Relevance", ["high", "low"], key=f"new_rel_{idx}")
    with add_col4:
        if st.button("➕ Add PII"):
            save_current_edits(idx, entries)
            context_text = st.session_state[context_key]
            pii_val = new_pii_val.strip()

            if not pii_val:
                st.warning("Please enter a PII value before adding.")
            elif pii_val not in context_text:
                st.error("❌ The PII value does not appear in the context. Add it to the text first.")
            else:
                # Add the new PII
                entry["piis"][pii_val] = {"type": new_pii_type, "relevance": new_pii_rel}
                # Immediately refresh (Update PII list)
                entry = refresh_pii_from_context(entry)
                entries[idx] = entry
                st.session_state.entries = entries
                st.success(f"✅ Added PII: {pii_val} and updated PII list.")
                st.rerun()

    # ---------- Update (keep only PIIs in context) ----------
    if st.button("🔄 Update PII list from context"):
        save_current_edits(idx, entries)
        entry = refresh_pii_from_context(entry)
        entries[idx] = entry
        st.session_state.entries = entries
        st.success("PIIs updated to match context.")
        st.rerun()

    # ---------- Preview ----------
    st.markdown("**Preview with highlights: (blue - high relevance, yellow - low relevance)**")
    st.markdown(
        f"<div style='border:1px solid #ddd; padding:10px; border-radius:8px;'>{highlight_pii(entry['context'], entry['piis'])}</div>",
        unsafe_allow_html=True
    )

    # ---------- Question ----------
    question_key = f"question_{idx}"
    if question_key not in st.session_state:
        st.session_state[question_key] = entry["question"]

    st.markdown("**Question:**")
    st.text_area("Edit question", st.session_state[question_key], height=120, key=question_key)

    # ---------- PII Editing ----------
    st.markdown("**PIIs:**")
    for pii, info in entry["piis"].items():
        t_key = f"type_{idx}_{pii}"
        r_key = f"rel_{idx}_{pii}"
        if t_key not in st.session_state:
            st.session_state[t_key] = info["type"]
        if r_key not in st.session_state:
            st.session_state[r_key] = info["relevance"]

        exp_label = f"🔹 **{pii}** *({st.session_state[t_key]})*"
        with st.expander(exp_label, expanded=False):
            st.selectbox("Type", PII_TYPES,
                         index=PII_TYPES.index(st.session_state[t_key])
                         if st.session_state[t_key] in PII_TYPES else len(PII_TYPES)-1,
                         key=t_key)
            st.selectbox("Relevance", ["high", "low"],
                         index=0 if st.session_state[r_key] == "high" else 1,
                         key=r_key)

    # ---------- Save ----------
    if st.button("💾 Save edits"):
        save_current_edits(idx, entries)
        st.success("Edits saved (in memory).")

    # ---------- Download / Load Original ----------
    st.markdown("---")
    colA, colB = st.columns(2)
    with colA:
        if st.download_button(
            "⬇️ Download Updated JSONL",
            data="\n".join(
                json.dumps(e, ensure_ascii=False)
                for e in (
                    save_current_edits(st.session_state.current_idx, st.session_state.entries)
                    or st.session_state.entries
                )
            ),
            file_name="annotated.jsonl",
            mime="application/jsonl"
        ):
            st.success("✅ Edits saved and file ready for download.")

    with colB:
        if st.button("🧩 Load Original"):
            if "original_entries" in st.session_state:
                # Fully reset Streamlit session state
                original = copy.deepcopy(st.session_state.original_entries)
                st.session_state.clear()  # ✅ wipe all widget & variable states
                st.session_state.entries = copy.deepcopy(original)
                st.session_state.original_entries = copy.deepcopy(original)
                st.session_state.current_idx = 0
                st.success("✅ Original data reloaded.")
                st.rerun()
            else:
                st.warning("No original data found to restore.")
else:
    st.info("Upload a .jsonl file to begin annotation.")