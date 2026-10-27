
import itertools
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Digital Logic Agent",
    page_icon="🔌",
    layout="wide",
)

CIRCUITS = {
    "4-to-1 MUX": "MUX",
    "1-to-4 DEMUX": "DEMUX",
    "4-to-2 Encoder": "ENCODER",
    "2-to-4 Decoder": "DECODER",
}

st.title("🔌 Agentic AI-Based Digital Logic Circuit Tester")
st.caption(
    "Intelligent fault diagnosis • Truth tables • Test generation "
    "• No API key required"
)

st.info(
    "Simulation mode: expected outputs are calculated in Python. "
    "When actual outputs are not supplied, results are labelled "
    "SIMULATED FUNCTIONAL TEST, not a physical hardware test."
)


# ============================================================
# DIGITAL LOGIC FUNCTIONS
# ============================================================

def bit(value: int) -> int:
    """Validate and return a binary bit."""
    if value not in (0, 1):
        raise ValueError("Every digital input must be either 0 or 1.")
    return value


def mux(d: List[int], s1: int, s0: int) -> int:
    """4-to-1 multiplexer."""
    if len(d) != 4:
        raise ValueError("A 4-to-1 MUX requires exactly four data inputs.")
    d = [bit(x) for x in d]
    s1, s0 = bit(s1), bit(s0)
    return d[2 * s1 + s0]


def demux(data: int, s1: int, s0: int) -> List[int]:
    """1-to-4 demultiplexer."""
    data, s1, s0 = bit(data), bit(s1), bit(s0)
    result = [0, 0, 0, 0]
    result[2 * s1 + s0] = data
    return result


def encoder(inputs: List[int]) -> List[int]:
    """
    4-to-2 active-high encoder.
    Exactly one input must be HIGH (one-hot).
    """
    if len(inputs) != 4:
        raise ValueError("A 4-to-2 encoder requires four input bits.")

    inputs = [bit(x) for x in inputs]

    if sum(inputs) != 1:
        raise ValueError(
            "A basic 4-to-2 encoder requires exactly one HIGH input. "
            "Use one-hot inputs such as 0001, 0010, 0100, or 1000."
        )

    index = inputs.index(1)
    return [(index >> 1) & 1, index & 1]


def decoder(a1: int, a0: int) -> List[int]:
    """2-to-4 active-high decoder."""
    a1, a0 = bit(a1), bit(a0)
    result = [0, 0, 0, 0]
    result[2 * a1 + a0] = 1
    return result


def expected_output(circuit: str, inputs: Dict) -> Dict:
    """Calculate a deterministic expected output."""
    if circuit == "MUX":
        return {"Y": mux(inputs["D"], inputs["S1"], inputs["S0"])}
    if circuit == "DEMUX":
        return {
            f"Y{i}": value
            for i, value in enumerate(
                demux(inputs["DATA"], inputs["S1"], inputs["S0"])
            )
        }
    if circuit == "ENCODER":
        result = encoder(inputs["I"])
        return {"Y1": result[0], "Y0": result[1]}
    if circuit == "DECODER":
        return {
            f"Y{i}": value
            for i, value in enumerate(decoder(inputs["A1"], inputs["A0"]))
        }
    raise ValueError("Unknown circuit selected.")


def all_test_cases(circuit: str) -> List[Dict]:
    """Create valid exhaustive test cases for a circuit."""
    cases = []

    if circuit == "MUX":
        for d in itertools.product((0, 1), repeat=4):
            for s1, s0 in itertools.product((0, 1), repeat=2):
                cases.append({
                    "D": list(d), "S1": s1, "S0": s0
                })

    elif circuit == "DEMUX":
        for data, s1, s0 in itertools.product((0, 1), repeat=3):
            cases.append({"DATA": data, "S1": s1, "S0": s0})

    elif circuit == "ENCODER":
        for index in range(4):
            values = [0, 0, 0, 0]
            values[index] = 1
            cases.append({"I": values})

    elif circuit == "DECODER":
        for a1, a0 in itertools.product((0, 1), repeat=2):
            cases.append({"A1": a1, "A0": a0})

    return cases


def input_text(inputs: Dict) -> str:
    """Format inputs for display."""
    parts = []
    for name, value in inputs.items():
        parts.append(
            f"{name}={''.join(map(str, value)) if isinstance(value, list) else value}"
        )
    return ", ".join(parts)


def output_text(outputs: Dict) -> str:
    return ", ".join(f"{key}={value}" for key, value in outputs.items())


def diagnose(
    circuit: str,
    inputs: Dict,
    expected: Dict,
    actual: Dict,
) -> List[str]:
    """Suggest possible causes; these are not confirmed physical faults."""
    issues = []

    if not actual:
        return [
            "No actual output was supplied, so a hardware fault cannot be "
            "confirmed. The expected output was calculated by simulation."
        ]

    mismatches = [
        name for name, value in expected.items()
        if actual.get(name) != value
    ]

    if not mismatches:
        return ["No output mismatch was found for this test case."]

    issues.append(
        "Output mismatch detected at: " + ", ".join(mismatches) + "."
    )

    if circuit == "MUX":
        issues.append(
            "Check S1/S0 wiring and select-bit order. Verify the selected "
            "data input and inspect the output connection."
        )
        if inputs["D"][2 * inputs["S1"] + inputs["S0"]] != expected["Y"]:
            issues.append("Review the MUX input mapping and selection logic.")

    elif circuit == "DEMUX":
        issues.append(
            "Check the select lines, data input, output pin mapping, "
            "and whether inactive outputs are LOW."
        )

    elif circuit == "ENCODER":
        issues.append(
            "Check that exactly one input is HIGH and verify the encoder "
            "output bit order (Y1, Y0)."
        )

    elif circuit == "DECODER":
        issues.append(
            "Check the address-bit order (A1, A0), output mapping, "
            "and active-HIGH/active-LOW convention."
        )

    issues.append(
        "If using real hardware, also check the power supply, common ground, "
        "loose wires, IC pinout, and measurement method."
    )
    issues.append(
        "These are possible causes only. One test case cannot identify "
        "the exact physical fault."
    )
    return issues


# ============================================================
# PROMPT INTERPRETATION
# ============================================================

def parse_prompt(prompt: str) -> Tuple[Optional[str], Dict, Optional[str]]:
    """
    Interpret simple natural-language requests without an LLM.
    Supports MUX, DEMUX, encoder, decoder, and named binary inputs.
    """
    text = prompt.upper()

    aliases = [
        (r"\bMUX\b|\bMULTIPLEXER\b", "MUX"),
        (r"\bDEMUX\b|\bDEMULTIPLEXER\b", "DEMUX"),
        (r"\bENCODER\b", "ENCODER"),
        (r"\bDECODER\b", "DECODER"),
    ]

    circuit = None
    for pattern, name in aliases:
        if re.search(pattern, text):
            circuit = name
            break

    if circuit is None:
        return None, {}, (
            "I couldn't identify the circuit. Mention MUX, DEMUX, "
            "encoder, or decoder."
        )

    found = {}
    for name, value in re.findall(
        r"\b(D0|D1|D2|D3|S1|S0|DATA|A1|A0|I0|I1|I2|I3|Y0|Y1|Y2|Y3|Y)\s*=\s*([01])\b",
        text,
    ):
        found[name] = int(value)

    try:
        if circuit == "MUX":
            required = ["D0", "D1", "D2", "D3", "S1", "S0"]
            missing = [x for x in required if x not in found]
            if missing:
                return circuit, {}, "Missing inputs: " + ", ".join(missing)
            inputs = {
                "D": [found[f"D{i}"] for i in range(4)],
                "S1": found["S1"], "S0": found["S0"],
            }

        elif circuit == "DEMUX":
            required = ["DATA", "S1", "S0"]
            missing = [x for x in required if x not in found]
            if missing:
                return circuit, {}, "Missing inputs: " + ", ".join(missing)
            inputs = {x: found[x] for x in required}

        elif circuit == "ENCODER":
            required = ["I0", "I1", "I2", "I3"]
            missing = [x for x in required if x not in found]
            if missing:
                return circuit, {}, "Missing inputs: " + ", ".join(missing)
            inputs = {"I": [found[x] for x in required]}

        else:
            required = ["A1", "A0"]
            missing = [x for x in required if x not in found]
            if missing:
                return circuit, {}, "Missing inputs: " + ", ".join(missing)
            inputs = {x: found[x] for x in required}

        return circuit, inputs, None

    except (KeyError, ValueError) as exc:
        return circuit, {}, f"Input error: {exc}"


def actual_output_controls(expected: Dict, prefix: str) -> Dict:
    """Show optional actual-output controls and return supplied values."""
    supplied = {}
    for name, exp in expected.items():
        use_actual = st.checkbox(
            f"Provide actual {name}", key=f"{prefix}_use_{name}"
        )
        if use_actual:
            supplied[name] = st.selectbox(
                f"Actual {name} (0 or 1)",
                [0, 1],
                index=exp,
                key=f"{prefix}_actual_{name}",
            )
    return supplied


# ============================================================
# SIDEBAR AND INPUT CONTROLS
# ============================================================

with st.sidebar:
    st.header("Circuit selection")
    selected_label = st.selectbox("Choose a circuit", list(CIRCUITS.keys()))
    selected_circuit = CIRCUITS[selected_label]

    st.divider()
    st.subheader("How this app works")
    st.write("1. Select a circuit.")
    st.write("2. Set binary inputs or enter a prompt.")
    st.write("3. Calculate expected outputs.")
    st.write("4. Optionally enter actual outputs.")
    st.write("5. Review test status and possible diagnoses.")

tab_manual, tab_prompt, tab_exhaustive, tab_theory = st.tabs(
    ["Manual Test", "Prompt Agent", "Exhaustive Tests", "Theory & Truth Table"]
)


# ============================================================
# MANUAL TEST
# ============================================================

with tab_manual:
    st.subheader(f"Manual test: {selected_label}")

    inputs = {}

    if selected_circuit == "MUX":
        cols = st.columns(4)
        d = [
            cols[i].selectbox(f"D{i}", [0, 1], key=f"mux_d{i}")
            for i in range(4)
        ]
        c1, c2 = st.columns(2)
        s1 = c1.selectbox("S1", [0, 1], key="mux_s1")
        s0 = c2.selectbox("S0", [0, 1], key="mux_s0")
        inputs = {"D": d, "S1": s1, "S0": s0}

    elif selected_circuit == "DEMUX":
        c1, c2, c3 = st.columns(3)
        data = c1.selectbox("DATA", [0, 1], key="demux_data")
        s1 = c2.selectbox("S1", [0, 1], key="demux_s1")
        s0 = c3.selectbox("S0", [0, 1], key="demux_s0")
        inputs = {"DATA": data, "S1": s1, "S0": s0}

    elif selected_circuit == "ENCODER":
        st.caption("Basic encoder: exactly one input must be HIGH.")
        cols = st.columns(4)
        values = [
            cols[i].selectbox(f"I{i}", [0, 1], index=1 if i == 0 else 0,
                              key=f"enc_i{i}")
            for i in range(4)
        ]
        inputs = {"I": values}

    else:
        c1, c2 = st.columns(2)
        a1 = c1.selectbox("A1", [0, 1], key="dec_a1")
        a0 = c2.selectbox("A0", [0, 1], key="dec_a0")
        inputs = {"A1": a1, "A0": a0}

    if st.button("Calculate Expected Output", type="primary", key="manual_run"):
        try:
            result = expected_output(selected_circuit, inputs)
            st.session_state["manual_result"] = {
                "circuit": selected_circuit,
                "inputs": inputs,
                "expected": result,
            }
            st.success("Expected outputs calculated successfully.")
        except ValueError as exc:
            st.error(str(exc))
            st.session_state.pop("manual_result", None)

    saved = st.session_state.get("manual_result")
    if saved and saved["circuit"] == selected_circuit:
        st.markdown("#### Test result")
        st.write("**Inputs:**", input_text(saved["inputs"]))
        st.write("**Expected output:**", output_text(saved["expected"]))

        actual = actual_output_controls(saved["expected"], "manual")

        if st.button("Evaluate Test", key="manual_evaluate"):
            expected = saved["expected"]
            if not actual:
                st.warning(
                    "SIMULATED FUNCTIONAL TEST — PASS. "
                    "The expected result was calculated in Python; "
                    "no actual output was supplied."
                )
                st.session_state["manual_eval"] = {
                    "actual": {}, "pass": None,
                    "circuit": selected_circuit,
                }
            else:
                passed = all(
                    actual.get(k) == v for k, v in expected.items()
                    if k in actual
                ) and all(k in actual for k in expected)

                st.session_state["manual_eval"] = {
                    "actual": actual,
                    "pass": passed,
                    "circuit": selected_circuit,
                }
                if passed:
                    st.success("PASS — all supplied actual outputs match.")
                else:
                    st.error("FAIL — one or more outputs mismatch.")

            if actual:
                for message in diagnose(
                    selected_circuit, saved["inputs"], saved["expected"], actual
                ):
                    st.write("•", message)

        eval_result = st.session_state.get("manual_eval")
        if eval_result and eval_result.get("circuit") == selected_circuit:
            if eval_result["actual"]:
                st.write("**Actual output:**", output_text(eval_result["actual"]))
            else:
                st.caption("No actual outputs supplied; hardware status is unknown.")


# ============================================================
# PROMPT AGENT
# ============================================================

with tab_prompt:
    st.subheader("Talk to the logic-testing agent")
    st.write(
        "Enter a circuit request using binary values. The agent extracts "
        "the circuit and input assignments, validates them, and calculates "
        "the expected output."
    )

    example = (
        "Test MUX D0=1 D1=0 D2=1 D3=0 S1=1 S0=0"
    )
    prompt = st.text_area(
        "Your prompt",
        value=example,
        height=100,
        key="agent_prompt",
    )

    if st.button("Interpret and Run Prompt", type="primary"):
        circuit, parsed_inputs, error = parse_prompt(prompt)

        if error:
            st.error(error)
        else:
            try:
                result = expected_output(circuit, parsed_inputs)
                st.success(f"Agent selected: {circuit}")
                st.write("**Plan:** identify circuit → validate inputs → "
                         "calculate expected output → explain result.")
                st.write("**Parsed inputs:**", input_text(parsed_inputs))
                st.write("**Expected output:**", output_text(result))

                if circuit == "MUX":
                    index = 2 * parsed_inputs["S1"] + parsed_inputs["S0"]
                    st.write(
                        f"The select bits are {parsed_inputs['S1']}"
                        f"{parsed_inputs['S0']}, so D{index} is selected."
                    )
                elif circuit == "DEMUX":
                    index = 2 * parsed_inputs["S1"] + parsed_inputs["S0"]
                    st.write(
                        f"DATA is routed to Y{index}; the other outputs are LOW."
                    )
                elif circuit == "ENCODER":
                    st.write(
                        "The active input position is converted to a two-bit "
                        "binary code."
                    )
                else:
                    index = 2 * parsed_inputs["A1"] + parsed_inputs["A0"]
                    st.write(
                        f"Address {parsed_inputs['A1']}{parsed_inputs['A0']} "
                        f"activates output Y{index}."
                    )

                st.info(
                    "This built-in prompt interpreter uses deterministic rules, "
                    "not an external generative AI model."
                )

            except ValueError as exc:
                st.error(f"Input validation failed: {exc}")


# ============================================================
# EXHAUSTIVE TESTS
# ============================================================

with tab_exhaustive:
    st.subheader("Automatic test-case generation")
    st.write(
        "Generate every valid input combination supported by the selected "
        "circuit and calculate the expected outputs."
    )

    if st.button("Run Exhaustive Simulation", type="primary"):
        cases = all_test_cases(selected_circuit)
        rows = []

        for index, case in enumerate(cases, start=1):
            expected = expected_output(selected_circuit, case)
            rows.append({
                "Test": index,
                "Inputs": input_text(case),
                "Expected outputs": output_text(expected),
                "Status": "SIMULATED — PASS",
            })

        frame = pd.DataFrame(rows)
        st.session_state["exhaustive"] = {
            "circuit": selected_circuit,
            "frame": frame,
        }

    exhaustive = st.session_state.get("exhaustive")
    if exhaustive and exhaustive["circuit"] == selected_circuit:
        frame = exhaustive["frame"]
        st.success(
            f"{len(frame)} valid test cases generated. "
            "All expected values were calculated successfully in Python."
        )
        st.dataframe(frame, use_container_width=True, hide_index=True)
        st.download_button(
            "Download test report as CSV",
            data=frame.to_csv(index=False).encode("utf-8"),
            file_name=f"{selected_circuit.lower()}_test_report.csv",
            mime="text/csv",
        )
        st.caption(
            "These are simulation results, not measured hardware outputs."
        )


# ============================================================
# THEORY AND TRUTH TABLE
# ============================================================

with tab_theory:
    st.subheader("Circuit theory")

    if selected_circuit == "MUX":
        st.write(
            "**Multiplexer (MUX):** selects one of four data inputs using "
            "two select lines. The selected input appears at Y."
        )
        st.code("Y = D[2*S1 + S0]")
        cases = all_test_cases("MUX")
        truth_cases = [
            {"D0": 0, "D1": 1, "D2": 0, "D3": 1,
             "S1": s1, "S0": s0}
            for s1, s0 in itertools.product((0, 1), repeat=2)
        ]
        truth_rows = []
        for case in truth_cases:
            out = mux(
                [case[f"D{i}"] for i in range(4)],
                case["S1"], case["S0"]
            )
            truth_rows.append({**case, "Y": out})
        st.write("Truth table using example data inputs D0=0, D1=1, D2=0, D3=1:")
        st.dataframe(pd.DataFrame(truth_rows), hide_index=True)

    elif selected_circuit == "DEMUX":
        st.write(
            "**Demultiplexer (DEMUX):** routes one data input to exactly "
            "one selected output. All other outputs remain LOW."
        )
        st.code("Selected output index = 2*S1 + S0")
        rows = []
        for data, s1, s0 in itertools.product((0, 1), repeat=3):
            rows.append({
                "DATA": data, "S1": s1, "S0": s0,
                **{f"Y{i}": v for i, v in enumerate(demux(data, s1, s0))}
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True)

    elif selected_circuit == "ENCODER":
        st.write(
            "**4-to-2 Encoder:** converts one active input into its binary "
            "position. This basic encoder requires exactly one HIGH input."
        )
        rows = []
        for i in range(4):
            values = [0, 0, 0, 0]
            values[i] = 1
            y1, y0 = encoder(values)
            rows.append({
                **{f"I{j}": values[j] for j in range(4)},
                "Y1": y1, "Y0": y0,
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True)

    else:
        st.write(
            "**2-to-4 Decoder:** converts a two-bit address into four "
            "outputs. Exactly one output is HIGH for each address."
        )
        rows = []
        for a1, a0 in itertools.product((0, 1), repeat=2):
            rows.append({
                "A1": a1, "A0": a0,
                **{f"Y{i}": v for i, v in enumerate(decoder(a1, a0))}
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True)

    st.divider()
    st.markdown("#### Assumptions")
    st.write(
        "- All signals are binary and active-HIGH.\n"
        "- Select/address bit order is MSB first: S1/S0 or A1/A0.\n"
        "- The encoder is a basic one-hot encoder without a valid bit.\n"
        "- Unknown states (X/Z), propagation delays, and electrical faults "
        "are not simulated."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()
st.caption(
    "Educational prototype • Python-based logic simulation • "
    "No physical hardware was tested by this software."
)
