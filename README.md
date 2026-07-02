# Trust Score Calculator with OpenTelemetry Tracing
This project demonstrates how OpenTelemetry can be used to trace the execution of a Trust Score Calculator and visualize the complete execution flow in Jaeger.
## What this project does
The calculator:
- Validates the input scores and weights
- Calculates the overall Trust Score
- Identifies any risk flags
- Generates a SHA-256 hash of the evidence
- Exports trace data to Jaeger using OpenTelemetry
Each important step is captured as an individual trace span.
## Trace Design
The application contains the following spans:
1. trust_score_pipeline (Parent span)
2. validate_input
3. calculate_trust_score
4. get_risk_flags
5. generate_evidence_hash

The parent span represents the complete execution, while the remaining spans represent each major step of the Trust Score calculation.

Each span records useful attributes such as:

- input validation status
- score values
- weights
- trust score
- detected risk flags
- hash algorithm
- generated hash value

These attributes help understand what happened during each stage of execution.

## Exporting Traces

The application uses the OTLP exporter to send trace data to Jaeger.

Jaeger receives the trace information and displays the execution as a trace waterfall, making it easy to understand how the application executed step by step.

---

## About `time.sleep()`

The actual Trust Score calculation finishes almost instantly.

Without any delay, every span appears as **0 ms** in Jaeger because the work completes too quickly to be visible.

A small `time.sleep(0.01)` delay was added inside each span only to simulate processing time. This makes the execution timeline visible in Jaeger and helps demonstrate the tracing workflow.

This delay is only for visualization and would normally not be used in a production application.

---

## Running the Project

Start Jaeger using Docker:

```bash
docker run -d --name jaeger -p 16686:16686 -p 4317:4317 -p 4318:4318 -p 6831:6831/udp jaegertracing/all-in-one:latest
```

Run the calculator:

```bash
python trust_score.py
```

Open Jaeger:

```
http://localhost:16686
```

Select the **trust-score-calculator** service and view the generated trace.

---

## Output

The application prints:

- Trust Score
- Risk Flags
- Evidence JSON
- SHA-256 Hash

The same execution can also be viewed in Jaeger as a trace waterfall.

---
