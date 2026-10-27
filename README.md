
# Agentic AI-Based Digital Logic Circuit Tester and Intelligent Fault Diagnosis System

## Overview

This beginner-friendly digital electronics project uses Python and Streamlit
to simulate and test four combinational logic circuits:

1. 4-to-1 Multiplexer (MUX)
2. 1-to-4 Demultiplexer (DEMUX)
3. 4-to-2 Encoder
4. 2-to-4 Decoder

The application calculates expected outputs using deterministic Python
functions. Users can provide actual output values for comparison, generate
exhaustive test cases, view truth tables, and receive possible fault-diagnosis
suggestions.

## Features

- Interactive binary input controls
- Automatic expected-output calculation
- Optional actual-output comparison
- PASS/FAIL evaluation when actual outputs are supplied
- Explicit simulated-functional-test labels
- Rule-based prompt interpretation
- Exhaustive test-case generation
- CSV test-report download
- Possible fault diagnosis
- Input validation and helpful error messages
- No API keys or external AI services required
- Deployable to Render

## Technology stack

- Python
- Streamlit
- Pandas
- GitHub
- Render

## Project structure

    digital-logic-agent/
    ├── app.py
    ├── requirements.txt
    └── README.md

## Run locally

### 1. Install Python

Install Python 3.10 or newer from https://www.python.org/downloads/.

### 2. Open a terminal in the project folder

### 3. Install dependencies

    python -m pip install -r requirements.txt

### 4. Run the application

    python -m streamlit run app.py

Open the local URL printed by Streamlit, normally:

    http://localhost:8501

## Deploy on Render

1. Push this repository to GitHub.
2. Sign in to https://render.com/.
3. Create a new Web Service.
4. Connect the GitHub repository.
5. Select Python as the runtime if prompted.
6. Set the build command:

       pip install -r requirements.txt

7. Set the start command:

       streamlit run app.py --server.port $PORT --server.address 0.0.0.0

8. Choose an available instance plan and deploy.
9. Open the generated Render URL after deployment completes.

## Prompt examples

### MUX

    Test MUX D0=1 D1=0 D2=1 D3=0 S1=1 S0=0

Expected output:

    Y=1

### DEMUX

    Test DEMUX DATA=1 S1=0 S0=1

Expected output:

    Y0=0, Y1=1, Y2=0, Y3=0

### Encoder

    Test encoder I0=0 I1=0 I2=1 I3=0

Expected output:

    Y1=1, Y0=0

### Decoder

    Test decoder A1=1 A0=0

Expected output:

    Y0=0, Y1=0, Y2=1, Y3=0

## Important limitations

This is a software simulation and educational fault-diagnosis prototype.
It does not connect directly to physical circuits or measure electrical
signals. If actual outputs are manually entered, the application compares
those values with the calculated expected values.

The diagnosis lists plausible causes, not confirmed physical faults.
The prompt interpreter uses deterministic rules rather than a hosted
large language model.

The encoder is a basic one-hot encoder. Multiple simultaneous active inputs
are rejected.

The application does not model X/Z values, timing delays, metastability,
or electrical characteristics.

## Future improvements

- Connect a microcontroller or FPGA to collect real output values.
- Add Verilog testbench generation.
- Add a hosted language model for more flexible prompt understanding.
- Add fault injection and automated test coverage.
- Export reports as PDF.

## License

This project may be used for educational and demonstration purposes.
