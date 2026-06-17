"""
Streamlit UI for TraceMind - Modern Dark Clinical Edition.
Cleanly refactored with brand elements matching logo.jpeg.

Run:
  streamlit run tracemind/streamlit_ui.py
"""

from __future__ import annotations

import re
import sys
import base64
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import networkx as nx

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from source.orchestration.graph import run_turn
    from source.agents.explanation import _RULE_META
    from source.state import CareTraceState, default_case
except ImportError:
    # High-fidelity clinical mockups for local development/testing fallback
    def run_turn(state):
        state["turn"] = state.get("turn", 0) + 1
        state["assistant_reply"] = (
            "🚨 EMERGENCY DEPARTMENT — GO NOW.\n\n"
            "**Key positives/concerns:**\n"
            "- I'm weighing reduced responsiveness, breathing, hydration, and urine output as hard safety signals\n"
            "- Local outbreak context (if mentioned) can raise suspicion for viral illness but does not override these gates.\n\n"
            "**What to do now:**\n"
            "- Go to the ER now; do not wait overnight.\n"
            "- Bring temperature log, medication list, and recent fluid intake notes if possible.\n\n"
            "**Disclaimer:** THIS IS NOT A DIAGNOSIS; IT IS AN ESCALATION BASED ON RISK THRESHOLDS."
        )
        state["decision"] = {
            "disposition": "ER_NOW",
            "rule_ids": ["PED-FEV-VOM-2.1", "MED-ABX-INT-1.4"],
            "med_flags": ["Amoxicillin active course noted."],
            "missing_required": []
        }
        state["kg_annotations"] = [
            {
                "concept": {"id": "C0015967", "term": "Fever"},
                "mention": "fever",
                "ancestors": [{"id": "C0123456", "term": "Body Temperature Changes"}]
            },
            {
                "concept": {"id": "C0042963", "term": "Vomiting"},
                "mention": "vomited",
                "ancestors": [{"id": "C0018991", "term": "Gastrointestinal Symptoms"}]
            }
        ]
        return state

    _RULE_META = {
        "PED-FEV-VOM-2.1": ("Fever + Emesis hydration check", "Age 6 with fever >= 101°F and vomiting triggers mandatory fluid-intake and urine-output assessment.", "Pediatric CPG Guideline Sec. 4"),
        "MED-ABX-INT-1.4": ("Active antibiotic course noted", "Amoxicillin for otitis media — flag for medication-related GI side effects vs. progressing illness.", "Clinical Pharmaceutics Advisory")
    }
    
    class CareTraceState(dict):
        pass

    def default_case():
        return {}

SAMPLE_SCENARIOS = {
    "HOME_MANAGEMENT": {
        "title": "Home Care",
        "badge": "HOME MANAGEMENT",
        "description": "Moderate fever, mild symptoms — manageable at home.",
        "turns": [
            "My 6-year-old has a fever, threw up once, and looks really wiped out.",
            "Temp is 101.8. He's tired but answers me. No breathing issues. He's sipping water, not much though. He's been on medication for a recent ear infection.",
            "He's on amoxicillin. Last dose was earlier tonight. Just vomited once. He peed earlier this evening."
        ]
    },
    "URGENT_SAME_DAY": {
        "title": "Urgent Same-Day",
        "badge": "URGENT SAME-DAY",
        "description": "Persistent vomiting, low fluid intake — needs same-day care.",
        "turns": [
            "5 year old fever and vomiting",
            "He vomited 4 times in the last 2 hours and only sips",
            "102.5 fever, breathing fine, answers questions, he keeps throwing up and won't drink much, he peed an hour ago"
        ]
    },
    "ER_NOW": {
        "title": "ER Now",
        "badge": "EMERGENCY NOW",
        "description": "Lethargy, dehydration risk — go to ER immediately.",
        "turns": [
            "My 6-year-old has a fever, threw up, and looks really wiped out. I'm worried.",
            "Temp is 103.5. He's barely responding, just lying there. He doesn't want to drink. No trouble breathing. Also, there's been a stomach virus going around his school this week.",
            "I don't think he's peed since this afternoon."
        ]
    }
}


def _apply_custom_css() -> None:
    """Inject styling sheet defined at the bottom of the file."""
    st.markdown(f"<style>{CLINICAL_DARK_THEME_CSS}</style>", unsafe_allow_html=True)


@st.dialog("📋 Copy Preset Turns", width="large")
def _show_sample_modal(scenario_key: str) -> None:
    """Display modal with turns list in premium dark layout."""
    scenario = SAMPLE_SCENARIOS[scenario_key]

    st.markdown(f"### {scenario['title']}")
    st.caption(scenario["description"])
    st.divider()

    for index, turn in enumerate(scenario["turns"], start=1):
        st.markdown(f"**Turn {index}:**")
        st.code(turn, language=None)

    st.divider()
    st.markdown("**All turns combined**")
    combined_text = " ".join(scenario["turns"])
    st.text_area(
        "Copy this text into the chat input below:",
        value=combined_text,
        height=120,
        key=f"sample_combined_{scenario_key}",
        label_visibility="visible",
    )

    if st.button("Close Preset View", key=f"close_sample_modal_{scenario_key}"):
        st.session_state.show_sample_modal = None
        st.rerun()


def _init_state() -> CareTraceState:
    return {
        "messages": [],
        "case": default_case(),
        "kg_annotations": [],
        "turn": 0,
    }


def _reset() -> None:
    st.session_state.ct_state = _init_state()
    st.session_state.ct_chat = []


def _get_disposition_emoji(disposition: str) -> str:
    """Return emoji based on disposition."""
    emoji_map = {
        "ER_NOW": "🚨",
        "URGENT_SAME_DAY": "⚠️",
        "HOME_MANAGEMENT": "🏠",
        "OUT_OF_SCOPE": "❓",
    }
    return emoji_map.get(disposition, "❓")


_REASONING_SECTION_RE = re.compile(
    r"\*\*Why \(rule trace\):\*\*\s*[^\n]*(?:\n(?!\n|\*\*)[^\n]*)*",
    re.IGNORECASE,
)


def _strip_reasoning_from_reply(text: str) -> str:
    """Remove the inline rule-trace block; shown separately as Reasoning."""
    stripped = _REASONING_SECTION_RE.sub("", text, count=1).strip()
    return re.sub(r"\n{3,}", "\n\n", stripped)


def _normalize_markdown_lists(text: str) -> str:
    """Convert bullet glyphs and spacing so Streamlit renders lists correctly."""
    lines = text.splitlines()
    normalized: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("•"):
            bullet_line = f"- {stripped[1:].strip()}"
            if normalized and normalized[-1].strip() and not normalized[-1].lstrip().startswith("- "):
                normalized.append("")
            normalized.append(bullet_line)
            continue

        if stripped.startswith("**") and stripped.endswith("**") and not stripped.endswith(":**"):
            if normalized and normalized[-1].strip():
                normalized.append("")
            normalized.append(stripped)
            normalized.append("")
            continue

        if stripped.endswith(":**"):
            if normalized and normalized[-1].strip():
                normalized.append("")
            normalized.append(stripped)
            continue

        if stripped.startswith("-"):
            normalized.append(line)
            continue

        normalized.append(line)

    return "\n".join(normalized).strip()


def _get_logo_html() -> str:
    """Read logo image from local filesystem with dark-theme blend filters."""
    pkg_dir = Path(__file__).resolve().parent
    project_dir = pkg_dir.parent
    search_paths = [
        project_dir / "images" / "logo.png",
        pkg_dir / "images" / "logo.png",
        Path("tracemind/images/logo.png"),        
        Path("logo.jpg"),
    ]
    
    for img_path in search_paths:
        if img_path.exists():
            try:
                with open(img_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                # mix-blend-mode: screen hides black pixels. Inverting (1) turns the white image box black 
                # (disappearing). hue-rotate(180deg) shifts the inverted colors back to brand teal/coral.
                # Pixel-perfect negative margins trim down the excess horizontal canvas padding built into the logo asset.
                return (
                    f'<img class="sidebar-brand-logo" src="data:image/png;base64,{encoded}" alt="TraceMind" />'
                )
            except Exception:
                pass
            
    # Premium Diagnostic Vector Fallback - Cognitive Clinical Mind representation
    return (
        '<svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-top: -2px;">'
        # Left Brain/Mind Hemisphere network (glowing cyan #00D2C4)
        '<path d="M48,20 C30,20 22,35 22,50 C22,68 35,80 48,80" stroke="#00D2C4" stroke-width="5" stroke-linecap="round" stroke-dasharray="2 3"/>'
        # Right Brain/Mind medical trace pulse (brand teal #0EAF9F)
        '<path d="M52,20 C70,20 78,35 78,50 L70,50 L66,35 L60,65 L54,45 L52,50" stroke="#0EAF9F" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>'
        # Neural connection center nodes
        '<circle cx="34" cy="38" r="4" fill="#00D2C4" stroke="#090D10" stroke-width="1.5"/>'
        '<circle cx="42" cy="62" r="4" fill="#00D2C4" stroke="#090D10" stroke-width="1.5"/>'
        '<circle cx="66" cy="35" r="4" fill="#0EAF9F" stroke="#090D10" stroke-width="1.5"/>'
        '<circle cx="60" cy="65" r="4" fill="#0EAF9F" stroke="#090D10" stroke-width="1.5"/>'
        '<line x1="34" y1="38" x2="42" y2="62" stroke="#00D2C4" stroke-width="1.5" stroke-opacity="0.6"/>'
        '<line x1="42" y1="62" x2="60" y2="65" stroke="#0EAF9F" stroke-width="1.5" stroke-opacity="0.4"/>'
        '</svg>'
    )


def _render_assistant_reply(assistant_text: str) -> None:
    """Render caregiver guidance inside a single styled block with a clinical robot avatar."""
    display_text = _normalize_markdown_lists(_strip_reasoning_from_reply(assistant_text))
    if not display_text:
        st.markdown("(no response)")
        return

    # Convert simple markdown bullet lists and bolding headers into structured HTML
    html_content = ""
    lines = display_text.splitlines()
    in_list = False

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue

        # Convert bold markers to HTML style blocks using brand teal
        line_str = re.sub(r"\*\*(.*?)\*\*", r"<strong style='color:#0EAF9F; font-weight:600;'>\1</strong>", line_str)

        if line_str.startswith("- ") or line_str.startswith("* "):
            if not in_list:
                html_content += "<ul style='margin-left: 1.25rem; margin-top: 0.25rem; margin-bottom: 0.75rem; color: #E2E8F0; list-style-type: disc;'>"
                in_list = True
            item_text = line_str[2:]
            html_content += f"<li style='margin-bottom: 0.35rem; font-size: 0.95rem; line-height: 1.5;'>{item_text}</li>"
        else:
            if in_list:
                html_content += "</ul>"
                in_list = False
            
            # Formulate text as headers if it ends with a colon or represents emphasis headers
            if line_str.endswith(":") or line_str.startswith("<strong style='color:#0EAF9F;"):
                html_content += f"<div style='color: #FFFFFF; font-weight: 600; font-size: 1rem; margin-top: 1rem; margin-bottom: 0.5rem;'>{line_str}</div>"
            else:
                html_content += f"<p style='color: #E2E8F0; font-size: 0.95rem; line-height: 1.5; margin-bottom: 0.75rem;'>{line_str}</p>"

    if in_list:
        html_content += "</ul>"

    # SVG medical diagnostic robot avatar
    robot_svg = (
        '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0EAF9F" stroke-width="2" style="margin-top: 2px; flex-shrink: 0;">'
        '<rect x="3" y="9" width="18" height="11" rx="2" fill="#13181E" stroke="#0EAF9F" stroke-width="2"/>'
        '<circle cx="8" cy="14" r="1.5" fill="#0EAF9F"/>'
        '<circle cx="16" cy="14" r="1.5" fill="#0EAF9F"/>'
        '<path d="M12 2v4M9 5h6" stroke-linecap="round"/>'
        '<path d="M2 13h1M21 13h1" stroke-linecap="round"/>'
        '<path d="M9 17h6" stroke-linecap="round" stroke-width="1.5"/>'
        '</svg>'
    )

    # Flatten HTML completely into a single line string to prevent Streamlit indent parsing issues
    bubble_html = (
        f'<div class="chat-row-assistant">'
        f'<div class="robot-avatar">{robot_svg}</div>'
        f'<div class="chat-bubble-assistant-new">{html_content}</div>'
        f'</div>'
    )
    
    clean_bubble_html = re.sub(r'\s+', ' ', bubble_html).strip()
    st.markdown(clean_bubble_html, unsafe_allow_html=True)


def _render_radial_indicator(missing_count: int) -> str:
    """Generate inline SVG for a progress wheel tracking triage fields."""
    total_fields = 5
    completed = max(0, total_fields - missing_count)
    percent = int((completed / total_fields) * 100)
    
    radius = 24
    circumference = 2 * 3.14159 * radius
    stroke_dashoffset = circumference - (percent / 100) * circumference
    
    color_map = {
        0: "#FF5252",      # Warning Red
        20: "#E76F51",     # Coral Orange Brand
        40: "#E76F51",
        60: "#0EAF9F",     # Clinical Teal Brand
        80: "#2ED573"      # Confident green
    }
    
    color = "#E76F51"
    for threshold, hex_color in color_map.items():
        if percent >= threshold:
            color = hex_color

    svg = f'<svg width="64" height="64" viewBox="0 0 64 64" style="transform: rotate(-90deg);"><circle cx="32" cy="32" r="{radius}" fill="transparent" stroke="#1C2430" stroke-width="5" /><circle cx="32" cy="32" r="{radius}" fill="transparent" stroke="{color}" stroke-width="5" stroke-dasharray="{circumference}" stroke-dashoffset="{stroke_dashoffset}" stroke-linecap="round" /></svg>'
    
    pending_text = f"{missing_count} required variables pending." if missing_count > 0 else "Intake complete. Confident plan available."
    html_wrapper = (
        f'<div class="progress-radial-wrapper">'
        f'<div>{svg}</div>'
        f'<div>'
        f'<div style="font-size: 1.1rem; font-weight: 700; color: #FFFFFF; line-height: 1.1;">{percent}%</div>'
        f'<div style="font-size: 0.75rem; font-weight: 500; color: #8A99AD; margin-top: 2px;">{pending_text}</div>'
        f'</div>'
        f'</div>'
    )
    return re.sub(r'\s+', ' ', html_wrapper).strip()


def _create_kg_graph(kg_annotations: list) -> go.Figure:
    """Create network graph visualization customized to match the dark clinical theme."""
    G = nx.DiGraph()

    if not kg_annotations:
        return go.Figure()

    for ann in kg_annotations:
        concept = ann.get("concept", {})
        mention = ann.get("mention", "")
        ancestors = ann.get("ancestors", [])

        concept_id = concept.get("id") or concept.get("conceptId") or ""
        concept_name = concept.get("term") or concept.get("pt") or "Unknown"

        if mention:
            mention_node = f"Text: {mention}"
            G.add_node(mention_node, type="mention", color="#E76F51")

        concept_node = f"{concept_name}\n({concept_id})" if concept_id else concept_name
        G.add_node(concept_node, type="concept", color="#0EAF9F")

        if mention:
            G.add_edge(mention_node, concept_node)

        for ancestor in ancestors:
            anc_id = ancestor.get("id") or ancestor.get("conceptId") or ""
            anc_name = ancestor.get("term") or ancestor.get("pt") or "Unknown"
            ancestor_node = f"{anc_name}\n({anc_id})" if anc_id else anc_name

            G.add_node(ancestor_node, type="ancestor", color="#2ED573")
            G.add_edge(concept_node, ancestor_node)

    try:
        roots = [n for n in G.nodes() if G.in_degree(n) == 0]
        if not roots:
            roots = [next(iter(G.nodes()))] if G.nodes() else []

        pos = {}
        y_level = 0
        processed = set()
        current_level = roots

        while current_level and len(processed) < len(G.nodes()):
            x_positions = {n: x for x, n in enumerate(current_level)}
            for node in current_level:
                x = x_positions[node] * 1.5 - len(current_level) * 0.75
                pos[node] = (x, -y_level)
                processed.add(node)

            next_level = []
            for node in current_level:
                children = list(G.successors(node))
                for child in children:
                    if child not in processed and child not in next_level:
                        next_level.append(child)

            current_level = next_level
            y_level += 1

        for node in G.nodes():
            if node not in pos:
                pos[node] = (0, y_level)
    except Exception:
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    edge_traces = []
    for edge in G.edges():
        if edge[0] in pos and edge[1] in pos:
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]

            edge_trace = go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode='lines',
                line=dict(width=1.5, color='#233144'),
                hoverinfo='none',
                showlegend=False
            )
            edge_traces.append(edge_trace)

    node_x, node_y, node_colors, node_sizes, node_text = [], [], [], [], []
    depths = {}
    for node in G.nodes():
        if G.in_degree(node) == 0:
            depths[node] = 0
        else:
            parents = list(G.predecessors(node))
            max_parent_depth = max(depths.get(parent, 0) for parent in parents) if parents else 0
            depths[node] = max_parent_depth + 1

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_data = G.nodes[node]
        node_colors.append(node_data.get('color', '#0EAF9F'))
        depth = depths.get(node, 0)
        node_sizes.append(max(15, 24 - (depth * 3)))
        node_text.append(node)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        hoverinfo='text',
        textfont=dict(color='#E2E8F0', size=10),
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=1, color='#090D10')
        ),
        showlegend=False
    )

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        showlegend=False,
        hovermode='closest',
        margin=dict(b=10, l=5, r=5, t=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='#12181F',
        paper_bgcolor='#12181F',
        height=320,
    )

    return fig


def _latest_turn_state() -> CareTraceState | None:
    if st.session_state.ct_chat:
        return st.session_state.ct_chat[-1].get("state") or st.session_state.ct_state
    return st.session_state.ct_state if st.session_state.ct_state.get("decision") else None


def main() -> None:
    st.set_page_config(page_title="TraceMind - Pediatric Triage Console", page_icon="🩺", layout="wide")

    # Inject modern separated dark-theme stylesheet
    _apply_custom_css()

    # Session Initialization
    if "ct_state" not in st.session_state:
        st.session_state.ct_state = _init_state()
    if "ct_chat" not in st.session_state:
        st.session_state.ct_chat = []
    if "show_sample_modal" not in st.session_state:
        st.session_state.show_sample_modal = None

    with st.sidebar:
        logo_html = _get_logo_html()
        sidebar_brand_html = (
            '<div class="sidebar-brand-container">'
            f'<div class="sidebar-brand-icon">{logo_html}</div>'
            '<div class="sidebar-brand-text">'
            '<div class="sidebar-brand-title">TraceMind</div>'
            '<div class="sidebar-brand-subtitle">Pediatric Triage</div>'
            '</div>'
            '</div>'
        )
        st.markdown(re.sub(r'\s+', ' ', sidebar_brand_html).strip(), unsafe_allow_html=True)
        
        st.divider()
        st.markdown('<div class="scenario-section-header">Sample Scenarios</div>', unsafe_allow_html=True)

        for key, details in SAMPLE_SCENARIOS.items():
            card_html = f"""
            <div style="font-size: 0.85rem; font-weight: 700; color: #FFFFFF; display: flex; align-items: center; gap: 6px;">
                <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background-color:{'#2ED573' if key=='HOME_MANAGEMENT' else ('#E76F51' if key=='URGENT_SAME_DAY' else '#FF5252')};"></span>
                {details['title']}
            </div>
            <div style="font-size: 0.75rem; color: #8A99AD; margin-top: 4px; white-space: normal;">
                {details['description']}
            </div>
            """
            
            if st.button(details["title"], key=f"btn_scen_{key}", help="Copy clinical prompt scenario"):
                st.session_state.show_sample_modal = key
                st.rerun()

        st.divider()
        if st.button("🔄 Reset Live Triage Session", width='stretch'):
            _reset()
            st.rerun()

        st.divider()
        st.markdown("""
        <div style="background-color: #12181F; border: 1px solid #1C2430; border-radius: 8px; padding: 10px; font-size: 0.75rem; color: #8A99AD;">
            <strong>Neurosymbolic Graph-RAG</strong> clinical decision helper.<br><br>
            Grounds symptoms into pediatric clinical pathways.
        </div>
        """, unsafe_allow_html=True)

        disclaimer_html = (
            '<div style="background-color: #E11D48; border: 1.5px solid #FFFFFF; border-radius: 8px; padding: 12px; margin-top: 1rem; color: #FFFFFF; box-shadow: 0 4px 14px rgba(225, 29, 72, 0.4);">'
            '<div style="font-size: 0.8rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px; margin-bottom: 4px; color: #FFFFFF;">'
            '⚠️ CLINICAL DISCLAIMER'
            '</div>'
            '<p style="font-size: 0.72rem; color: #FFFFFF; margin: 0; line-height: 1.4; font-weight: 600;">'
            '<strong>NOT A MEDICAL DIAGNOSIS.</strong> TraceMind is an automated triage tool providing safety guidelines. Always seek direct clinical evaluation for severe or life-threatening pediatric events.'
            '</p>'
            '</div>'
        )
        st.markdown(re.sub(r'\s+', ' ', disclaimer_html).strip(), unsafe_allow_html=True)

    # Active Session Tracking
    active_state = _latest_turn_state()
    decision = active_state.get("decision") if active_state else {}
    disposition = decision.get("disposition", "UNKNOWN") if decision else "UNKNOWN"
    missing_required = decision.get("missing_required", []) if decision else []

    # Chat Pipeline and Audit Console split
    chat_col, right_panel = st.columns([13, 10], gap="large")

    with chat_col:
        header_html = (
            '<div class="live-triage-header-bar">'
            '<div class="live-pulse-container">'
            '<div class="live-pulse-dot"></div>'
            'TRIAGE SESSION &bull; LIVE'
            '</div>'
            '<div style="font-size: 0.8rem; color: #8A99AD; font-weight: 500;">'
            'Patient ID: TM-883-PED'
            '</div>'
            '</div>'
        )
        st.markdown(header_html, unsafe_allow_html=True)

        if st.session_state.show_sample_modal:
            _show_sample_modal(st.session_state.show_sample_modal)

        # Independent Scroll Container: Restricts height and creates customized low-profile scroll bars
        chat_scroll_container = st.container(height=580, border=False)
        
        with chat_scroll_container:
            if not st.session_state.ct_chat:
                st.markdown("""
                <div style="text-align: center; padding: 3rem 1rem; color: #56667A;">
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#233144" stroke-width="2" style="margin-bottom: 12px;">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                    <div style="font-weight: 600; color: #8A99AD; font-size: 0.95rem;">Awaiting Symptom Intake</div>
                    <div style="font-size: 0.8rem; margin-top: 4px;">Submit child details or copy a Preset Scenario to begin.</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                for index, turn in enumerate(st.session_state.ct_chat):
                    st.markdown(f"""
                    <div style="text-align: right; width: 100%;">
                        <div class="chat-bubble-user">{turn["user"]}</div>
                        <div class="chat-bubble-meta">Caregiver &bull; Turn {index+1}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    with st.container():
                        _render_assistant_reply(turn["assistant"])
                        st.markdown(f"""<div class="chat-bubble-meta">TraceMind System &bull; Active</div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        user_text = st.chat_input("Describe symptoms (temperature, hydration, behavior, breathing)...")

        if user_text:
            st.session_state.show_sample_modal = None
            
            state: CareTraceState = st.session_state.ct_state
            state["raw_user_text"] = user_text
            msgs = list(state.get("messages") or [])
            msgs.append({"role": "user", "content": user_text})
            state["messages"] = msgs

            with st.spinner("Analyzing against clinical pathways..."):
                new_state = run_turn(state)

            assistant_text = new_state.get("assistant_reply") or "(no response)"

            st.session_state.ct_state = new_state
            st.session_state.ct_chat.append(
                {
                    "user": user_text,
                    "assistant": assistant_text,
                    "state": new_state,
                }
            )
            st.rerun()

    with right_panel:
        st.markdown('<div class="sticky-panel">', unsafe_allow_html=True)
        
        st.markdown('<div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: #56667A; font-weight: 700; margin-bottom: 0.25rem;">CURRENT DISPOSITION</div>', unsafe_allow_html=True)
        
        disp_colors = {
            "HOME_MANAGEMENT": ("#2ED573", "• HOME MANAGEMENT"),
            "URGENT_SAME_DAY": ("#E76F51", "• URGENT SAME-DAY"),
            "ER_NOW": ("#FF5252", "• EMERGENCY NOW"),
            "OUT_OF_SCOPE": ("#8A99AD", "• OUT OF SCOPE")
        }
        active_disp_meta = disp_colors.get(disposition, ("#0EAF9F", f"• {disposition}"))
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #FFFFFF;">
                {_get_disposition_emoji(disposition)} {disposition.replace('_', ' ')}
            </div>
            <div style="background-color: {active_disp_meta[0]}15; color: {active_disp_meta[0]}; border: 1px solid {active_disp_meta[0]}; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700;">
                {active_disp_meta[1]}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if active_state:
            st.markdown(_render_radial_indicator(len(missing_required)), unsafe_allow_html=True)
        else:
            st.markdown(_render_radial_indicator(5), unsafe_allow_html=True)

        st.markdown('<div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: #56667A; font-weight: 700; margin-top: 1.5rem; margin-bottom: 0.5rem;">TRACEMIND TRACEABILITY</div>', unsafe_allow_html=True)
        tab_rules, tab_kg, tab_med = st.tabs(["⚡ Rules Fired", "🧬 KG Evidence", "⚕️ Med Safety"])

        # Tab 1: Clinical Rules Engine Trace
        with tab_rules:
            if active_state:
                rule_ids = decision.get("rule_ids") or []
                if rule_ids:
                    for rule in rule_ids:
                        meta = _RULE_META.get(rule)
                        cls_map = {
                            "HOME_MANAGEMENT": "active-rule-home",
                            "URGENT_SAME_DAY": "active-rule-urgent",
                            "ER_NOW": "active-rule-er"
                        }
                        cls = cls_map.get(disposition, "")
                        
                        if meta:
                            label, condition, cpg_basis = meta
                            st.markdown(f"""
                            <div class="logic-trace-card {cls}">
                                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: {active_disp_meta[0]}; font-weight:600;">{rule} &mdash; {label}</div>
                                <div style="font-size: 0.8rem; color: #E2E8F0; margin-top: 6px;">{condition}</div>
                                <div style="font-size: 0.7rem; color: #56667A; margin-top: 6px; font-style: italic;">CPG Base: {cpg_basis}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="logic-trace-card {cls}">
                                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #0EAF9F;">{rule}</div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No active symbolic clinical rules fired for this turn.")
            else:
                st.info("Clinical logic pathways will list here.")

        # Tab 2: Graph-RAG Concept Extraction Engine
        with tab_kg:
            if active_state:
                kg_annotations = active_state.get("kg_annotations") or []
                if kg_annotations:
                    fig = _create_kg_graph(kg_annotations)
                    st.plotly_chart(fig, width='stretch')

                    st.markdown("##### Extracted Clinical Term Relationships")
                    for ann in kg_annotations:
                        concept = ann.get("concept", {})
                        mention = ann.get("mention", "")
                        concept_id = concept.get("id") or concept.get("conceptId", "")
                        concept_name = concept.get("term") or concept.get("pt") or "Unknown"

                        st.markdown(f"""
                        <div style="background-color:#12181F; border: 1px solid #1C2430; padding:8px 12px; border-radius:6px; margin-bottom:6px; font-size:0.8rem;">
                            <strong style="color: #0EAF9F;">{concept_name}</strong> <span style="color:#56667A; font-size:0.7rem;">({concept_id})</span><br>
                            <span style="color:#8A99AD; font-size:0.75rem;">Source Mention: "{mention}"</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No Knowledge Graph records matched.")
            else:
                st.info("Entity linking visualizer outputs are generated once triage is underway.")

        # Tab 3: Pediatric Pharmacological Safety Check
        with tab_med:
            if active_state:
                med_flags = decision.get("med_flags") or []
                if med_flags:
                    for flag in med_flags:
                        st.markdown(f"""
                        <div style="background-color: #2D1A1C; border: 1px solid #FF5252; color: #FF5252; padding: 12px; border-radius: 8px; font-size: 0.8rem; font-weight: 500; display:flex; align-items:center; gap:8px;">
                            <span style="font-size:1.1rem;">⚠️</span> {flag}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("No critical medication safety alerts triggered.")
            else:
                st.info("Triage prescriptions are verified in real-time.")

        st.markdown('</div>', unsafe_allow_html=True)


CLINICAL_DARK_THEME_CSS = """
/* Theme Stylesheet for TraceMind Triage */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background-color: #090D10 !important;
    color: #E2E8F0 !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}

[data-testid="stSidebar"] {
    background-color: #0B0F13 !important;
    border-right: 1px solid #1A212A !important;
}

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
}

h1, h2, h3, h4, h5, h6 {
    color: #FFFFFF !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em;
}

.sidebar-brand-container {
    padding: 0.5rem 0 1rem;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 1rem;
}
.sidebar-brand-icon {
    flex: 0 0 76px;
    width: 76px;
    height: 76px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 0;
    background-color: transparent !important;
    border: none !important;
    padding: 0 !important;
}
.sidebar-brand-logo {
    height: 92px;
    width: auto;
    max-width: none;
    object-fit: contain;
    object-position: center;
    margin: 0 !important;
    display: block;
    mix-blend-mode: screen;
    filter: invert(1) hue-rotate(180deg) brightness(1.1) contrast(1.15);
    transform: scale(1.45);
    transform-origin: center center;
}
.sidebar-brand-text {
    flex: 1;
    min-width: 0;
}
.sidebar-brand-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #FFFFFF;
    line-height: 1.1;
    margin: 0;
}
.sidebar-brand-subtitle {
    font-size: 0.72rem;
    font-weight: 700;
    color: #0EAF9F;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin: 0;
}

.scenario-section-header {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #56667A;
    margin-bottom: 0.75rem;
    font-weight: 700;
}

/* Custom Sticky Right Column Layout */
.sticky-panel {
    position: -webkit-sticky;
    position: sticky;
    top: 1.5rem;
    max-height: calc(100vh - 3rem);
    overflow-y: auto;
    padding-right: 10px;
}
.sticky-panel::-webkit-scrollbar {
    width: 4px;
}
.sticky-panel::-webkit-scrollbar-track {
    background: transparent;
}
.sticky-panel::-webkit-scrollbar-thumb {
    background: #1C2430;
    border-radius: 10px;
}
.sticky-panel::-webkit-scrollbar-thumb:hover {
    background: #0EAF9F;
}

/* Custom premium grey-slate buttons in sidebar with blue-glow border highlights */
[data-testid="stSidebar"] div.stButton > button {
    background-color: #111823 !important;
    color: #E2E8F0 !important;
    border: 1px solid #1E2D4A !important;
    border-radius: 8px !important;
    padding: 0.75rem 1rem !important;
    width: 100% !important;
    text-align: left !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    display: block !important;
    margin-bottom: 0.75rem !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
}

[data-testid="stSidebar"] div.stButton > button:hover {
    background-color: #172237 !important;
    color: #FFFFFF !important;
    border-color: #0EAF9F !important;
    transform: translateY(-1px);
    box-shadow: 0 0 12px rgba(14, 175, 159, 0.25) !important;
}

/* Standard structural widgets fallback values */
div.stButton > button {
    background-color: #12181F;
    color: #E2E8F0;
    border: 1px solid #1A222D;
    border-radius: 10px;
    padding: 0.5rem 1rem;
}

.custom-card-container {
    background-color: #12181F;
    border: 1px solid #1C2430;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}

.live-triage-header-bar {
    background-color: #10161D;
    border: 1px solid #1B232E;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
}
.live-pulse-container {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    color: #2ED573;
}
.live-pulse-dot {
    width: 8px;
    height: 8px;
    background-color: #2ED573;
    border-radius: 50%;
    box-shadow: 0 0 0 0 rgba(46, 213, 115, 0.7);
    animation: pulse 1.6s infinite;
}

/* Chat bubble styling */
.chat-bubble-user {
    background-color: #18222E;
    color: #E2E8F0;
    border: 1px solid #233144;
    border-radius: 16px 16px 0px 16px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.4rem;
    text-align: left;
    display: inline-block;
    max-width: 85%;
}

/* Unified clean robotic response design style block */
.chat-row-assistant {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
}
.robot-avatar {
    width: 36px;
    height: 36px;
    background-color: #13181E;
    border: 1px solid #0EAF9F;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 0 8px rgba(14, 175, 159, 0.15);
}
.chat-bubble-assistant-new {
    background-color: #12181E;
    border: 1px solid #1C2430;
    border-radius: 4px 16px 16px 16px;
    padding: 1.25rem;
    flex-grow: 1;
    max-width: 90%;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.chat-bubble-meta {
    font-size: 0.7rem;
    color: #56667A;
    margin-bottom: 1.25rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.logic-trace-card {
    background-color: #12181F;
    border-left: 4px solid #56667A;
    border-top: 1px solid #1C2430;
    border-right: 1px solid #1C2430;
    border-bottom: 1px solid #1C2430;
    border-radius: 0 8px 8px 0;
    padding: 1rem;
    margin-bottom: 0.75rem;
}
.logic-trace-card.active-rule-home {
    border-left-color: #2ED573 !important;
}
.logic-trace-card.active-rule-urgent {
    border-left-color: #E76F51 !important;
}
.logic-trace-card.active-rule-er {
    border-left-color: #FF5252 !important;
}

.progress-radial-wrapper {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    padding: 1rem;
    background-color: #12181F;
    border: 1px solid #1C2430;
    border-radius: 12px;
    margin-bottom: 1.25rem;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Highlight Tab labels clearly inside dark panels */
div[data-testid="stTabBar"] button p {
    color: #94A3B8 !important; /* Brighter cool silver text */
    font-weight: 600 !important;
}
div[data-testid="stTabBar"] button[aria-selected="true"] p {
    color: #0EAF9F !important; /* Active selected tab is glowing brand teal */
    font-weight: 700 !important;
}

/* Custom Scrollbar Styles for scrollable middle container */
div[data-testid="stVContainer"] {
    scrollbar-width: thin !important;
    scrollbar-color: #1C2430 transparent !important;
}
div[data-testid="stVContainer"]::-webkit-scrollbar {
    width: 6px !important;
    height: 6px !important;
}
div[data-testid="stVContainer"]::-webkit-scrollbar-track {
    background: transparent !important;
}
div[data-testid="stVContainer"]::-webkit-scrollbar-thumb {
    background-color: #1C2430 !important;
    border-radius: 10px !important;
}
div[data-testid="stVContainer"]::-webkit-scrollbar-thumb:hover {
    background-color: #0EAF9F !important;
}

@keyframes pulse {
    0% {
        transform: scale(0.95);
        box-shadow: 0 0 0 0 rgba(46, 213, 115, 0.7);
    }
    70% {
        transform: scale(1);
        box-shadow: 0 0 0 6px rgba(46, 213, 115, 0);
    }
    100% {
        transform: scale(0.95);
        box-shadow: 0 0 0 0 rgba(46, 213, 115, 0);
    }
}
"""

if __name__ == "__main__":
    main()